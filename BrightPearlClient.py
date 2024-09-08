import sys
import os
import pydantic
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import requests

class OrderResult(BaseModel):
    orderId: int
    order_type_id: int
    contact_id: int
    order_status_id: int
    order_stock_status_id: int
    # Add other fields as needed, matching the order of items in the list

    @classmethod
    def from_list(cls, data: List[Any]):
        return cls(
            orderId=data[0],
            order_type_id=data[1],
            contact_id=data[2],
            order_status_id=data[3],
            order_stock_status_id=data[4],
            # Add other fields as needed
        )

class OrderResponse(BaseModel):
    results: List[List[Any]]  # Change this to List[List[Any]]

class BrightPearlApiResponse(BaseModel):
    response: OrderResponse

class BrightPearlClient:
    def __init__(self, api_url: str, api_headers: Dict[str, str]):
        self.api_url = api_url.rstrip('/')
        self.api_headers = api_headers

    def get_orders_by_status(self, status_id: int) -> BrightPearlApiResponse:
        if not isinstance(status_id, int):
            raise TypeError("status_id must be an integer")
        relative_url = f'/order-service/order-search?orderStatusId={status_id}'
        return self._make_request(relative_url)

    # def get_orders_by_list(self, list_id: str) -> BrightPearlApiResponse:
    #     relative_url = f'/order-service/order-search/{list_id}'
    #     return self._make_request(relative_url)

    def _make_request(self, relative_url: str) -> BrightPearlApiResponse:
        url = f'{self.api_url}{relative_url}'
        response = requests.get(url, headers=self.api_headers, timeout=15)
        response.raise_for_status()
        return BrightPearlApiResponse(**response.json())

    def parse_order_results(self, api_response: BrightPearlApiResponse) -> List[OrderResult]:
        return [OrderResult.from_list(result) for result in api_response.response.results]
