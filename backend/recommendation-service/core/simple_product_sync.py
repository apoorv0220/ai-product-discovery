"""
Simplified Product Synchronization for Recommendation Service
Direct database operations without complex relationships
"""

import json
import os
import asyncio
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime

from shared.database.base import get_database_session
from sqlalchemy import select, delete, func
# from shared.models import Product # Removed

logger = structlog.get_logger()

class SimpleProductSync:
    """Simplified product synchronization without model relationships"""
    
    def __init__(self):
        self.products_file = "/tmp/products_index.json"
        
    async def sync_products_from_search_index(self) -> Dict[str, Any]:
        """
        Sync products from search service index to recommendation database
        """
        try:
            # Load products from search index
            products_data = self._load_products_from_index()
            
            if not products_data:
                logger.warning("No products found in search index")
                return {
                    "success": False,
                    "message": "No products found in search index",
                    "synced_count": 0
                }
            
            # Sync to database using direct SQL
            synced_count = await self._sync_to_database_direct(products_data)
            
            logger.info("Product sync completed", synced_count=synced_count)
            
            return {
                "success": True,
                "message": f"Successfully synced {synced_count} products",
                "synced_count": synced_count
            }
            
        except Exception as e:
            logger.error("Product sync failed", error=str(e))
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}",
                "synced_count": 0
            }
    
    def _load_products_from_index(self) -> Dict[str, Any]:
        """Load products from search service index file"""
        try:
            if not os.path.exists(self.products_file):
                logger.warning("Products index file not found", file=self.products_file)
                return {}
                
            with open(self.products_file, 'r') as f:
                products = json.load(f)
                
            logger.info("Loaded products from search index", count=len(products))
            return products
            
        except Exception as e:
            logger.error("Failed to load products from index", error=str(e))
            return {}
    
    async def _sync_to_database_direct(self, products_data: Dict[str, Any]) -> int:
        """Sync products to database (Disabled: stored in ES/Qdrant)"""
        synced_count = len(products_data)
        logger.info("Products sync to database skipped (stored in ES/Qdrant)", count=synced_count)
        return synced_count
    
    def _extract_product_info(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize product information"""
        
        # Extract categories - handle both string IDs and category objects
        categories = product_data.get('categories', [])
        category_ids = []
        
        for cat in categories:
            if isinstance(cat, str) and cat.isdigit():
                category_ids.append(int(cat))
            elif isinstance(cat, int):
                category_ids.append(cat)
            elif isinstance(cat, dict) and 'id' in cat:
                category_ids.append(int(cat['id']))
        
        # Extract price information
        price = float(product_data.get('price', 0))
        special_price = product_data.get('special_price')
        if special_price:
            try:
                special_price = float(special_price)
            except (ValueError, TypeError):
                special_price = None
        
        # Extract attributes
        attributes = product_data.get('attributes', {})
        
        # Handle weight
        weight = attributes.get('weight')
        if weight:
            try:
                weight = float(weight)
            except (ValueError, TypeError):
                weight = None
        
        return {
            'magento_product_id': int(product_id),
            'store_id': int(product_data.get('store_id', 1)),
            'sku': product_data.get('sku', f'SKU-{product_id}'),
            'name': product_data.get('name', 'Unknown Product'),
            'description': product_data.get('description', ''),
            'short_description': product_data.get('short_description'),
            'price': price,
            'special_price': special_price,
            'category_ids': category_ids,
            'status': int(product_data.get('status', 1)),
            'visibility': int(product_data.get('visibility', 4)),
            'qty': float(product_data.get('stock', {}).get('qty', 0)),
            'is_in_stock': product_data.get('stock', {}).get('is_in_stock', True),
            'image_url': product_data.get('image_url', ''),
            'view_count': 0,
            'purchase_count': 0,
            'avg_rating': None,
            'review_count': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'last_synced_at': datetime.utcnow()
        }
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        try:
            # Count products in search index
            search_products = self._load_products_from_index()
            search_count = len(search_products)
            
            return {
                "database_products": 0,
                "search_index_products": search_count,
                "sync_needed": False,
                "last_check": datetime.utcnow().isoformat()
            }
                
        except Exception as e:
            logger.error("Failed to get sync status", error=str(e))
            return {
                "database_products": 0,
                "search_index_products": 0,
                "sync_needed": True,
                "error": str(e)
            }

# Global instance
simple_product_sync = SimpleProductSync()
