"""
BrightPearl API Client

This module provides a client for interacting with the BrightPearl API.
It allows you to retrieve and parse order data from the BrightPearl API.

It is a work in progress and is not yet fully functional.

It only supports querying orders by status id at the moment.
Next it will support warehouse inventory download and upload.
"""
from .base_client import BaseBrightPearlClient, BrightPearlApiResponse, OrderResult, BrightPearlApiError, BrightPearlClientError, OrderResponse
from typing import Union, List

class BrightPearlClient(BaseBrightPearlClient):
    def get_orders_by_status(self, status_id: int, parse_api_results: bool = True) -> Union[BrightPearlApiResponse, List[OrderResult]]:
        if not isinstance(status_id, int) or status_id <= 0:
            raise ValueError("status_id must be a positive integer")

        relative_url = f'/order-service/order-search?orderStatusId={status_id}'
        response = self._make_request(relative_url)
        return self._parse_api_results(response) if parse_api_results else response

    # Add other public API methods here
