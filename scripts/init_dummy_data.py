#!/usr/bin/env python3
"""
Initialize the AI Product Discovery Suite with dummy data for localhost testing
"""

import asyncio
import json
import sys
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared.database.base import init_database, get_database_session
    from shared.models.product import Product, Category
    from shared.models.user import User, CustomerProfile
    from shared.models.analytics import AnalyticsEvent, UserSession
    from shared.models.search import SearchQuery, SearchLog
    from shared.models.recommendation import RecommendationLog
    import structlog
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logger = structlog.get_logger()

# Dummy data definitions
CATEGORIES = [
    {"name": "Electronics", "description": "Electronic devices and gadgets"},
    {"name": "Laptops", "description": "Laptop computers and accessories"},
    {"name": "Smartphones", "description": "Mobile phones and accessories"},
    {"name": "Tablets", "description": "Tablet computers and accessories"},
    {"name": "Gaming", "description": "Gaming consoles and accessories"},
    {"name": "Audio", "description": "Headphones, speakers, and audio equipment"},
    {"name": "Smart Home", "description": "Smart home devices and automation"},
    {"name": "Cameras", "description": "Digital cameras and photography equipment"},
]

PRODUCTS = [
    {
        "name": "MacBook Pro 16-inch",
        "description": "Apple MacBook Pro with M2 Max chip, 16-inch Liquid Retina XDR display",
        "price": 2499.00,
        "sku": "MBP16-M2MAX-001",
        "category": "Laptops",
        "stock_quantity": 15,
        "attributes": {
            "brand": "Apple",
            "processor": "M2 Max",
            "memory": "32GB",
            "storage": "1TB SSD",
            "display": "16-inch Liquid Retina XDR",
            "color": "Space Gray"
        }
    },
    {
        "name": "Dell XPS 13",
        "description": "Dell XPS 13 laptop with Intel Core i7, 13.4-inch display",
        "price": 1399.00,
        "sku": "DELL-XPS13-002",
        "category": "Laptops",
        "stock_quantity": 22,
        "attributes": {
            "brand": "Dell",
            "processor": "Intel Core i7",
            "memory": "16GB",
            "storage": "512GB SSD",
            "display": "13.4-inch FHD+",
            "color": "Platinum Silver"
        }
    },
    {
        "name": "iPhone 15 Pro",
        "description": "Apple iPhone 15 Pro with A17 Pro chip, 48MP camera system",
        "price": 999.00,
        "sku": "IPHONE15PRO-003",
        "category": "Smartphones",
        "stock_quantity": 45,
        "attributes": {
            "brand": "Apple",
            "storage": "128GB",
            "color": "Natural Titanium",
            "camera": "48MP Main",
            "display": "6.1-inch Super Retina XDR"
        }
    },
    {
        "name": "Samsung Galaxy S24 Ultra",
        "description": "Samsung Galaxy S24 Ultra with S Pen, 200MP camera",
        "price": 1199.00,
        "sku": "SAMSUNG-S24U-004",
        "category": "Smartphones",
        "stock_quantity": 32,
        "attributes": {
            "brand": "Samsung",
            "storage": "256GB",
            "color": "Titanium Black",
            "camera": "200MP Main",
            "display": "6.8-inch Dynamic AMOLED 2X"
        }
    },
    {
        "name": "iPad Pro 12.9-inch",
        "description": "Apple iPad Pro with M2 chip, 12.9-inch Liquid Retina XDR display",
        "price": 1099.00,
        "sku": "IPADPRO-129-005",
        "category": "Tablets",
        "stock_quantity": 18,
        "attributes": {
            "brand": "Apple",
            "processor": "M2",
            "storage": "256GB",
            "display": "12.9-inch Liquid Retina XDR",
            "color": "Space Gray"
        }
    },
    {
        "name": "Sony PlayStation 5",
        "description": "Sony PlayStation 5 gaming console with DualSense controller",
        "price": 499.00,
        "sku": "PS5-CONSOLE-006",
        "category": "Gaming",
        "stock_quantity": 8,
        "attributes": {
            "brand": "Sony",
            "storage": "825GB SSD",
            "resolution": "4K UHD",
            "features": "Ray Tracing, 3D Audio",
            "color": "White"
        }
    },
    {
        "name": "AirPods Pro (2nd Gen)",
        "description": "Apple AirPods Pro with Active Noise Cancellation",
        "price": 249.00,
        "sku": "AIRPODS-PRO2-007",
        "category": "Audio",
        "stock_quantity": 67,
        "attributes": {
            "brand": "Apple",
            "features": "Active Noise Cancellation",
            "battery": "6 hours + 24 hours with case",
            "connectivity": "Bluetooth 5.3",
            "color": "White"
        }
    },
    {
        "name": "Amazon Echo Dot (5th Gen)",
        "description": "Amazon Echo Dot smart speaker with Alexa",
        "price": 49.99,
        "sku": "ECHO-DOT5-008",
        "category": "Smart Home",
        "stock_quantity": 125,
        "attributes": {
            "brand": "Amazon",
            "assistant": "Alexa",
            "connectivity": "Wi-Fi, Bluetooth",
            "features": "Voice Control, Smart Home Hub",
            "color": "Charcoal"
        }
    },
    {
        "name": "Canon EOS R6 Mark II",
        "description": "Canon EOS R6 Mark II mirrorless camera with 24.2MP sensor",
        "price": 2499.00,
        "sku": "CANON-R6M2-009",
        "category": "Cameras",
        "stock_quantity": 12,
        "attributes": {
            "brand": "Canon",
            "sensor": "24.2MP Full-Frame CMOS",
            "video": "4K 60p",
            "autofocus": "Dual Pixel CMOS AF II",
            "color": "Black"
        }
    },
    {
        "name": "Microsoft Surface Pro 9",
        "description": "Microsoft Surface Pro 9 2-in-1 laptop with Intel Core i7",
        "price": 1599.00,
        "sku": "SURFACE-PRO9-010",
        "category": "Tablets",
        "stock_quantity": 19,
        "attributes": {
            "brand": "Microsoft",
            "processor": "Intel Core i7",
            "memory": "16GB",
            "storage": "512GB SSD",
            "display": "13-inch PixelSense",
            "color": "Platinum"
        }
    }
]

USERS = [
    {
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "preferences": {"categories": ["Electronics", "Laptops"], "price_range": [1000, 3000]}
    },
    {
        "email": "jane.smith@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "preferences": {"categories": ["Smartphones", "Audio"], "price_range": [200, 1200]}
    },
    {
        "email": "mike.wilson@example.com",
        "first_name": "Mike",
        "last_name": "Wilson",
        "preferences": {"categories": ["Gaming", "Electronics"], "price_range": [300, 800]}
    },
    {
        "email": "sarah.johnson@example.com",
        "first_name": "Sarah",
        "last_name": "Johnson",
        "preferences": {"categories": ["Cameras", "Tablets"], "price_range": [500, 2500]}
    },
    {
        "email": "alex.brown@example.com",
        "first_name": "Alex",
        "last_name": "Brown",
        "preferences": {"categories": ["Smart Home", "Audio"], "price_range": [50, 500]}
    }
]

SEARCH_QUERIES = [
    "MacBook laptop", "iPhone 15", "gaming console", "wireless headphones", 
    "smart speaker", "professional camera", "tablet computer", "smartphone Samsung",
    "Dell laptop", "iPad Pro", "PlayStation 5", "AirPods", "Echo Dot", "Canon camera"
]

async def create_categories(session) -> Dict[str, int]:
    """Create product categories and return name -> id mapping"""
    print("📂 Creating product categories...")
    category_ids = {}
    
    for cat_data in CATEGORIES:
        category = Category(
            name=cat_data["name"],
            description=cat_data["description"],
            is_active=True
        )
        session.add(category)
        await session.flush()
        category_ids[cat_data["name"]] = category.id
        print(f"   ✅ Category: {cat_data['name']}")
    
    return category_ids

async def create_products(session, category_ids: Dict[str, int]) -> List[int]:
    """Create products and return list of product IDs"""
    print("📦 Creating products...")
    product_ids = []
    
    for prod_data in PRODUCTS:
        category_id = category_ids.get(prod_data["category"])
        if not category_id:
            print(f"   ⚠️  Category not found for {prod_data['name']}")
            continue
            
        product = Product(
            name=prod_data["name"],
            description=prod_data["description"],
            price=prod_data["price"],
            sku=prod_data["sku"],
            category_id=category_id,
            stock_quantity=prod_data["stock_quantity"],
            attributes=prod_data["attributes"],
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(product)
        await session.flush()
        product_ids.append(product.id)
        print(f"   ✅ Product: {prod_data['name']} (${prod_data['price']})")
    
    return product_ids

async def create_users(session) -> List[int]:
    """Create users and return list of user IDs"""
    print("👥 Creating users...")
    user_ids = []
    
    for user_data in USERS:
        user = User(
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        
        # Create customer profile
        profile = CustomerProfile(
            user_id=user.id,
            preferences=user_data["preferences"],
            created_at=datetime.utcnow()
        )
        session.add(profile)
        
        user_ids.append(user.id)
        print(f"   ✅ User: {user_data['first_name']} {user_data['last_name']} ({user_data['email']})")
    
    return user_ids

async def create_search_logs(session, user_ids: List[int], product_ids: List[int]):
    """Create sample search logs"""
    print("🔍 Creating search logs...")
    
    for i, query in enumerate(SEARCH_QUERIES):
        user_id = random.choice(user_ids)
        
        search_query = SearchQuery(
            query=query,
            user_id=user_id,
            filters={},
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        )
        session.add(search_query)
        await session.flush()
        
        # Create corresponding search log
        search_log = SearchLog(
            query_id=search_query.id,
            user_id=user_id,
            results_count=random.randint(1, 10),
            response_time_ms=random.randint(50, 500),
            clicked_products=random.sample(product_ids, random.randint(0, 3)),
            created_at=search_query.created_at
        )
        session.add(search_log)
        print(f"   ✅ Search: '{query}' by user {user_id}")

async def create_analytics_events(session, user_ids: List[int], product_ids: List[int]):
    """Create sample analytics events"""
    print("📊 Creating analytics events...")
    
    event_types = ["product_view", "add_to_cart", "purchase", "search", "click"]
    
    for i in range(50):  # Create 50 events
        user_id = random.choice(user_ids)
        product_id = random.choice(product_ids)
        event_type = random.choice(event_types)
        
        # Create user session first
        session_obj = UserSession(
            user_id=user_id,
            session_id=f"session_{user_id}_{i}",
            started_at=datetime.utcnow() - timedelta(days=random.randint(1, 7)),
            last_activity=datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        )
        session.add(session_obj)
        await session.flush()
        
        # Create analytics event
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_obj.session_id,
            properties={
                "product_id": product_id,
                "page": "product_detail" if event_type == "product_view" else "search_results",
                "timestamp": datetime.utcnow().isoformat()
            },
            created_at=session_obj.started_at
        )
        session.add(event)
        
        if i % 10 == 0:
            print(f"   ✅ Created {i+1} analytics events...")

async def create_recommendation_logs(session, user_ids: List[int], product_ids: List[int]):
    """Create sample recommendation logs"""
    print("🤖 Creating recommendation logs...")
    
    contexts = ["home", "product_page", "cart", "checkout"]
    
    for i in range(25):  # Create 25 recommendation logs
        user_id = random.choice(user_ids)
        context = random.choice(contexts)
        recommended_products = random.sample(product_ids, random.randint(3, 8))
        
        rec_log = RecommendationLog(
            user_id=user_id,
            context=context,
            recommended_products=recommended_products,
            algorithm="hybrid",
            confidence_score=random.uniform(0.6, 0.95),
            clicked_products=random.sample(recommended_products, random.randint(0, 2)),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 14))
        )
        session.add(rec_log)
        
        if i % 5 == 0:
            print(f"   ✅ Created {i+1} recommendation logs...")

async def main():
    """Main function to initialize all dummy data"""
    print("🚀 Initializing AI Product Discovery Suite with dummy data...")
    print("=" * 60)
    
    try:
        # Initialize database
        await init_database()
        print("✅ Database initialized successfully")
        
        # Get database session
        async with get_database_session() as session:
            # Create all dummy data
            category_ids = await create_categories(session)
            product_ids = await create_products(session, category_ids)
            user_ids = await create_users(session)
            await create_search_logs(session, user_ids, product_ids)
            await create_analytics_events(session, user_ids, product_ids)
            await create_recommendation_logs(session, user_ids, product_ids)
            
            # Commit all changes
            await session.commit()
            print("\n✅ All dummy data created successfully!")
            
            # Print summary
            print("\n📊 SUMMARY:")
            print(f"   • Categories: {len(CATEGORIES)}")
            print(f"   • Products: {len(PRODUCTS)}")
            print(f"   • Users: {len(USERS)}")
            print(f"   • Search Queries: {len(SEARCH_QUERIES)}")
            print(f"   • Analytics Events: 50")
            print(f"   • Recommendation Logs: 25")
            
    except Exception as e:
        logger.error("Failed to initialize dummy data", error=str(e))
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())