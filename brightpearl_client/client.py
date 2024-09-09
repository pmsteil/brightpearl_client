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

logger = logging.getLogger(__name__)

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

    def get_warehouse_inventory(self, product_ids: List[int]) -> Dict:
        """
        Retrieve the inventory for specified products across all warehouses.

        Args:
            product_ids (List[int]): A list of product IDs to query.

        Returns:
            Dict: A dictionary containing the inventory information for the specified products across all warehouses.

        Raises:
            ValueError: If product_ids is empty.
            BrightPearlApiError: If there's an error with the API request.
        """
        if not product_ids:
            raise ValueError("product_ids must not be empty")

        product_ids_str = ','.join(map(str, product_ids))
        relative_url = f'/warehouse-service/product-availability/{product_ids_str}'

        try:
            response = self._make_request(relative_url, WarehouseInventoryResponse)
            return response.response
        except BrightPearlApiError as e:
            logger.error(f"Failed to retrieve warehouse inventory: {str(e)}")
            raise BrightPearlApiError(f"Failed to retrieve warehouse inventory for products {product_ids_str}: {str(e)}")

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

    # def _make_raw_request(self, relative_url: str) -> requests.Response:
    #     url = f'{self._config.api_base_url}{relative_url}'
    #     headers = {
    #         "brightpearl-app-ref": self._config.brightpearl_app_ref,
    #         "brightpearl-account-token": self._config.brightpearl_account_token
    #     }
    #     for attempt in range(self._config.max_retries):
    #         try:
    #             self._respect_rate_limit()
    #             logger.debug(f"Making request to: {url}")
    #             response = requests.get(url, headers=headers, timeout=self._config.timeout)
    #             response.raise_for_status()
    #             logger.info(f"Successfully retrieved data from: {url}")
    #             return response
    #         except requests.exceptions.RequestException as e:
    #             self._handle_request_exception(e, attempt)

    #     logger.error(f"Max retries ({self._config.max_retries}) exceeded for URL: {url}")
    #     raise BrightPearlApiError(f"Failed to retrieve data after {self._config.max_retries} attempts")

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
