import requests
import logging
import time
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

class OrderResult(BaseModel):
    """
    Represents a single order result from the BrightPearl API.
    """
    orderId: int
    order_type_id: int
    contact_id: int
    order_status_id: int
    order_stock_status_id: int
    # Add other fields as needed

    @classmethod
    def from_list(cls, data: List[Any]) -> 'OrderResult':
        """
        Create an OrderResult instance from a list of values.

        :param data: A list containing order data.
        :return: An OrderResult instance.
        """
        return cls(
            orderId=data[0],
            order_type_id=data[1],
            contact_id=data[2],
            order_status_id=data[3],
            order_stock_status_id=data[4],
            # Add other fields as needed
        )

class OrderResponse(BaseModel):
    """
    Represents the response containing order results from the BrightPearl API.
    """
    results: List[List[Any]]

class BrightPearlApiResponse(BaseModel):
    """
    Represents the full API response from BrightPearl.
    """
    response: OrderResponse

class BrightPearlClient:
    """
    A client for interacting with the BrightPearl API.
    """

    def __init__(self, api_url: str, api_headers: Dict[str, str], timeout: int = 15, max_retries: int = 3, rate_limit: float = 1.0):
        """
        Initialize the BrightPearl client.

        :param api_url: The base URL for the BrightPearl API.
        :param api_headers: Headers to be sent with each request.
        :param timeout: Timeout for API requests in seconds.
        :param max_retries: Maximum number of retries for failed requests.
        :param rate_limit: Minimum time (in seconds) between API requests.
        """
        self.api_url: str = api_url.rstrip('/')
        self.api_headers: Dict[str, str] = api_headers
        self.timeout: int = timeout
        self.max_retries: int = max_retries
        self.rate_limit: float = rate_limit
        self.last_request_time: float = 0.0

    def get_orders_by_status(self, status_id: int) -> BrightPearlApiResponse:
        """
        Retrieve orders by status ID.

        :param status_id: The status ID to filter orders by.
        :return: A BrightPearlApiResponse object containing the order data.
        :raises ValueError: If status_id is not a positive integer.
        """
        if not isinstance(status_id, int) or status_id <= 0:
            raise ValueError("status_id must be a positive integer")
        relative_url: str = f'/order-service/order-search?orderStatusId={status_id}'
        return self._make_request(relative_url)

    def _respect_rate_limit(self):
        """Ensure the rate limit is respected before making a request."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last_request)
        self.last_request_time = time.time()

    def _make_request(self, relative_url: str) -> BrightPearlApiResponse:
        """
        Make a GET request to the BrightPearl API.

        :param relative_url: The relative URL for the API endpoint.
        :return: A BrightPearlApiResponse object containing the API response data.
        :raises RequestException: If the request fails after max_retries attempts.
        """
        url: str = f'{self.api_url}{relative_url}'
        for attempt in range(self.max_retries):
            try:
                self._respect_rate_limit()
                response: requests.Response = requests.get(url, headers=self.api_headers, timeout=self.timeout)
                response.raise_for_status()
                return BrightPearlApiResponse(**response.json())
            except Timeout:
                logger.warning(f"Request timed out (attempt {attempt + 1}/{self.max_retries})")
            except RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
        raise RequestException("Max retries exceeded")

    def parse_order_results(self, api_response: BrightPearlApiResponse) -> List[OrderResult]:
        """
        Parse the order results from the API response.

        :param api_response: The BrightPearlApiResponse object to parse.
        :return: A list of OrderResult objects.
        """
        return [OrderResult.from_list(result) for result in api_response.response.results]
