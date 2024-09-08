# BrightPearl Client

A Python client for interacting with the BrightPearl API.

## Installation

To install the BrightPearl client, you can use pip:

```bash
pipenv install git+https://github.com/pmsteil/brightpearl_client.git

## Usage

Here are some examples of how to use the BrightPearl client:

### Initializing the client

```python
from brightpearl_client import BrightPearlClient
api_url = "https://use1.brightpearlconnect.com/public-api/nisolo/"
api_headers = {
"brightpearl-app-ref": "your_app_ref",
"brightpearl-account-token": "your_account_token"
}
client = BrightPearlClient(api_url, api_headers)

### Retrieving orders by status

```python
try:
response = client.get_orders_by_status(37) # 37 is an example status ID
print(f"Retrieved {len(response.response.results)} orders")
except ValueError as e:
print(f"Invalid input: {e}")
except BrightPearlApiError as e:
print(f"API error: {e}")

### Parsing order results

```python
response = client.get_orders_by_status(37)
parsed_results = client.parse_order_results(response)
for order in parsed_results:
print(f"Order ID: {order.orderId}")
print(f"Order Type ID: {order.order_type_id}")
print(f"Contact ID: {order.contact_id}")
print(f"Order Status ID: {order.order_status_id}")
print(f"Order Stock Status ID: {order.order_stock_status_id}")
print("---")

### Error handling

The client raises `BrightPearlApiError` for API-related errors:

```python
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

## License

This project is licensed under the MIT License.
This updated README provides a comprehensive guide on how to install, use, and develop with the BrightPearl client. It includes examples for initializing the client, retrieving orders by status, parsing order results, and handling errors. It also provides information about development setup and licensing.
To apply this update:
Open the README.md file in your project directory.
Replace the entire contents of the file with the markdown provided above.
Save the file.
After making these changes, commit the updated README.md file to your repository:
git add README.md
git commit -m "Update README with comprehensive usage examples and development instructions"
git push
This should resolve the issue with the README not being updated.
