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
import unittest
import io
import logging
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
from brightpearl_client.client import BrightPearlClient, BrightPearlApiResponse, OrderResponse, OrderResult, BrightPearlApiError
import requests

# Load environment variables from .env file
# load_dotenv()

class TestBrightPearlClientMocked(unittest.TestCase):
    def setUp(self):
        self.api_url = "https://use1.brightpearlconnect.com/public-api/nisolo/"
        self.api_headers = { "brightpearl-app-ref": "nisolo_operations", "brightpearl-account-token": "Da+8ugbNK6nUL1QnmJROutSj77AKOqPLbzXymaK/yrU=" }
        self.client = BrightPearlClient(self.api_url, self.api_headers)

    @patch('brightpearl_client.client.requests.get')
    def test_get_orders_by_status(self, mock_get):
        """
        Test the get_orders_by_status method with a mocked API response.
        Verifies that the method correctly processes the API response and makes the request with the right parameters.
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": {"results": [[1, 2, 3, 4, 5]]}}
        mock_get.return_value = mock_response

        # Call the method
        result = self.client.get_orders_by_status(37)

        # Assert the result
        self.assertIsInstance(result, BrightPearlApiResponse)
        self.assertEqual(result.response.results[0][0], 1)

        # Assert the request was made correctly
        mock_get.assert_called_once_with(
            f"{self.api_url}order-service/order-search?orderStatusId=37",
            headers=self.api_headers,
            timeout=15
        )

    def test_get_orders_by_status_with_string(self):
        """
        Test the get_orders_by_status method with a string input for status_id.
        This test should fail as the method expects a positive integer for status_id.
        """
        # Call the method
        with self.assertRaises(ValueError):
            self.client.get_orders_by_status("42")

    def test_get_orders_by_status_with_negative_integer(self):
        """
        Test the get_orders_by_status method with a negative integer input for status_id.
        This test should fail as the method expects a positive integer for status_id.
        """
        # Call the method
        with self.assertRaises(ValueError):
            self.client.get_orders_by_status(-1)

    @patch('brightpearl_client.client.requests.get')
    def test_make_request_error(self, mock_get):
        """
        Test the error handling of the _make_request method.
        Verifies that exceptions from the API call are properly raised.
        """
        # Setup mock response to raise an exception
        mock_get.side_effect = Exception("API Error")

        # Assert that the exception is raised
        with self.assertRaises(Exception):
            self.client.get_orders_by_status(37)

    def test_api_url_trailing_slash(self):
        """
        Test that the BrightPearlClient correctly handles API URLs with trailing slashes.
        Verifies that the trailing slash is removed from the API URL.
        """
        client = BrightPearlClient(self.api_url + "/", self.api_headers)
        expected_url = self.api_url.rstrip('/')
        self.assertEqual(client.api_url, expected_url)

    def test_parse_order_results(self):
        """
        Test the parse_order_results method.
        """
        mock_response = BrightPearlApiResponse(response=OrderResponse(results=[[1, 2, 3, 4, 5]]))
        parsed_results = self.client.parse_order_results(mock_response)
        self.assertIsInstance(parsed_results[0], OrderResult)
        self.assertEqual(parsed_results[0].orderId, 1)
        self.assertEqual(parsed_results[0].order_type_id, 2)
        self.assertEqual(parsed_results[0].contact_id, 3)
        self.assertEqual(parsed_results[0].order_status_id, 4)
        self.assertEqual(parsed_results[0].order_stock_status_id, 5)

    # @patch('time.sleep')
    # @patch('time.time')
    # def test_respect_rate_limit(self, mock_time, mock_sleep):
    #     mock_time.side_effect = [0, 0.5, 1.0]  # Simulate time passing
    #     self.client._respect_rate_limit()
    #     self.client._respect_rate_limit()
    #     mock_sleep.assert_called_once_with(0.5)
    #     self.assertEqual(self.client.last_request_time, 1.0)

    @patch('brightpearl_client.client.requests.get')
    @patch('time.sleep')
    def test_rate_limit_exponential_backoff(self, mock_sleep, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = [
            requests.exceptions.HTTPError("429 Client Error: Too Many Requests"),
            None
        ]
        mock_response.status_code = 429
        mock_response.json.return_value = {"response": {"results": []}}
        mock_get.return_value = mock_response

        self.client.get_orders_by_status(37)

        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)  # First retry sleeps for 1 second
        mock_sleep.assert_any_call(1)  # Rate limit sleep

    @patch('brightpearl_client.client.requests.get')
    def test_client_error_handling(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error: Bad Request")
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        with self.assertRaises(BrightPearlApiError):
            self.client.get_orders_by_status(37)

    @patch('brightpearl_client.client.requests.get')
    def test_server_error_handling(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error: Internal Server Error")
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with self.assertRaises(BrightPearlApiError):
            self.client.get_orders_by_status(37)

    @patch('brightpearl_client.client.requests.get')
    def test_max_retries_exceeded(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        with self.assertRaises(BrightPearlApiError) as context:
            self.client.get_orders_by_status(37)

        self.assertIn("Failed to retrieve data after 3 attempts", str(context.exception))

class TestLogging(unittest.TestCase):
    def setUp(self):
        self.log_capture = io.StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger().removeHandler(self.handler)

    @patch('brightpearl_client.client.requests.get')
    def test_logging(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": {"results": [[1, 2, 3, 4, 5]]}}
        mock_get.return_value = mock_response

        client = BrightPearlClient("http://test.com", {})
        client.get_orders_by_status(37)

        log_contents = self.log_capture.getvalue()
        self.assertIn("Retrieving orders with status ID: 37", log_contents)
        self.assertIn("Making request to: http://test.com/order-service/order-search?orderStatusId=37", log_contents)
        self.assertIn("Successfully retrieved data from: http://test.com/order-service/order-search?orderStatusId=37", log_contents)

class TestBrightPearlClientLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_url = "https://use1.brightpearlconnect.com/public-api/nisolo/"
        cls.api_header = { "brightpearl-app-ref": "nisolo_operations", "brightpearl-account-token": "Da+8ugbNK6nUL1QnmJROutSj77AKOqPLbzXymaK/yrU=" }
        cls.client = BrightPearlClient(cls.api_url, cls.api_header)

    def test_live_get_orders_by_status(self):
        """
        Test the get_orders_by_status method with a live API call.
        Verifies that the method can successfully connect to the API and retrieve order data.
        """
        result = self.client.get_orders_by_status(37)  # 37 is "Needs Attention" status
        self.assertIsInstance(result, BrightPearlApiResponse)
        self.assertIsInstance(result.response, OrderResponse)
        self.assertIsInstance(result.response.results, list)
        if result.response.results:
            self.assertIsInstance(result.response.results[0], list)

        parsed_results = self.client.parse_order_results(result)
        if parsed_results:
            self.assertIsInstance(parsed_results[0], OrderResult)

if __name__ == '__main__':
    unittest.main()
