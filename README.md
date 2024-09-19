# BrightPearl Client

A Python client for interacting with the BrightPearl API.

## Installation

To install the BrightPearl client, you can use pip:

```
pipenv install git+https://github.com/pmsteil/brightpearl_client.git
```

## Usage

Here's a basic example of how to use the BrightPearl client:

```
from brightpearl_client import BrightPearlClient

api_base_url = "https://use1.brightpearlconnect.com/public-api/your_account_name/"
brightpearl_app_ref = "your_app_ref"
brightpearl_account_token = "your_account_token"

# Initialize with required parameters
client = BrightPearlClient(api_base_url, brightpearl_app_ref, brightpearl_account_token)

# Or, initialize with all parameters including optional ones
client = BrightPearlClient(
    api_base_url=api_base_url,
    brightpearl_app_ref=brightpearl_app_ref,
    brightpearl_account_token=brightpearl_account_token,
    timeout=30,  # Optional: API request timeout in seconds (default: 15)
    max_retries=5,  # Optional: Maximum number of retries for failed requests (default: 3)
    rate_limit=1.5  # Optional: Minimum time in seconds between API requests (default: 1.0)
)
```

Parameters:
- `api_base_url` (required): The base URL for the BrightPearl API.
- `brightpearl_app_ref` (required): The BrightPearl application reference.
- `brightpearl_account_token` (required): The BrightPearl account token.
- `timeout` (optional): Timeout for API requests in seconds. Default is 15 seconds.
- `max_retries` (optional): Maximum number of retries for failed requests. Default is 3 retries.
- `rate_limit` (optional): Minimum time in seconds between API requests. Default is 1.0 second.

### Retrieving orders by status

```
parsed_orders = client.get_orders_by_status(37)

for order in parsed_orders:
    print(f"Order ID: {order.orderId}")
    print(f"Order Type ID: {order.order_type_id}")
    print(f"Contact ID: {order.contact_id}")
    print(f"Order Status ID: {order.order_status_id}")
    print(f"Order Stock Status ID: {order.order_stock_status_id}")
    print("---")
```

### Error handling

The client raises `BrightPearlApiError` for API-related errors:

```
try:
    response = client.get_orders_by_status(37)
except BrightPearlApiError as e:
    if "Client error" in str(e):
        print("There was a problem with the request")
    elif "Server error" in str(e):
        print("The BrightPearl API is experiencing issues")
    else:
        print(f"An unexpected error occurred: {e}")
```

## Development

1. Clone the repository
2. Install dependencies: `pipenv install`
3. Run tests: `python -m unittest discover tests`

## Creating BrightPearl API credentials

1. Login to BrightPearl with the proper account name, this will be the last part of the `BRIGHTPEARL_API_URL`. Example: /public-api/account_name/.
2. Click "App Store"
3. Click "Private Apps" in the top right of the toolbar
4. Click "Add private app"
5. Select "Staff app"
6. Give it a descriptive Name like "Python API Client"
7. Add the "Identifier".
8. Make sure "Active" is checked
9. Click the "Install" button at the bottom
10. Copy the "Reference" field value.  This is the `BRIGHTPEARL_APP_REF`. This will be different from the Identifier you provided above.
10. Copy the "Token" displayed on the screen.  This is the `BRIGHTPEARL_ACCOUNT_TOKEN`
11. Configure your three ENV variables accordingly for example:
BRIGHTPEARL_API_URL="https://use1.brightpearlconnect.com/public-api/account_name/"
BRIGHTPEARL_APP_REF="accountname_python_api_client"
BRIGHTPEARL_ACCOUNT_TOKEN="1234567890"

## License

This project is licensed under the MIT License.
