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

logger = logging.getLogger(__name__)

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

    def get_product_availability(self, product_ids: List[int], cache_minutes: int = 15) -> Dict:
        """
        Retrieve the availability for specified products across all warehouses.

        Args:
            product_ids (List[int]): A list of product IDs to query.
            cache_minutes (int): Number of minutes to consider the cache valid. Defaults to 15.

        Returns:
            Dict: A dictionary containing the availability information for the specified products across all warehouses.

        Raises:
            ValueError: If product_ids is empty.
            BrightPearlApiError: If there's an error with the API request.
        """
        if not product_ids:
            raise ValueError("product_ids must not be empty")

        # Create a hash of the product IDs for the cache key
        product_ids_str = ','.join(map(str, sorted(product_ids)))
        hash_object = hashlib.md5(product_ids_str.encode())
        cache_key = f'product_availability_{hash_object.hexdigest()}'

        cached_data = self._get_cached_data(cache_key, cache_minutes)
        if cached_data:
            return cached_data

        relative_url = f'/warehouse-service/product-availability/{product_ids_str}'

        try:
            response = self._make_request(relative_url, ProductAvailabilityResponse)
            self._save_to_cache(cache_key, response.response)
            return response.response
        except BrightPearlApiError as e:
            logger.error(f"Failed to retrieve product availability: {str(e)}")
            raise BrightPearlApiError(f"Failed to retrieve product availability for products {product_ids_str}: {str(e)}")

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
            return cached_data

        logger.info("Fetching fresh live products data")
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

        logger.info("Starting retrieval of all live products")

        while True:
            try:
                relative_url = f'/product-service/product-search?pageSize={products_per_page}&firstResult={first_result}'
                logger.info(f"Retrieving products starting from result {first_result}")
                response = self._make_request(relative_url, ProductSearchResponse)
                formatted_response = self._format_product_search_response(response)

                metadata = formatted_response.metadata
                logger.info(f"Batch metadata:")
                logger.info(f"  More pages available: {metadata.morePagesAvailable}")
                logger.info(f"  Results available: {metadata.resultsAvailable}")
                logger.info(f"  Results returned: {metadata.resultsReturned}")
                logger.info(f"  First result: {metadata.firstResult}")
                logger.info(f"  Last result: {metadata.lastResult}")

                products_in_batch = len(formatted_response.products)
                logger.info(f"Retrieved {products_in_batch} products in this batch")

                all_products.extend(formatted_response.products)

                total_products = len(all_products)
                logger.info(f"Total products retrieved so far: {total_products}")

                if total_products >= metadata.resultsAvailable or not metadata.morePagesAvailable:
                    logger.info("All available products have been retrieved.")
                    break

                first_result = metadata.lastResult + 1

            except BrightPearlApiError as e:
                logger.error(f"Failed to retrieve products starting from result {first_result}: {str(e)}")
                raise BrightPearlApiError(f"Failed to retrieve all products: {str(e)}")

        live_products = [product for product in all_products if product.get('productStatus') == 'LIVE']
        logger.info(f"Filtered {len(live_products)} live products out of {len(all_products)} total products")

        return live_products

    def warehouse_inventory_download(self, warehouse_ids: List[int]) -> Dict[int, Dict[int, int]]:
        """
        Download warehouse inventory for specified warehouse IDs.

        Args:
            warehouse_ids (List[int]): List of warehouse IDs to fetch inventory for.

        Returns:
            Dict[int, Dict[int, int]]: A dictionary with warehouse IDs as keys and
                                       dictionaries of product IDs and their quantities as values.
        """
        # Get all live products
        live_products = self.get_all_live_products()
        product_ids = [product['productId'] for product in live_products]

        # Fetch inventory data
        inventory_data = self._fetch_inventory_data(product_ids)

        # Filter inventory data for requested warehouse IDs
        filtered_inventory = {
            warehouse_id: {
                product_id: warehouse_data.get(warehouse_id, 0)
                for product_id, warehouse_data in inventory_data.items()
                if warehouse_id in warehouse_data
            }
            for warehouse_id in warehouse_ids
        }

        return filtered_inventory

    def _fetch_inventory_data(self, product_ids: List[int]) -> Dict[int, Dict[int, int]]:
        """
        Fetch inventory data for given product IDs.

        Args:
            product_ids (List[int]): List of product IDs to fetch inventory for.

        Returns:
            Dict[int, Dict[int, int]]: A dictionary with product IDs as keys and
                                       dictionaries of warehouse IDs and quantities as values.
        """
        inventory_data = {}
        batch_size = 500
        total_batches = math.ceil(len(product_ids) / batch_size)

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(product_ids))
            batch_product_ids = product_ids[start_idx:end_idx]

            logger.info(f"Fetching inventory data for batch {batch_num + 1}/{total_batches}")
            batch_availability = self.get_product_availability(batch_product_ids)

            for product_id, availability in batch_availability.items():
                inventory_data[int(product_id)] = {
                    int(warehouse_id): warehouse_info['onHand']
                    for warehouse_id, warehouse_info in availability['warehouses'].items()
                }

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

    # Add other public API methods here
