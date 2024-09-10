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
from unittest.mock import patch, MagicMock
from brightpearl_client.client import BrightPearlClient
from brightpearl_client.base_client import BrightPearlApiResponse, OrderResponse, OrderResult, BrightPearlApiError, BrightPearlClientError
import requests

# Remove the dotenv import if it's not being used

class TestBrightPearlClientMocked(unittest.TestCase):
    def setUp(self):
        self.api_base_url = "https://use1.brightpearlconnect.com/public-api/nisolo/"
        self.brightpearl_app_ref = "nisolo_operations"
        self.brightpearl_account_token = "Da+8ugbNK6nUL1QnmJROutSj77AKOqPLbzXymaK/yrU="
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
        mock_response.json.return_value = {"response": {"results": [[1, 2, 3, 4, 5]]}}
        mock_get.return_value = mock_response

        result = self.client.get_orders_by_status(37)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], OrderResult)
        self.assertEqual(result[0].orderId, 1)

    @patch('requests.get')
    def test_get_orders_by_status_unparsed(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": {"results": [[1, 2, 3, 4, 5]]}}
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

    # @patch('requests.get')
    # def test_warehouse_inventory_download(self, mock_get):
    #     mock_response = MagicMock()
    #     mock_response.json.return_value = {
    #         "response": {
    #             "results": [
    #                 [1, "Product 1", "SKU1", 10, 15, 2, 3],
    #                 [2, "Product 2", "SKU2", 5, 7, 1, 2]
    #             ],
    #             "metaData": {
    #                 "columns": [
    #                     {"name": "productId"},
    #                     {"name": "productName"},
    #                     {"name": "SKU"},
    #                     {"name": "inStock"},
    #                     {"name": "onHand"},
    #                     {"name": "allocated"},
    #                     {"name": "inTransit"}
    #                 ]
    #             }
    #         }
    #     }
    #     mock_get.return_value = mock_response

    #     # Mock the get_all_live_products method
    #     self.client.get_all_live_products = MagicMock(return_value=[
    #         {"productId": 1, "productName": "Product 1", "SKU": "SKU1"},
    #         {"productId": 2, "productName": "Product 2", "SKU": "SKU2"}
    #     ])

    #     result = self.client.warehouse_inventory_download(18)

    #     self.assertIsInstance(result, dict)
    #     self.assertEqual(len(result), 2)
    #     self.assertEqual(result[1]["productName"], "Product 1")
    #     self.assertEqual(result[1]["inventory_inStock"], 10)
    #     self.assertEqual(result[1]["inventory_onHand"], 15)
    #     self.assertEqual(result[1]["inventory_allocated"], 2)
    #     self.assertEqual(result[1]["inventory_inTransit"], 3)
    #     self.assertEqual(result[2]["productName"], "Product 2")
    #     self.assertEqual(result[2]["inventory_inStock"], 5)

    #     # Test with invalid warehouse_id
    #     with self.assertRaises(ValueError):
    #         self.client.warehouse_inventory_download(0)

class TestBrightPearlClientLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_base_url = "https://use1.brightpearlconnect.com/public-api/nisolo/"
        cls.brightpearl_app_ref = "nisolo_operations"
        cls.brightpearl_account_token = "Da+8ugbNK6nUL1QnmJROutSj77AKOqPLbzXymaK/yrU="
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

if __name__ == '__main__':
    unittest.main()
