import os
import logging
import json
import hashlib
from dotenv import load_dotenv
from brightpearl_client import BrightPearlClient
from brightpearl_client.base_client import BrightPearlApiError  # Add this import

# Control logging to screen
logging_level = logging.WARNING
logging_level = logging.DEBUG
logging_level = logging.ERROR
logging_level = logging.INFO

# Set global logging level to WARNING
logging.basicConfig(level=logging_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Enable INFO logging for specific modules if needed
logging.getLogger('brightpearl_client.client').setLevel(logging_level)

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


    # Get orders with parsed results
    parsed_orders, metadata = client.get_orders_by_status(4)
    print(f"\nRetrieved {len(parsed_orders)} parsed orders with status 4:")
    print(f"Orders available: {metadata.resultsAvailable}")
    for order in parsed_orders[:5]:  # Print first 5 orders
        print(f"  Order ID: {order.orderId}, Type: {order.order_type_id}, Status: {order.order_status_id}")

    # print( f"parsed_orders: {json.dumps(str(parsed_orders), indent=2)}")

    # exit(0)

    print("\nTesting stock correction...")
    try:
        warehouse_id = 3  # this one works: Nisolo DC
        location = "53" # 53 works with Nisolo DC... not sure why
        warehouse_id = 13  # JayGroupLCO doesn't like location 53
        location = "439"

        warehouse_id = 14 # JayGroupLCOPublic
        location = "442"

        # Get current inventory for the products we want to update
        product_ids = [1007,1008]
        current_inventory = client.get_product_availability(product_ids)

        # Find the SKU for product ID 1007
        sku_1007 = next((product['SKU'] for product in client.get_all_live_products() if product['productId'] == 1007), None)
        sku_1007_current_inventory = current_inventory[1007]['warehouses'].get(str(warehouse_id), {}).get('onHand', 0)

        # find the productId for SKU 1HBON085
        product_id_1hb085 = next((product['productId'] for product in client.get_all_live_products() if product['SKU'] == '1HBON085'), None)
        sku_1hb085_current_inventory = current_inventory[product_id_1hb085]['warehouses'].get(str(warehouse_id), {}).get('onHand', 0)

        current_state = {
            "1007": sku_1007_current_inventory,
            "1008": sku_1hb085_current_inventory
        }

        print(f"Current state: {current_state}")

        locations = client.warehouse_get_locations(warehouse_id)
        print(f"Locations for warehouse {warehouse_id}: {locations}")

        corrections = [
            # {
            #     "productId": 1007,
            #     "new_quantity": sku_1007_current_inventory + 10,
            #     "reason": "Test Sync"
            # }
            # ,
            # {
            #     "sku": "1HBON085",
            #     # "productId": product_id_1hb085,
            #     "new_quantity": sku_1hb085_current_inventory + 20,
            #     "reason": "Test Sync",
            #     # "locationId": location,
            #     # "cost": {
            #     #     "currency": "USD",
            #     #     "value": 0.00
            #     # }
            # }
            # ,
            {
                "sku": "1HBON095",
                "new_quantity": 0,
                "reason": "Test Sync",
            }
        ]

        print( f"corrections: {json.dumps(corrections, indent=2) }")

        result = client.stock_correction(warehouse_id, location, corrections)
        print(f"Correction IDs: {result}")


        # Generate cache prefix
        cache_prefix = hashlib.md5(brightpearl_app_ref.encode()).hexdigest()[:8]

        # After the stock correction
        for product_id in [1007, 1008]:
            cache_file = os.path.join(client._cache_dir, f'{cache_prefix}_product_availability_{product_id}_cache.json')
            if os.path.exists(cache_file):
                print(f"Warning: Cache file still exists for product ID {product_id}")
            else:
                print(f"Cache file successfully removed for product ID {product_id}")

    except BrightPearlApiError as e:
        print(f"API error: {e}")
        print("Please check the following:")
        print("1. The warehouse ID and product IDs/SKUs are valid and exist in your BrightPearl account.")
        print("2. You have the necessary permissions to perform stock corrections.")
        print("3. The API endpoint is correct for your BrightPearl account.")
        exit(1)
    except Exception as e:
        raise e







    # Test warehouse inventory download
    print("\nTesting warehouse inventory download...")
    try:
        warehouse_id = 3
        inventory = client.warehouse_inventory_download(warehouse_id)
        print(f"Retrieved inventory for warehouse {warehouse_id}:")
        print(f"  Total products with inventory: {len(inventory)}")
        print("  Sample of inventory data:")
        for product_id, product_data in list(inventory.items())[:3]:
            print(f"    Product ID: {product_id}")
            print(f"    SKU: {product_data.get('SKU', 'N/A')}")
            print(f"    Name: {product_data.get('productName', 'N/A')}")
            print(f"    In Stock: {product_data['inventory_inStock']}")
            print(f"    On Hand: {product_data['inventory_onHand']}")
            print(f"    Allocated: {product_data['inventory_allocated']}")
            print(f"    In Transit: {product_data['inventory_inTransit']}")
            print("    ---")
        # save the warehouse inventory to a separate JSON file
        with open(f'warehouse_inventory_{warehouse_id}.json', 'w') as f:
            json.dump(inventory, f, indent=2, sort_keys=True, default=str)
        print(f"Full results saved to 'warehouse_inventory_{warehouse_id}.json'")

    except BrightPearlApiError as e:
        print(f"API error: {e}")
        print("Please check the following:")
        print("1. The warehouse ID is valid and exists in your BrightPearl account.")
        print("2. You have the necessary permissions to access inventory data.")
        print("3. The API endpoint is correct for your BrightPearl account.")
    except Exception as e:
        raise e

    # exit(0)

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
            json.dump(product_search_result.dict(), f, indent=2, sort_keys=True, default=str)
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

    # exit(0)

    # Get orders with parsed results
    parsed_orders = client.get_orders_by_status(4)
    print(f"\nRetrieved {len(parsed_orders)} parsed orders with status 4 (invoiced):")

    # example parsed_orders: [ OrderResult(orderId=200001, order_type_id=1, contact_id=217582, order_status_id=4, order_stock_status_id=3) ]
    for order in parsed_orders[:5]:
        for order_item in order:
            if 'orderId' in order_item:
                print(f"order_item.orderId: {order_item.orderId}, order_item.order_status_id: {order_item.order_status_id}")
            # else:
            #     print(f"order_item: {order_item}")

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
