"""
Unit tests for the BrightPearlClient module.

This will test:
    - get_orders_by_status
    - make_request
    - parse_order_results
    - rate_limit_exponential_backoff
    - client_error_handling
    - server_error_handling
    - max_retries_exceeded
    - logging
"""
import os
import unittest
import json
from unittest.mock import patch, MagicMock
from brightpearl_client.client import BrightPearlClient
from brightpearl_client.base_client import BrightPearlApiResponse, OrderResponse, OrderResult, BrightPearlApiError, BrightPearlClientError
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TestBrightPearlClientMocked(unittest.TestCase):
    def setUp(self):
        self.api_base_url = os.getenv("BRIGHTPEARL_API_URL")
        self.brightpearl_app_ref = os.getenv("BRIGHTPEARL_APP_REF")
        self.brightpearl_account_token = os.getenv("BRIGHTPEARL_ACCOUNT_TOKEN")
        self.client = BrightPearlClient(self.api_base_url, self.brightpearl_app_ref, self.brightpearl_account_token)

    def test_init_without_required_params(self):
        with self.assertRaises(BrightPearlClientError) as context:
            BrightPearlClient("", "", "")
        self.assertIn("Error initializing BrightPearlClient", str(context.exception))

    def test_init_with_invalid_url(self):
        with self.assertRaises(BrightPearlClientError) as context:
            BrightPearlClient("not_a_url", self.brightpearl_app_ref, self.brightpearl_account_token)
        self.assertIn("Error initializing BrightPearlClient", str(context.exception))

    def test_init_with_invalid_timeout(self):
        with self.assertRaises(BrightPearlClientError) as context:
            BrightPearlClient(self.api_base_url, self.brightpearl_app_ref, self.brightpearl_account_token, timeout=0)
        self.assertIn("Error initializing BrightPearlClient", str(context.exception))

    def test_init_with_invalid_max_retries(self):
        with self.assertRaises(BrightPearlClientError) as context:
            BrightPearlClient(self.api_base_url, self.brightpearl_app_ref, self.brightpearl_account_token, max_retries=-1)
        self.assertIn("Error initializing BrightPearlClient", str(context.exception))

    def test_init_with_invalid_rate_limit(self):
        with self.assertRaises(BrightPearlClientError) as context:
            BrightPearlClient(self.api_base_url, self.brightpearl_app_ref, self.brightpearl_account_token, rate_limit=0)
        self.assertIn("Error initializing BrightPearlClient", str(context.exception))

    @patch('requests.get')
    def test_get_orders_by_status_parsed(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "metaData": {
                    "columns": [
                        {"name": "orderId"},
                        {"name": "orderTypeId"},
                        {"name": "contactId"},
                        {"name": "orderStatusId"},
                        {"name": "orderStockStatusId"}
                    ]
                },
                "results": [[1, 2, 3, 4, 5]]
            }
        }
        mock_get.return_value = mock_response

        result = self.client.get_orders_by_status(37)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], OrderResult)
        self.assertEqual(result[0].orderId, 1)

    @patch('requests.get')
    def test_get_orders_by_status_unparsed(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "metaData": {
                    "columns": [
                        {"name": "orderId"},
                        {"name": "orderTypeId"},
                        {"name": "contactId"},
                        {"name": "orderStatusId"},
                        {"name": "orderStockStatusId"}
                    ]
                },
                "results": [[1, 2, 3, 4, 5]]
            }
        }
        mock_get.return_value = mock_response

        result = self.client.get_orders_by_status(37, parse_api_results=False)

        self.assertIsInstance(result, BrightPearlApiResponse)
        self.assertEqual(len(result.response.results), 1)
        self.assertEqual(result.response.results[0], [1, 2, 3, 4, 5])

    def test_get_orders_by_status_with_string(self):
        with self.assertRaises(ValueError):
            self.client.get_orders_by_status("42")

    @patch('requests.get')
    def test_make_request_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        with self.assertRaises(BrightPearlApiError):
            self.client.get_orders_by_status(37)

    def test_api_url_trailing_slash(self):
        client = BrightPearlClient(self.api_base_url + "/", self.brightpearl_app_ref, self.brightpearl_account_token)
        expected_url = self.api_base_url.rstrip('/')
        actual_url = str(client._config.api_base_url).rstrip('/')
        self.assertEqual(actual_url, expected_url)

    def test_parse_api_results(self):
        mock_response = BrightPearlApiResponse(response=OrderResponse(results=[[1, 2, 3, 4, 5]]))
        parsed_results = self.client._parse_api_results(mock_response)
        self.assertIsInstance(parsed_results[0], OrderResult)
        self.assertEqual(parsed_results[0].orderId, 1)
        self.assertEqual(parsed_results[0].order_type_id, 2)
        self.assertEqual(parsed_results[0].contact_id, 3)
        self.assertEqual(parsed_results[0].order_status_id, 4)
        self.assertEqual(parsed_results[0].order_stock_status_id, 5)

    def test_parse_api_results_invalid_format(self):
        mock_response = BrightPearlApiResponse(response=OrderResponse(results=[]))
        parsed_results = self.client._parse_api_results(mock_response)
        self.assertEqual(parsed_results, [])

class TestBrightPearlClientLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_base_url = os.getenv("BRIGHTPEARL_API_URL")
        cls.brightpearl_app_ref = os.getenv("BRIGHTPEARL_APP_REF")
        cls.brightpearl_account_token = os.getenv("BRIGHTPEARL_ACCOUNT_TOKEN")
        cls.client = BrightPearlClient(cls.api_base_url, cls.brightpearl_app_ref, cls.brightpearl_account_token)

    def test_live_get_orders_by_status(self):
        result = self.client.get_orders_by_status(37)  # 37 is "Needs Attention" status
        self.assertIsInstance(result, list)
        if result:
            self.assertIsInstance(result[0], OrderResult)

    def test_live_get_orders_by_status_unparsed(self):
        result = self.client.get_orders_by_status(37, parse_api_results=False)
        self.assertIsInstance(result, BrightPearlApiResponse)
        self.assertIsInstance(result.response, OrderResponse)
        self.assertIsInstance(result.response.results, list)
        if result.response.results:
            self.assertIsInstance(result.response.results[0], list)

    @patch('requests.post')
    @patch('brightpearl_client.client.BrightPearlClient.get_all_live_products')
    @patch('brightpearl_client.client.BrightPearlClient.get_product_availability')
    def test_stock_correction_invalidates_cache(self, mock_get_product_availability, mock_get_all_live_products, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": [813313, 813314]}
        mock_post.return_value = mock_response

        # Mock get_all_live_products to return a list of products
        mock_get_all_live_products.return_value = [
            {"productId": 1007, "SKU": "SKU1007"},
            {"productId": 1008, "SKU": "SKU1008"}
        ]

        # Mock get_product_availability to return some availability data
        mock_get_product_availability.return_value = {
            1007: {"warehouses": {"3": {"onHand": 5}}},
            1008: {"warehouses": {"3": {"onHand": 7}}}
        }

        # Create dummy cache files
        for product_id in [1007, 1008]:
            cache_file = os.path.join(self.client._cache_dir, f'product_availability_{product_id}_cache.json')
            with open(cache_file, 'w') as f:
                json.dump({'some': 'data'}, f)

        corrections = [
            {"productId": 1007, "new_quantity": 10, "reason": "Test correction"},
            {"productId": 1008, "new_quantity": 15, "reason": "Test correction"}
        ]

        with self.assertLogs(level='DEBUG') as log:
            result = self.client.stock_correction(3, corrections)

        # Print log output for debugging
        print("Log output:")
        for message in log.output:
            print(message)

        self.assertEqual(result, [813313, 813314])

        for product_id in [1007, 1008]:
            cache_file = os.path.join(self.client._cache_dir, f'product_availability_{product_id}_cache.json')
            self.assertFalse(os.path.exists(cache_file), f"Cache file for product {product_id} should not exist")

        self.assertTrue(any('Cache file removed for key: product_availability_1007' in message for message in log.output))
        self.assertTrue(any('Cache file removed for key: product_availability_1008' in message for message in log.output))

if __name__ == '__main__':
    unittest.main()
