# BrightPearl Client

A Python client for interacting with the BrightPearl API.

## Installation

To install the BrightPearl client, you can use pip:

```
pipenv install git+https://github.com/pmsteil/brightpearl_client.git
pipenv install python-fasthtml
```

## Usage

Here's a basic example of how to use the BrightPearl client:

```
from brightpearl_client import BrightPearlClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

api_base_url = os.getenv("BRIGHTPEARL_API_URL")
brightpearl_app_ref = os.getenv("BRIGHTPEARL_APP_REF")
brightpearl_account_token = os.getenv("BRIGHTPEARL_ACCOUNT_TOKEN")

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

## Available Methods

### 1. Stock Correction

Perform a stock correction for specified products.

```
corrections = [
    {
        "productId": 1007,
        "new_quantity": 15,
        "reason": "Inventory Sync"
    },
    {
        "sku": "1HBON085",
        "new_quantity": 20,
        "reason": "Inventory Sync"
    }
]
result = client.stock_correction(warehouse_id, corrections)
```

### 2. Warehouse Inventory Download

Download inventory information for a specific warehouse.

```
warehouse_id = 3
inventory = client.warehouse_inventory_download(warehouse_id)
```

### 3. Get All Live Products

Retrieve all live products from BrightPearl.

```
live_products = client.get_all_live_products()
```

### 4. Search Products

Search for products with optional filters.

```
product_search_result = client.search_products()
```

### 5. Get Product Availability (Inventory)

Retrieve availability information for specific products.

```
products = [1007, 1008]
availability = client.get_product_availability(products)
```

### 6. Get Orders by Status

Retrieve orders with a specific status.

```
parsed_orders = client.get_orders_by_status(23)
```

### 7. Download All Products and Sync Inventory Between Warehouses

Here's an example of how to download all products and sync inventory between two warehouses:

```
#### Get all live products
live_products = client.get_all_live_products()

#### Define source and destination warehouse IDs
source_warehouse_id = 1
destination_warehouse_id = 2

#### Get inventory for both warehouses
source_inventory = client.warehouse_inventory_download(source_warehouse_id)
destination_inventory = client.warehouse_inventory_download(destination_warehouse_id)

#### Prepare corrections list
corrections = []

for product in live_products:
    product_id = product['productId']
    sku = product['SKU']

    source_quantity = source_inventory.get(product_id, {}).get('inventory_onHand', 0)
    destination_quantity = destination_inventory.get(product_id, {}).get('inventory_onHand', 0)

    if source_quantity != destination_quantity:
        corrections.append({
            "productId": product_id,
            "new_quantity": source_quantity,
            "reason": f"Sync inventory from Warehouse {source_warehouse_id} to {destination_warehouse_id}"
        })

#### Apply corrections to destination warehouse
if corrections:
    result = client.stock_correction(destination_warehouse_id, corrections)
    print(f"Synced {len(corrections)} products between warehouses {source_warehouse_id} and {destination_warehouse_id}")
else:
    print("No inventory differences found between warehouses")
```

## Error Handling

The client raises `BrightPearlApiError` for API-related errors:

```
from brightpearl_client.base_client import BrightPearlApiError

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
10. Copy the "Reference" field value. This is the `BRIGHTPEARL_APP_REF`. This will be different from the Identifier you provided above.
11. Copy the "Token" displayed on the screen. This is the `BRIGHTPEARL_ACCOUNT_TOKEN`
12. Configure your three ENV variables accordingly, for example:
    BRIGHTPEARL_API_URL="https://use1.brightpearlconnect.com/public-api/account_name/"
    BRIGHTPEARL_APP_REF="accountname_python_api_client"
    BRIGHTPEARL_ACCOUNT_TOKEN="1234567890"

## License

This project is licensed under the MIT License.
