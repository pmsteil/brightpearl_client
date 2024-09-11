"""
BrightPearl API Client

This module provides a client for interacting with the BrightPearl API.
It allows you to retrieve and parse order data from the BrightPearl API.

It is a work in progress and is not yet fully functional.

It only supports querying orders by status id at the moment.
Next it will support warehouse inventory download and upload.
"""
from .base_client import BaseBrightPearlClient, BrightPearlApiResponse, OrderResult, BrightPearlApiError, BrightPearlClientError, OrderResponse
from typing import Union, List, Dict, Any, Optional
import logging
from pydantic import BaseModel, Field
import requests  # Add this import
import os
import json
from datetime import datetime, timedelta
import math
import hashlib
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING to reduce output

class ProductAvailabilityResponse(BaseModel):
    response: Dict[str, Any]

class WarehouseInventoryResponse(BaseModel):
    response: Dict[str, Any]

class ProductSearchMetaDataColumn(BaseModel):
    name: str
    sortable: bool
    filterable: bool
    reportDataType: str
    referenceData: List[str]
    isFreeTextSearchable: bool
    required: bool

class ProductSearchMetaDataSorting(BaseModel):
    filterable: ProductSearchMetaDataColumn
    direction: str

class ProductSearchMetaData(BaseModel):
    morePagesAvailable: bool
    resultsAvailable: int
    resultsReturned: int
    firstResult: int
    lastResult: int
    columns: List[Dict[str, Any]]
    sorting: List[Dict[str, Any]]

class ProductSearchResponse(BaseModel):
    response: Dict[str, Any]

class FormattedProductSearchResponse(BaseModel):
    products: List[Dict[str, Any]]
    metadata: ProductSearchMetaData

class BrightPearlClient(BaseBrightPearlClient):
    def get_orders_by_status(self, status_id: int, parse_api_results: bool = True) -> Union[BrightPearlApiResponse, List[OrderResult]]:
        if not isinstance(status_id, int) or status_id <= 0:
            raise ValueError("status_id must be a positive integer")

        relative_url = f'/order-service/order-search?orderStatusId={status_id}'
        response = self._make_request(relative_url, BrightPearlApiResponse)
        return self._parse_api_results(response) if parse_api_results else response

    def get_product_availability(self, product_ids: List[int], cache_minutes: int = 15) -> Dict[int, Dict[str, Any]]:
        """
        Retrieve the availability for specified products across all warehouses.

        Args:
            product_ids (List[int]): A list of product IDs to query.
            cache_minutes (int): Number of minutes to consider the cache valid. Defaults to 15.

        Returns:
            Dict[int, Dict[str, Any]]: A dictionary containing the availability information for the specified products.

        Raises:
            ValueError: If product_ids is empty.
        """
        if not product_ids:
            raise ValueError("product_ids must not be empty")

        result = {}
        uncached_product_ids = []

        for product_id in product_ids:
            cache_key = f'product_availability_{product_id}'
            cached_data = self._get_cached_data(cache_key, cache_minutes)
            if cached_data:
                result[product_id] = cached_data
            else:
                uncached_product_ids.append(product_id)

        if uncached_product_ids:
            product_ids_str = ','.join(map(str, uncached_product_ids))
            relative_url = f'/warehouse-service/product-availability/{product_ids_str}'

            try:
                response = self._make_request(relative_url, ProductAvailabilityResponse)
                for product_id, availability in response.response.items():
                    result[int(product_id)] = availability
                    self._save_to_cache(f'product_availability_{product_id}', availability)
            except BrightPearlApiError as e:
                if isinstance(e.__cause__, requests.exceptions.HTTPError) and e.__cause__.response.status_code == 400:
                    logger.warning(f"No inventory data available for some products: {product_ids_str}")
                    # Set empty availability for products with no data
                    for product_id in uncached_product_ids:
                        result[product_id] = {"warehouses": {}, "total": {}}
                else:
                    logger.error(f"Failed to retrieve product availability: {str(e)}")
                    # In case of other errors, we'll still return the data we have
                    for product_id in uncached_product_ids:
                        if product_id not in result:
                            result[product_id] = {"warehouses": {}, "total": {}}

        return result

    def search_products(self) -> FormattedProductSearchResponse:
        """
        Search for products with no arguments, returning the complete list of available products.

        Returns:
            FormattedProductSearchResponse: A formatted response containing the product search results and metadata.

        Raises:
            BrightPearlApiError: If there's an error with the API request.
        """
        relative_url = '/product-service/product-search'

        try:
            response = self._make_request(relative_url, ProductSearchResponse)
            return self._format_product_search_response(response)
        except BrightPearlApiError as e:
            logger.error(f"Failed to search products: {str(e)}")
            raise BrightPearlApiError(f"Failed to search products: {str(e)}")

    def _format_product_search_response(self, response: ProductSearchResponse) -> FormattedProductSearchResponse:
        metadata = response.response['metaData']
        column_names = [column['name'] for column in metadata['columns']]

        formatted_products = []
        for product_data in response.response['results']:
            product_dict = dict(zip(column_names, product_data))
            formatted_products.append(product_dict)

        return FormattedProductSearchResponse(
            products=formatted_products,
            metadata=ProductSearchMetaData(**metadata)
        )

    def get_all_live_products(self, cache_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Retrieve all live products, using a cached version if available and not older than specified minutes.

        Args:
            cache_minutes (int): Number of minutes to consider the cache valid. Defaults to 60.

        Returns:
            List[Dict[str, Any]]: A list of all live products.

        Raises:
            BrightPearlApiError: If there's an error with the API request.
        """
        cache_key = 'live_products'
        cached_data = self._get_cached_data(cache_key, cache_minutes)
        if cached_data:
            logger.info("Using cached live products data")
            return cached_data

        live_products = self._fetch_all_live_products()

        self._save_to_cache(cache_key, live_products)

        return live_products

    def _fetch_all_live_products(self) -> List[Dict[str, Any]]:
        """
        Fetch all live products from the API.
        """
        all_products = []
        first_result = 1
        products_per_page = 500

        print("Fetching products: ", end="", flush=True)

        while True:
            try:
                relative_url = f'/product-service/product-search?pageSize={products_per_page}&firstResult={first_result}'
                logger.debug(f"Retrieving products starting from result {first_result}")
                response = self._make_request(relative_url, ProductSearchResponse)
                formatted_response = self._format_product_search_response(response)

                metadata = formatted_response.metadata
                products_in_batch = len(formatted_response.products)

                all_products.extend(formatted_response.products)

                print(".", end="", flush=True)

                if len(all_products) >= metadata.resultsAvailable or not metadata.morePagesAvailable:
                    break

                first_result = metadata.lastResult + 1

            except BrightPearlApiError as e:
                print()  # Move to a new line before printing the error
                logger.error(f"Failed to retrieve products starting from result {first_result}: {str(e)}")
                raise BrightPearlApiError(f"Failed to retrieve all products: {str(e)}")

        print()  # Move to a new line after all products are fetched
        logger.info(f"Retrieved {len(all_products)} total products")

        live_products = [product for product in all_products if product.get('productStatus') == 'LIVE']
        logger.info(f"Filtered {len(live_products)} live products out of {len(all_products)} total products")

        return live_products

    def warehouse_inventory_download(self, warehouse_id: int) -> Dict[int, Dict[str, Any]]:
        """
        Download warehouse inventory for a specified warehouse ID.

        Args:
            warehouse_id (int): Warehouse ID to fetch inventory for.

        Returns:
            Dict[int, Dict[str, Any]]: A dictionary with product IDs as keys and their inventory and product data as values.
        """
        # Get all live products
        live_products = self.get_all_live_products()
        product_ids = [product['productId'] for product in live_products]

        # Fetch inventory data
        inventory_data = self._fetch_inventory_data(product_ids)

        # Create a dictionary to map product IDs to their data
        product_data_map = {product['productId']: product for product in live_products}

        # Filter inventory data for the requested warehouse ID and merge with product data
        filtered_inventory = {}
        for product_id, warehouse_data in inventory_data.items():
            if warehouse_id in warehouse_data:
                product_info = product_data_map.get(product_id, {})
                warehouse_inventory = warehouse_data[warehouse_id]
                filtered_inventory[product_id] = {
                    **product_info,
                    'inventory_inStock': warehouse_inventory['inStock'],
                    'inventory_onHand': warehouse_inventory['onHand'],
                    'inventory_allocated': warehouse_inventory['allocated'],
                    'inventory_inTransit': warehouse_inventory['inTransit'],
                    'warehouseId': warehouse_id
                }

        return filtered_inventory

    def _fetch_inventory_data(self, product_ids: List[int]) -> Dict[int, Dict[int, Dict[str, Any]]]:
        """
        Fetch inventory data for given product IDs.

        Args:
            product_ids (List[int]): List of product IDs to fetch inventory for.

        Returns:
            Dict[int, Dict[int, Dict[str, Any]]]: A dictionary with product IDs as keys and
                                                  dictionaries of warehouse IDs and inventory data as values.
        """
        inventory_data = {}
        batch_size = 500
        total_batches = math.ceil(len(product_ids) / batch_size)

        print("Fetching inventory: ", end="", flush=True)
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(product_ids))
            batch_product_ids = product_ids[start_idx:end_idx]

            logger.debug(f"Fetching inventory for batch {batch_num + 1}/{total_batches}")
            batch_availability = self.get_product_availability(batch_product_ids)

            for product_id, availability in batch_availability.items():
                if isinstance(availability, dict) and 'warehouses' in availability:
                    inventory_data[int(product_id)] = {
                        int(warehouse_id): {
                            'inStock': warehouse_info.get('inStock', 0),
                            'onHand': warehouse_info.get('onHand', 0),
                            'allocated': warehouse_info.get('allocated', 0),
                            'inTransit': warehouse_info.get('inTransit', 0)
                        }
                        for warehouse_id, warehouse_info in availability['warehouses'].items()
                    }
                    # Add total availability data
                    inventory_data[int(product_id)]['total'] = availability.get('total', {})
                else:
                    logger.warning(f"Unexpected availability data format for product ID {product_id}")

            print(".", end="", flush=True)

        print()  # Move to a new line after all batches are processed
        return inventory_data

    def _handle_request_exception(self, e: requests.exceptions.RequestException, attempt: int):
        if isinstance(e, requests.exceptions.Timeout):
            logger.warning(f"Request timed out (attempt {attempt + 1}/{self._config.max_retries})")
        elif isinstance(e, requests.exceptions.HTTPError):
            self._handle_http_error(e, attempt)
        else:
            logger.error(f"Request failed: {str(e)}")
            if attempt == self._config.max_retries - 1:
                raise BrightPearlApiError(f"Request failed after {self._config.max_retries} attempts: {str(e)}")

    def stock_correction(self, warehouse_id: int, corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply stock corrections for multiple products in a specified warehouse.

        Args:
            warehouse_id (int): The ID of the warehouse where the corrections will be applied.
            corrections (List[Dict[str, Any]]): A list of dictionaries containing correction details.
                Each dictionary should have the following structure:
                {
                    "productId": int or "sku": str,
                    "new_quantity": int,
                    "reason": str
                }

        Returns:
            Dict[str, Any]: The API response containing the results of the stock corrections.

        Raises:
            BrightPearlApiError: If there's an error with the API request.
            ValueError: If the input parameters are invalid.
        """
        if not isinstance(warehouse_id, int) or warehouse_id <= 0:
            raise ValueError("warehouse_id must be a positive integer")

        if not corrections or not isinstance(corrections, list):
            raise ValueError("corrections must be a non-empty list of dictionaries")

        # Get all live products to map SKUs to product IDs
        live_products = self.get_all_live_products()
        sku_to_product_id = {product['SKU']: product['productId'] for product in live_products}

        formatted_corrections = []
        product_ids = []

        for correction in corrections:
            if 'sku' in correction:
                sku = correction['sku']
                if sku not in sku_to_product_id:
                    raise ValueError(f"SKU '{sku}' not found in live products")
                product_id = sku_to_product_id[sku]
            elif 'productId' in correction:
                product_id = correction['productId']
            else:
                raise ValueError("Each correction must contain either 'sku' or 'productId'")

            product_ids.append(product_id)

        # Get current availability for all products
        current_availability = self.get_product_availability(product_ids)

        for correction in corrections:
            product_id = correction.get('productId') or sku_to_product_id[correction['sku']]
            new_quantity = correction['new_quantity']
            product_availability = current_availability.get(product_id, {})
            warehouse_availability = product_availability.get('warehouses', {}).get(str(warehouse_id), {})
            current_quantity = warehouse_availability.get('onHand', 0)
            quantity_change = new_quantity - current_quantity

            formatted_corrections.append({
                "quantity": quantity_change,
                "productId": product_id,
                "reason": correction["reason"],
                "locationId": 2,  # Hardcoded to 2 as per requirements
                "cost": {
                    "currency": "USD",
                    "value": 0.00
                }
            })

        payload = {
            "corrections": formatted_corrections
        }

        relative_url = f'/warehouse-service/warehouse/{warehouse_id}/stock-correction'

        try:
            response = self._make_request(relative_url, dict, method='POST', json=payload)
            return response
        except BrightPearlApiError as e:
            logger.error(f"Failed to apply stock corrections: {str(e)}")
            raise BrightPearlApiError(f"Failed to apply stock corrections: {str(e)}")

    # Add other public API methods here
