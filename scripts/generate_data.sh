#!/bin/bash

# Configuration
API_URL="http://localhost:7097/api/v1/tracking"
# Use the default test key or your generated live key
AUTH_TOKEN="Bearer sk_YnsYYfGYKIsii-xjfoWfHjhAWKDOo7ksxq_aJT0Fll0"

platforms=("magento" "shopify" "woocommerce")
devices=("mobile" "desktop" "tablet")
events=("product_view" "search_query" "search_click" "add_to_cart" "purchase")

echo "🚀 Starting data generation for Phase 2A testing..."

for i in {1..1000}
do
    PLATFORM=${platforms[$((i % 3))]}
    DEVICE=${devices[$((i % 3))]}
    EVENT_TYPE=${events[$((i % 5))]}
    
    # Map event type to endpoint and build type-specific payload
    case $EVENT_TYPE in
        "product_view")
            ENDPOINT="product-view"
            EXTRA_FIELDS='"product_id": '$i', "product_name": "Product '$i'", "product_sku": "SKU-'$i'"'
            ;;
        "search_query")
            ENDPOINT="search-query"
            EXTRA_FIELDS='"query": "test query '$i'", "results_count": '$((i % 50))''
            ;;
        "search_click")
            ENDPOINT="search-click"
            EXTRA_FIELDS='"search_query": "test query '$i'", "clicked_product_id": '$i', "position_in_results": '$((i % 10 + 1))''
            ;;
        "add_to_cart")
            ENDPOINT="add-to-cart"
            EXTRA_FIELDS='"product_id": '$i''
            ;;
        "purchase")
            ENDPOINT="purchase"
            EXTRA_FIELDS='"product_id": '$i', "revenue": '$(( (RANDOM % 100) + 10 )).99''
            ;;
    esac
    
    # Construct JSON
    JSON_BODY=$(cat <<EOF
    {
        "session_id": "sess_phase2a_test_$((i / 10))",
        "user_id": "user_test_$((i / 25))",
        "platform": "$PLATFORM",
        "device_type": "$DEVICE",
        "ip_address": "192.168.1.$((i % 255))",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        $EXTRA_FIELDS
    }
EOF
    )

    # Send Request
    curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/$ENDPOINT" \
         -H "Authorization: $AUTH_TOKEN" \
         -H "Content-Type: application/json" \
         -d "$JSON_BODY" | grep -q "200" || echo "Error on event $i (Type: $EVENT_TYPE)"

    if [ $((i % 100)) -eq 0 ]; then
        echo "✅ Generated $i events..."
    fi
done

echo "🏁 Done. Waiting for background aggregation (approx 15s)..."
sleep 15
