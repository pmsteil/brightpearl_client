import requests
import logging
import time
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from requests.exceptions import RequestException, Timeout, HTTPError

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

class BrightPearlApiError(Exception):
    """Custom exception for BrightPearl API errors."""
    pass

class BrightPearlClient:
    """
    A client for interacting with the BrightPearl API.

    This client provides methods to retrieve and parse order data from the BrightPearl API.
    It handles authentication, rate limiting, and error handling.

    Attributes:
        api_url (str): The base URL for the BrightPearl API.
        api_headers (Dict[str, str]): Headers to be sent with each request.
        timeout (int): Timeout for API requests in seconds.
        max_retries (int): Maximum number of retries for failed requests.
        rate_limit (float): Minimum time (in seconds) between API requests.
        last_request_time (float): Timestamp of the last API request.

    Methods:
        get_orders_by_status: Retrieve orders by status ID.
        parse_order_results: Parse the order results from the API response.
    """

    def __init__(self, api_url: str, api_headers: Dict[str, str], timeout: int = 15, max_retries: int = 3, rate_limit: float = 1.0) -> None:
        """
        Initialize the BrightPearl client.

        Args:
            api_url: The base URL for the BrightPearl API.
            api_headers: Headers to be sent with each request.
            timeout: Timeout for API requests in seconds.
            max_retries: Maximum number of retries for failed requests.
            rate_limit: Minimum time (in seconds) between API requests.
        """
        self.api_url: str = api_url.rstrip('/')
        self.api_headers: Dict[str, str] = api_headers
        self.timeout: int = timeout
        self.max_retries: int = max_retries
        self.rate_limit: float = rate_limit
        self.last_request_time: float = 0.0

        logger.info(f"Initialized BrightPearlClient with API URL: {self.api_url}")

    def get_orders_by_status(self, status_id: int) -> BrightPearlApiResponse:
        """
        Retrieve orders by status ID.

        This method makes a GET request to the BrightPearl API to retrieve orders
        with the specified status ID.

        Args:
            status_id: The status ID to filter orders by.

        Returns:
            A BrightPearlApiResponse object containing the order data.

        Raises:
            ValueError: If status_id is not a positive integer.
            BrightPearlApiError: If the API request fails.
        """
        if not isinstance(status_id, int) or status_id <= 0:
            logger.error(f"Invalid status_id: {status_id}")
            raise ValueError("status_id must be a positive integer")

        logger.info(f"Retrieving orders with status ID: {status_id}")
        relative_url: str = f'/order-service/order-search?orderStatusId={status_id}'
        return self._make_request(relative_url)

    def _respect_rate_limit(self) -> None:
        """Ensure the rate limit is respected before making a request."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            logger.debug(f"Rate limit: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = current_time

    def _make_request(self, relative_url: str) -> BrightPearlApiResponse:
        """
        Make a GET request to the BrightPearl API.

        :param relative_url: The relative URL for the API endpoint.
        :return: A BrightPearlApiResponse object containing the API response data.
        :raises BrightPearlApiError: If the request fails after max_retries attempts.
        """
        url: str = f'{self.api_url}{relative_url}'
        for attempt in range(self.max_retries):
            try:
                self._respect_rate_limit()
                logger.debug(f"Making request to: {url}")
                response: requests.Response = requests.get(url, headers=self.api_headers, timeout=self.timeout)
                response.raise_for_status()
                logger.info(f"Successfully retrieved data from: {url}")
                return BrightPearlApiResponse(**response.json())
            except Timeout:
                logger.warning(f"Request timed out (attempt {attempt + 1}/{self.max_retries})")
            except HTTPError as http_err:
                logger.error(f"HTTP error occurred: {http_err}")
                if response.status_code == 429:
                    logger.warning("Rate limit exceeded. Implementing exponential backoff.")
                    time.sleep((attempt + 1) ** 2)
                elif 400 <= response.status_code < 500:
                    raise BrightPearlApiError(f"Client error: {http_err}")
                elif 500 <= response.status_code < 600:
                    logger.error(f"Server error: {http_err}")
                    raise BrightPearlApiError(f"Server error: {http_err}")
                else:
                    logger.error(f"Unexpected HTTP error: {http_err}")
                    raise BrightPearlApiError(f"Unexpected HTTP error: {http_err}")
            except RequestException as e:
                logger.error(f"Request failed: {str(e)}")

        logger.error(f"Max retries ({self.max_retries}) exceeded for URL: {url}")
        raise BrightPearlApiError(f"Failed to retrieve data after {self.max_retries} attempts")

    def parse_order_results(self, api_response: BrightPearlApiResponse) -> List[OrderResult]:
        """
        Parse the order results from the API response.

        :param api_response: The BrightPearlApiResponse object to parse.
        :return: A list of OrderResult objects.
        """
        logger.info(f"Parsing {len(api_response.response.results)} order results")
        return [OrderResult.from_list(result) for result in api_response.response.results]
