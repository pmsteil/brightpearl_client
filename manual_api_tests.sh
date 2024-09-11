#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Check if required environment variables are set
if [ -z "$BRIGHTPEARL_API_URL" ] || [ -z "$BRIGHTPEARL_APP_REF" ] || [ -z "$BRIGHTPEARL_ACCOUNT_TOKEN" ]; then
    echo "Error: Missing required environment variables. Please check your .env file."
    exit 1
fi

# Remove protocol and trailing slash from API_URL if present
API_URL=$(echo $BRIGHTPEARL_API_URL | sed -e 's#^https?://##' -e 's#/$##')

# Set API endpoint and product ID
API_ENDPOINT="${API_URL}/warehouse-service/product-availability/1007"

# Make the API request
curl -X GET "$API_ENDPOINT" \
     -H "brightpearl-app-ref: ${BRIGHTPEARL_APP_REF}" \
     -H "brightpearl-account-token: ${BRIGHTPEARL_ACCOUNT_TOKEN}" \
     -H "Content-Type: application/json"



# Set API endpoint and product ID
API_ENDPOINT="${API_URL}/warehouse-service/product-availability"

# Make the API request
curl -X GET "$API_ENDPOINT" \
     -H "brightpearl-app-ref: ${BRIGHTPEARL_APP_REF}" \
     -H "brightpearl-account-token: ${BRIGHTPEARL_ACCOUNT_TOKEN}" \
     -H "Content-Type: application/json"

# {"errors":[{"code":"WHSC-020","message":"You must specify at least one product Id when performing an availability check"}]}

# Add a newline for better readability of output
echo
