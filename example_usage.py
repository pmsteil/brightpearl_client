import os
from dotenv import load_dotenv
from brightpearl_client import BrightPearlClient, BrightPearlApiError

# Load environment variables from .env file
load_dotenv()

def main():
    # Initialize the client
    api_base_url = os.getenv("BRIGHTPEARL_API_URL")
    brightpearl_app_ref = os.getenv("BRIGHTPEARL_APP_REF")
    brightpearl_account_token = os.getenv("BRIGHTPEARL_ACCOUNT_TOKEN")

    client = BrightPearlClient(
        api_base_url=api_base_url,
        brightpearl_app_ref=brightpearl_app_ref,
        brightpearl_account_token=brightpearl_account_token,
        timeout=30,
        max_retries=5,
        rate_limit=1.5
    )

    print(f"Initialized BrightPearl client with API URL: {api_base_url}")

    # Test getting orders by status
    try:
        # Get orders with parsed results (default behavior)
        parsed_orders = client.get_orders_by_status(37)
        print(f"\nRetrieved {len(parsed_orders)} parsed orders with status 37:")
        for order in parsed_orders[:5]:  # Print first 5 orders
            print(f"  Order ID: {order.orderId}, Type: {order.order_type_id}, Status: {order.order_status_id}")

        # Get orders without parsing
        raw_response = client.get_orders_by_status(38, parse_api_results=False)
        print(f"\nRetrieved {len(raw_response.response.results)} raw orders with status 38")

    except ValueError as e:
        print(f"Invalid input: {e}")
    except BrightPearlApiError as e:
        print(f"API error: {e}")

    # Test error handling
    try:
        client.get_orders_by_status(-1)
    except ValueError as e:
        print(f"\nCaught expected ValueError: {e}")

    # Test rate limiting
    print("\nTesting rate limiting...")
    for i in range(5):
        try:
            orders = client.get_orders_by_status(37)
            print(f"  Request {i+1}: Retrieved {len(orders)} orders")
        except BrightPearlApiError as e:
            print(f"  Request {i+1}: API error: {e}")

if __name__ == "__main__":
    main()
