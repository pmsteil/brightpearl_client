import os
import unittest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
from brightpearl_client.client import BrightPearlClient, BrightPearlApiResponse, OrderResponse, OrderResult

# Load environment variables from .env file
load_dotenv()

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
        This test should fail as the method expects an integer for status_id.
        """
        # Call the method
        with self.assertRaises(TypeError):
            self.client.get_orders_by_status("42")  # type: ignore

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
