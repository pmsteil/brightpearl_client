import os
import logging
import json
from dotenv import load_dotenv
from brightpearl_client import BrightPearlClient
from brightpearl_client.base_client import BrightPearlApiError  # Add this import

# Control logging to screen

# Set global logging level to WARNING
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Enable INFO logging for specific modules if needed
logging.getLogger('brightpearl_client.client').setLevel(logging.INFO)

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
        rate_limit=1
    )

    print(f"Initialized BrightPearl client with API URL: {api_base_url}")

    # Test warehouse inventory download
    print("\nTesting warehouse inventory download...")
    try:
        warehouse_id = 18
        inventory = client.warehouse_inventory_download(warehouse_id)
        print(f"Retrieved inventory for warehouse {warehouse_id}:")
        print(f"  Total products with inventory: {len(inventory)}")
        print("  Sample of inventory data:")
        for product_id, inventory_data in list(inventory.items())[:3]:
            print(f"    Product ID: {product_id}")
            print(f"      In Stock: {inventory_data['inStock']}")
            print(f"      On Hand: {inventory_data['onHand']}")
            print(f"      Allocated: {inventory_data['allocated']}")
            print(f"      In Transit: {inventory_data['inTransit']}")
        # save the warehouse inventory to a separate JSON file
        with open(f'warehouse_inventory_{warehouse_id}.json', 'w') as f:
            json.dump(inventory, f, indent=2)
        print(f"Full results saved to 'warehouse_inventory_{warehouse_id}.json'")

    except BrightPearlApiError as e:
        print(f"API error: {e}")
        print("Please check the following:")
        print("1. The warehouse ID is valid and exists in your BrightPearl account.")
        print("2. You have the necessary permissions to access inventory data.")
        print("3. The API endpoint is correct for your BrightPearl account.")
    except Exception as e:
        raise e

    exit(0)

    # Get all live products (with caching)
    print("\nRetrieving all live products...")
    try:
        live_products = client.get_all_live_products()
        print(f"Retrieved {len(live_products)} live products, first 5 shown below:")

        # Print details of the first 5 live products
        for product in live_products[:5]:
            print(f"  Product ID: {product['productId']}")
            print(f"  Name: {product['productName']}")
            print(f"  SKU: {product['SKU']}")
            print(f"  UPC: {product['UPC']}")
            print("")


    except BrightPearlApiError as e:
        print(f"API error: {e}")
        print("Please check the following:")
        print("1. You have the necessary permissions to access product data.")
        print("2. The API endpoint is correct for your BrightPearl account.")
    except Exception as e:
        print(f"Unexpected error: {e}")




    # Test product search
    print("\nTesting product search...")
    try:
        product_search_result = client.search_products()
        print(f"Retrieved {len(product_search_result.products)} products")
        print(f"Total results available: {product_search_result.metadata.resultsAvailable}")

        # Print details of the first 5 products
        for product in product_search_result.products[:5]:
            print(f"  Product ID: {product['productId']}")
            print(f"  Name: {product['productName']}")
            print(f"  SKU: {product['SKU']}")
            print(f"  Created On: {product['createdOn']}")
            print("  ---")

        # Save the full response to a JSON file
        with open('product_search_results.json', 'w') as f:
            json.dump(product_search_result.dict(), f, indent=2, default=str)
        print("Full results saved to 'product_search_results.json'")

    except BrightPearlApiError as e:
        print(f"API error: {e}")
        print("Please check the following:")
        print("1. You have the necessary permissions to access product data.")
        print("2. The API endpoint is correct for your BrightPearl account.")
    except Exception as e:
        print(f"Unexpected error: {e}")


    # Test product availability retrieval
    print("\nTesting product availability retrieval...")
    try:
        products = [1007, 1008]
        availability = client.get_product_availability(products)
        print(f"Retrieved availability for products {products}:")
        for product_id, product_info in availability.items():
            print(f"  Product ID: {product_id}")
            print(f"    Total in stock: {product_info['total']['inStock']}")
            print(f"    Total on hand: {product_info['total']['onHand']}")
            print(f"    Total allocated: {product_info['total']['allocated']}")
            print(f"    Total in transit: {product_info['total']['inTransit']}")
            print("    Warehouse breakdown:")
            for warehouse_id, warehouse_info in product_info['warehouses'].items():
                print(f"      Warehouse {warehouse_id}:")
                print(f"        In stock: {warehouse_info['inStock']}")
                print(f"        On hand: {warehouse_info['onHand']}")
                print(f"        Allocated: {warehouse_info['allocated']}")
                print(f"        In transit: {warehouse_info['inTransit']}")
    except BrightPearlApiError as e:
        print(f"API error: {e}")
        print("Please check the following:")
        print("1. The product IDs are valid and exist in your BrightPearl account.")
        print("2. You have the necessary permissions to access this data.")
        print("3. The API endpoint is correct for your BrightPearl account.")
    except Exception as e:
        print(f"Unexpected error: {e}")

    exit(0)

    # Get orders with parsed results
    parsed_orders = client.get_orders_by_status(23)
    print(f"\nRetrieved {len(parsed_orders)} parsed orders with status 23:")
    for order in parsed_orders[:5]:  # Print first 5 orders
        print(f"  Order ID: {order.orderId}, Type: {order.order_type_id}, Status: {order.order_status_id}")

    # Get orders without parsing
    raw_response = client.get_orders_by_status(38, parse_api_results=False)
    print(f"\nRetrieved {len(raw_response.response.results)} raw orders with status 38")

    # Test rate limiting
    print("\nTesting rate limiting...")
    for i in range(5):
        orders = client.get_orders_by_status(23)
        print(f"  Request {i+1}: Retrieved {len(orders)} orders")


if __name__ == "__main__":
    main()
