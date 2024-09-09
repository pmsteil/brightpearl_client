import time
import requests
from requests.exceptions import Timeout, HTTPError, RequestException
import logging
from pydantic import BaseModel, Field, HttpUrl, field_validator, ValidationError
from typing import Dict, Any, List, Optional, Union, Type, TypeVar
import os
import json
from datetime import datetime, timedelta

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)

class BrightPearlClientError(Exception):
    """Custom exception for BrightPearl client configuration errors."""
    pass

class BrightPearlApiError(Exception):
    """Custom exception for BrightPearl API errors."""
    pass

class BrightPearlClientConfig(BaseModel):
    api_base_url: HttpUrl = Field(..., description="The base URL for the BrightPearl API")
    brightpearl_app_ref: str = Field(..., description="The BrightPearl application reference")
    brightpearl_account_token: str = Field(..., description="The BrightPearl account token")
    timeout: int = Field(15, description="Timeout for API requests in seconds")
    max_retries: int = Field(3, description="Maximum number of retries for failed requests")
    rate_limit: float = Field(1.0, description="Minimum time (in seconds) between API requests")

    @field_validator('timeout', 'max_retries')
    @classmethod
    def check_positive_int(cls, v):
        if v <= 0:
            raise ValueError("Must be a positive integer")
        return v

    @field_validator('rate_limit')
    @classmethod
    def check_positive_float(cls, v):
        if v <= 0:
            raise ValueError("Must be a positive number")
        return v

    @field_validator('api_base_url')
    @classmethod
    def remove_trailing_slash(cls, v):
        return str(v).rstrip('/')

class OrderResult(BaseModel):
    orderId: int
    order_type_id: int
    contact_id: int
    order_status_id: int
    order_stock_status_id: int

    @classmethod
    def from_list(cls, data: List[Any]) -> 'OrderResult':
        return cls(
            orderId=data[0],
            order_type_id=data[1],
            contact_id=data[2],
            order_status_id=data[3],
            order_stock_status_id=data[4],
        )

class OrderResponse(BaseModel):
    results: List[List[Any]]

class BrightPearlApiResponse(BaseModel):
    response: OrderResponse

class BaseBrightPearlClient:
    def __init__(self, api_base_url: str, brightpearl_app_ref: str, brightpearl_account_token: str,
                 timeout: int = 30, max_retries: int = 3, rate_limit: float = 1):
        self._config = self._initialize_config(
            api_base_url=api_base_url,
            brightpearl_app_ref=brightpearl_app_ref,
            brightpearl_account_token=brightpearl_account_token,
            timeout=timeout,
            max_retries=max_retries,
            rate_limit=rate_limit
        )
        self._last_request_time = 0.0
        self._cache_dir = '_bp_cache_'
        os.makedirs(self._cache_dir, exist_ok=True)

    def _initialize_config(self, **kwargs):
        try:
            return BrightPearlClientConfig(**kwargs)
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = error["loc"][0]
                message = error["msg"]
                error_messages.append(f"'{field}': {message}")
            raise BrightPearlClientError("Error initializing BrightPearlClient:\n" + "\n".join(error_messages))

    def _respect_rate_limit(self) -> None:
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._config.rate_limit:
            sleep_time = self._config.rate_limit - time_since_last_request
            logger.debug(f"Rate limit: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _make_request(self, relative_url: str, response_model: Type[T]) -> T:
        url = f'{self._config.api_base_url}{relative_url}'
        headers = {
            "brightpearl-app-ref": self._config.brightpearl_app_ref,
            "brightpearl-account-token": self._config.brightpearl_account_token
        }
        for attempt in range(self._config.max_retries):
            try:
                self._respect_rate_limit()
                logger.debug(f"Making request to: {url}")
                response = requests.get(url, headers=headers, timeout=self._config.timeout)
                response.raise_for_status()
                logger.info(f"Successfully retrieved data from: {url}")
                return response_model(**response.json())
            except Timeout:
                logger.warning(f"Request timed out (attempt {attempt + 1}/{self._config.max_retries})")
            except HTTPError as http_err:
                self._handle_http_error(http_err, attempt)
            except RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                if attempt == self._config.max_retries - 1:
                    raise BrightPearlApiError(f"Request failed after {self._config.max_retries} attempts: {str(e)}")

        logger.error(f"Max retries ({self._config.max_retries}) exceeded for URL: {url}")
        raise BrightPearlApiError(f"Failed to retrieve data after {self._config.max_retries} attempts")

    def _handle_http_error(self, http_err: HTTPError, attempt: int):
        if http_err.response.status_code == 429:
            logger.warning("Rate limit exceeded. Implementing exponential backoff.")
            time.sleep((attempt + 1) ** 2)
        elif 400 <= http_err.response.status_code < 500:
            raise BrightPearlApiError(f"Client error: {http_err}")
        elif 500 <= http_err.response.status_code < 600:
            logger.error(f"Server error: {http_err}")
            raise BrightPearlApiError(f"Server error: {http_err}")
        else:
            logger.error(f"Unexpected HTTP error: {http_err}")
            raise BrightPearlApiError(f"Unexpected HTTP error: {http_err}")

    def _parse_api_results(self, api_response: BrightPearlApiResponse) -> List[OrderResult]:
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

    def _get_cached_data(self, cache_key: str, cache_minutes: int) -> Optional[Any]:
        """
        Retrieve cached data if it exists and is not older than specified minutes.

        Args:
            cache_key (str): Key to identify the cached data.
            cache_minutes (int): Number of minutes to consider the cache valid.

        Returns:
            Optional[Any]: Cached data if valid, None otherwise.
        """
        cache_file = os.path.join(self._cache_dir, f'{cache_key}_cache.json')
        if os.path.exists(cache_file):
            cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - cache_time < timedelta(minutes=cache_minutes):
                logger.info(f"Using cached data for {cache_key}")
                with open(cache_file, 'r') as cache_file:
                    return json.load(cache_file)
        return None

    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """
        Save data to cache.

        Args:
            cache_key (str): Key to identify the cached data.
            data (Any): Data to be cached.
        """
        cache_file = os.path.join(self._cache_dir, f'{cache_key}_cache.json')
        with open(cache_file, 'w') as cache_file:
            json.dump(data, cache_file)
        logger.info(f"Saved data to cache for {cache_key}")
