# BrightPearl Client v0.1.0

A Python client for interacting with the BrightPearl API.
This is very much a work in progress and is not yet fully functional.
It only supports querying orders by status id at the moment.
Next it will support warehouse inventory download and upload.

## Installation

To install the BrightPearl client, you can use pip:

```
pipenv install git+https://github.com/pmsteil/brightpearl_client.git
```

## Usage

Here are some examples of how to use the BrightPearl client:

### Initializing the client

```
from brightpearl_client import BrightPearlClient

api_url = "https://use1.brightpearlconnect.com/public-api/nisolo/"
api_headers = {
    "brightpearl-app-ref": "your_app_ref",
    "brightpearl-account-token": "your_account_token"
}

# Initialize with required parameters
client = BrightPearlClient(api_url, api_headers)

# Or, initialize with all parameters including optional ones
client = BrightPearlClient(
    api_url=api_url,
    api_headers=api_headers,
    timeout=30,  # Optional: API request timeout in seconds (default: 15)
    max_retries=5,  # Optional: Maximum number of retries for failed requests (default: 3)
    rate_limit=1.5  # Optional: Minimum time in seconds between API requests (default: 1.0)
)
```

Parameters:
- `api_url` (required): The base URL for the BrightPearl API.
- `api_headers` (required): Headers to be sent with each request, including authentication tokens.
- `timeout` (optional): Timeout for API requests in seconds. Default is 15 seconds.
- `max_retries` (optional): Maximum number of retries for failed requests. Default is 3 retries.
- `rate_limit` (optional): Minimum time in seconds between API requests. Default is 1.0 second.

### Retrieving orders by status

```
try:
    response = client.get_orders_by_status(37)  # 37 is an example status ID
    print(f"Retrieved {len(response.response.results)} orders")
except ValueError as e:
    print(f"Invalid input: {e}")
except BrightPearlApiError as e:
    print(f"API error: {e}")
```

### Parsing order results

```
response = client.get_orders_by_status(37)
parsed_results = client.parse_order_results(response)

for order in parsed_results:
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
3. Run tests: `pytest` or `python -m unittest discover tests`

## License

This project is licensed under the MIT License.
