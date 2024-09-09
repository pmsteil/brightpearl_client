"""
BrightPearl API Client

This module provides a client for interacting with the BrightPearl API.
It allows you to retrieve and parse order data from the BrightPearl API.

It is a work in progress and is not yet fully functional.

It only supports querying orders by status id at the moment.
Next it will support warehouse inventory download and upload.
"""
import requests
import logging
import time
from pydantic import BaseModel, Field, HttpUrl, field_validator, ValidationError
from typing import Dict, Any, List, Optional, Union
from requests.exceptions import RequestException, Timeout, HTTPError

logger = logging.getLogger(__name__)

class BrightPearlClientError(Exception):
    """Custom exception for BrightPearl client configuration errors."""
    pass

class BrightPearlClientConfig(BaseModel):
    api_base_url: HttpUrl = Field(..., description="The base URL for the BrightPearl API")
    brightpearl_app_ref: str = Field(..., description="The BrightPearl application reference")
    brightpearl_account_token: str = Field(..., description="The BrightPearl account token")
    timeout: int = Field(15, description="Timeout for API requests in seconds")
    max_retries: int = Field(3, description="Maximum number of retries for failed requests")
    rate_limit: float = Field(1.0, description="Minimum time (in seconds) between API requests")

    @field_validator('api_base_url', 'brightpearl_app_ref', 'brightpearl_account_token', 'timeout', 'max_retries', 'rate_limit')
    @classmethod
    def check_not_none(cls, v):
        if v is None:
            raise ValueError("This field cannot be None")
        return v

    @field_validator('brightpearl_app_ref', 'brightpearl_account_token')
    @classmethod
    def check_not_empty(cls, v):
        if not v:
            raise ValueError("This field cannot be empty")
        return v

    @field_validator('timeout', 'max_retries')
    @classmethod
    def check_positive_int(cls, v):
        if v <= 0:
            raise ValueError("This field must be a positive integer")
        return v

    @field_validator('rate_limit')
    @classmethod
    def check_positive_float(cls, v):
        if v <= 0:
            raise ValueError("This field must be a positive number")
        return v

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

        Args:
            data: A list containing order data.

        Returns:
            An OrderResult instance.
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

    @field_validator('results')
    @classmethod
    def check_results(cls, v):
        if not isinstance(v, list):
            return []
        return v

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
    """

    def __init__(self, api_base_url: str, brightpearl_app_ref: str, brightpearl_account_token: str,
                 timeout: int = 15, max_retries: int = 3, rate_limit: float = 1.0) -> None:
        """
        Initialize the BrightPearl client.

        Args:
            api_base_url: The base URL for the BrightPearl API.
            brightpearl_app_ref: The BrightPearl application reference.
            brightpearl_account_token: The BrightPearl account token.
            timeout: Timeout for API requests in seconds. Defaults to 15.
            max_retries: Maximum number of retries for failed requests. Defaults to 3.
            rate_limit: Minimum time (in seconds) between API requests. Defaults to 1.0.

        Raises:
            BrightPearlClientError: If any of the input parameters are invalid.
        """
        try:
            config = BrightPearlClientConfig(
                api_base_url=api_base_url,
                brightpearl_app_ref=brightpearl_app_ref,
                brightpearl_account_token=brightpearl_account_token,
                timeout=timeout,
                max_retries=max_retries,
                rate_limit=rate_limit
            )
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = error["loc"][0]
                message = error["msg"]
                error_messages.append(f"'{field}': {message}")
            raise BrightPearlClientError("Error initializing BrightPearlClient:\n" + "\n".join(error_messages))

        self.api_url: str = str(config.api_base_url).rstrip('/')
        self.api_headers: Dict[str, str] = {
            "brightpearl-app-ref": config.brightpearl_app_ref,
            "brightpearl-account-token": config.brightpearl_account_token
        }
        self.timeout: int = config.timeout
        self.max_retries: int = config.max_retries
        self.rate_limit: float = config.rate_limit
        self.last_request_time: float = 0.0

        logger.info(f"Initialized BrightPearlClient with API URL: {self.api_url}")

    def get_orders_by_status(self, status_id: int, parse_api_results: bool = True) -> Union[BrightPearlApiResponse, List[OrderResult]]:
        """
        Retrieve orders by status ID.

        Args:
            status_id: The status ID to filter orders by.
            parse_api_results: Whether to parse the API results into OrderResult objects. Defaults to True.

        Returns:
            If parse_api_results is True, returns a list of OrderResult objects.
            Otherwise, returns the raw BrightPearlApiResponse.

        Raises:
            ValueError: If status_id is not a positive integer.
            BrightPearlApiError: If the API request fails.
        """
        if not isinstance(status_id, int) or status_id <= 0:
            logger.error(f"Invalid status_id: {status_id}")
            raise ValueError("status_id must be a positive integer")

        logger.info(f"Retrieving orders with status ID: {status_id}")
        relative_url: str = f'/order-service/order-search?orderStatusId={status_id}'
        response = self._make_request(relative_url)

        if parse_api_results:
            return self._parse_api_results(response)
        return response

    def _respect_rate_limit(self) -> None:
        """
        Ensure the rate limit is respected before making a request.

        This method will sleep if necessary to maintain the minimum time between requests.
        """
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

        Args:
            relative_url: The relative URL for the API endpoint.

        Returns:
            BrightPearlApiResponse: An object containing the API response data.

        Raises:
            BrightPearlApiError: If the request fails after max_retries attempts.
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
                if attempt == self.max_retries - 1:
                    raise BrightPearlApiError(f"Request failed after {self.max_retries} attempts: {str(e)}")

        logger.error(f"Max retries ({self.max_retries}) exceeded for URL: {url}")
        raise BrightPearlApiError(f"Failed to retrieve data after {self.max_retries} attempts")

    def _parse_api_results(self, api_response: BrightPearlApiResponse) -> List[OrderResult]:
        """
        Parse the API results from BrightPearl's format into a list of OrderResult objects.

        This method detects if the data is in BrightPearl's typical format (a list of lists) and converts
        it into more usable OrderResult objects.

        Args:
            api_response: The raw API response from BrightPearl.

        Returns:
            A list of OrderResult objects.

        Example:
            BrightPearl typically returns data in this format:
            {
                "response": {
                    "results": [
                        [1001, 1, 5001, 3, 2],
                        [1002, 2, 5002, 4, 1],
                        ...
                    ]
                }
            }

            This method converts it to:
            [
                OrderResult(orderId=1001, order_type_id=1, contact_id=5001, order_status_id=3, order_stock_status_id=2),
                OrderResult(orderId=1002, order_type_id=2, contact_id=5002, order_status_id=4, order_stock_status_id=1),
                ...
            ]
        """
        logger.info(f"Parsing API results")
        if not isinstance(api_response.response.results, list):
            logger.warning("API response is not in the expected format")
            return []

        parsed_results = []
        for result in api_response.response.results:
            if isinstance(result, list) and len(result) >= 5:
                parsed_results.append(OrderResult.from_list(result))
            else:
                logger.warning(f"Unexpected result format: {result}")

        logger.info(f"Parsed {len(parsed_results)} results")
        return parsed_results
