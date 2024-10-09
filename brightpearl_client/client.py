"""
BrightPearl API Client

This module provides a client for interacting with the BrightPearl API.
It allows you to retrieve and parse order data from the BrightPearl API.

It is a work in progress and is not yet fully functional.

It only supports querying orders by status id at the moment.
Next it will support warehouse inventory download and upload.
"""
from .base_client import BaseBrightPearlClient, BrightPearlApiResponse, OrderResult, BrightPearlApiError, BrightPearlClientError, OrderResponse, OrdersMetadata
from typing import Union, List, Dict, Any, Optional, Tuple
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
logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all log messages

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


# response like: {'response': [{'id': 438, 'warehouseId': 13, 'groupingA': 'QUARANTINE'}, {'id': 439, 'warehouseId': 13, 'groupingA': '0', 'groupingB': '0', 'groupingC': '0', 'groupingD': '0'}]}
class WarehouseLocationResponse(BaseModel):
    response: List[Dict[str, Any]]

class BrightPearlClient(BaseBrightPearlClient):
    def __init__(self, api_base_url: str, brightpearl_app_ref: str, brightpearl_account_token: str,
                 timeout: int = 30, max_retries: int = 3, rate_limit: float = 1):
        super().__init__(api_base_url, brightpearl_app_ref, brightpearl_account_token,
                         timeout, max_retries, rate_limit)
        self._cache_prefix = self._generate_cache_prefix(brightpearl_app_ref)

    def set_log_level(self, log_level: int):
        logger.setLevel(log_level)

    def _generate_cache_prefix(self, brightpearl_app_ref: str) -> str:
        """Generate a hash prefix for cache filenames."""
        return hashlib.md5(brightpearl_app_ref.encode()).hexdigest()[:8]

    def _get_cache_filename(self, cache_key: str) -> str:
        """Generate a cache filename with the hash prefix."""
        return f"{self._cache_prefix}_{cache_key}_cache.json"

    def _get_cached_data(self, cache_key: str, cache_minutes: int) -> Optional[Any]:
        cache_file = os.path.join(self._cache_dir, self._get_cache_filename(cache_key))
        if os.path.exists(cache_file):
            cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - cache_time < timedelta(minutes=cache_minutes):
                # logger.info(f"Using cached data for {cache_key}")
                with open(cache_file, 'r') as cache_file:
                    return json.load(cache_file)
        return None

    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        cache_file = os.path.join(self._cache_dir, self._get_cache_filename(cache_key))
        with open(cache_file, 'w') as cache_file:
            json.dump(data, cache_file)
        # logger.info(f"Saved data to cache for {cache_key}")

    def _invalidate_cache(self, cache_key: str):
        cache_file = os.path.join(self._cache_dir, self._get_cache_filename(cache_key))
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except OSError as e:
                logger.error(f"Error removing cache file for key {cache_key}: {e}")
        else:
            logger.info(f"No cache file found for key: {cache_key}")

    def get_orders_by_status(self, status_id: int, parse_api_results: bool = True) -> Union[BrightPearlApiResponse, Tuple[List[OrderResult], OrdersMetadata]]:
        if not isinstance(status_id, int) or status_id <= 0:
            raise ValueError("status_id must be a positive integer")

        relative_url = f'/order-service/order-search?orderStatusId={status_id}'
        response = self._make_request(relative_url, BrightPearlApiResponse)
        if parse_api_results:
            return self._parse_api_results(response)
        else:
            return response

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

        # Get all live products to check stockTracked status
        live_products = self.get_all_live_products()
        stock_tracked_products = {product['productId']: product for product in live_products if product.get('stockTracked', False)}

        for product_id in product_ids:
            if product_id not in stock_tracked_products:
                logger.info(f"Product ID {product_id} is not stock tracked. Skipping availability check.")
                result[product_id] = {"warehouses": {}, "total": {}}
                continue

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
                logger.error(f"Failed to retrieve product availability: {str(e)}")
                # In case of errors, we'll still return the data we have
                for product_id in uncached_product_ids:
                    if product_id not in result:
                        result[product_id] = {"warehouses": {}, "total": {}}

        return result

    def search_products(self, include_non_stock_tracked: bool = False) -> FormattedProductSearchResponse:
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
            return self._format_product_search_response(response, include_non_stock_tracked)
        except BrightPearlApiError as e:
            logger.error(f"Failed to search products: {str(e)}")
            raise BrightPearlApiError(f"Failed to search products: {str(e)}")

    def _format_product_search_response(self, response: ProductSearchResponse, include_non_stock_tracked: bool = False) -> FormattedProductSearchResponse:
        """
            Format the returned product search response.
            The returned response is a dictionary with a 'results' key and a 'metaData' key.
            The 'results' key contains a list of products, each with the same number of elements as there are columns in the 'metaData'.
            The 'metaData' key contains a dictionary with a 'columns' key, which has a list of column names.
            This function zips the column names to the product data to return a list of products, each with a dictionary of column names and values.
            Also if include_non_stock_tracked is true, it will include products that are not stock tracked in the results.
        """
        metadata = response.response['metaData']
        column_names = [column['name'] for column in metadata['columns']]

        formatted_products = []
        for product_data in response.response['results']:
            product_dict = dict(zip(column_names, product_data))
            if include_non_stock_tracked or product_dict.get('stockTracked', False):
                formatted_products.append(product_dict)
            else:
                logger.debug(f"Product ID {product_dict.get('productId')} is not stock tracked. Skipping.")

        return FormattedProductSearchResponse(
            products=formatted_products,
            metadata=ProductSearchMetaData(**metadata)
        )

    def get_all_live_products(self, cache_minutes: int = 60, include_non_stock_tracked: bool = False) -> List[Dict[str, Any]]:
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

        live_products = self._fetch_all_live_products(include_non_stock_tracked)

        self._save_to_cache(cache_key, live_products)

        return live_products

    def _fetch_all_live_products(self, include_non_stock_tracked: bool = False) -> List[Dict[str, Any]]:
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
                formatted_response = self._format_product_search_response(response, include_non_stock_tracked)

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

    def warehouse_get_locations( self, warehouse_id: int ) -> List[Dict[str, Any]]:
        """
        Get the locations for a warehouse
        /warehouse/1/location/
        """
        relative_url = f'/warehouse-service/warehouse/{warehouse_id}/location'

        response = self._make_request(relative_url, WarehouseLocationResponse)
        return response.response

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

    def stock_correction(self, warehouse_id: int, location: str, corrections: List[Dict[str, Any]]) -> List[int]:
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
            List[int]: The list of correction IDs returned by the API.

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
                    raise ValueError(f"SKU '{sku}' not found in live products in warehouse {warehouse_id}")
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
            # calculate the quantity delta to send as the stock correction (positive:add stock, negative:remove stock)
            quantity_delta = new_quantity - current_quantity

            if location is None:
                location = "0.0.0.0"

            if quantity_delta != 0:
                correction = ({
                    "quantity": quantity_delta,
                    "productId": product_id,
                    "locationId": int(location),
                    "reason": correction["reason"],
                    "cost": {
                        "currency": "USD",
                    "value": 0.00
                }
                })
                formatted_corrections.append( correction )

        if len(formatted_corrections) > 0:
            apply_stock_correction_response = self.apply_stock_correction(warehouse_id, formatted_corrections)
            return apply_stock_correction_response
        else:
            logger.warning("No stock corrections to apply")
            return []

    def apply_stock_correction( self, warehouse_id: int, formatted_corrections: List[Dict[str, Any]] ) -> List[int]:
        """
        Apply stock corrections to a warehouse.

        Args:
            warehouse_id (int): The ID of the warehouse where the corrections will be applied.
            formatted_corrections (List[Dict[str, Any]]): A list of dictionaries containing correction details.

        Returns:
            List[int]: The list of correction IDs returned by the API.

        Raises:
            BrightPearlApiError: If there's an error with the API request.
        """
        logger.debug(f"formatted_corrections: {formatted_corrections}")
        payload = {
            "corrections": formatted_corrections
        }

        relative_url = f'/warehouse-service/warehouse/{warehouse_id}/stock-correction'

        try:
            logger.info(f"POSTing stock corrections to {relative_url}:\n{json.dumps(payload, indent=2)}")
            response = self._make_request(relative_url, list, method='POST', json=payload)

            if isinstance(response, list) and len(response) > 0:
                for correction in formatted_corrections:
                    product_id = correction['productId']
                    self._invalidate_product_availability_cache(product_id)
                    logger.info(f"Invalidated cache for product ID {product_id} after successful stock correction")

                return response
            else:
                raise BrightPearlApiError(f"Stock correction failed: {response}")

        except BrightPearlApiError as e:
            logger.error(f"Failed to apply stock corrections: {str(e)}")
            logger.error(f"payload: {payload}")
            raise BrightPearlApiError(f"Failed to apply stock corrections: {str(e)}")


    def _invalidate_product_availability_cache(self, product_id):
        cache_key = f'product_availability_{product_id}'
        cache_file = os.path.join(self._cache_dir, self._get_cache_filename(cache_key))
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except OSError as e:
                logger.error(f"Error removing cache file for key {self._cache_prefix}_{cache_key}: {e}")
        else:
            logger.info(f"No cache file found for key: {self._cache_prefix}_{cache_key}")

    def _get_product_id_by_sku(self, sku):
        # Implement this method to fetch product ID by SKU
        # You can use the existing get_all_live_products method or implement a new API call
        products = self.get_all_live_products()
        for product in products:
            if product['SKU'] == sku:
                return product['productId']
        raise ValueError(f"Product with SKU {sku} not found")
