"""
Product Synchronization for Recommendation Service
Syncs products from search index to recommendation database
"""

import json
import os
import asyncio
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime

from shared.database.base import get_database_session
from shared.models.product import Product
from sqlalchemy import select, delete, insert, update
from sqlalchemy.exc import IntegrityError

logger = structlog.get_logger()

class ProductSyncManager:
    """Manages product synchronization for recommendations"""
    
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
            
            # Sync to database
            synced_count = await self._sync_to_database(products_data)
            
            # Update product similarities if we have enough products
            if synced_count > 5:
                await self._calculate_product_similarities(products_data)
            
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
    
    async def _sync_to_database(self, products_data: Dict[str, Any]) -> int:
        """Sync products to recommendation database"""
        synced_count = 0
        
        try:
            session_generator = get_database_session()
            session = await session_generator.__anext__()
            
            try:
                # Clear existing products
                await session.execute(delete(Product))
                
                # Insert new products
                for product_id, product_data in products_data.items():
                    try:
                        # Extract and clean product data
                        product_info = self._extract_product_info(product_id, product_data)
                        
                        # Create product record
                        new_product = Product(**product_info)
                        session.add(new_product)
                        synced_count += 1
                        
                    except Exception as e:
                        logger.warning("Failed to sync product", 
                                     product_id=product_id, 
                                     error=str(e))
                        continue
                
                await session.commit()
                logger.info("Products synced to database", count=synced_count)
                
            finally:
                await session.close()
                
        except Exception as e:
            logger.error("Database sync failed", error=str(e))
            raise
            
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
        
        return {
            'id': int(product_id),
            'sku': product_data.get('sku', f'SKU-{product_id}'),
            'name': product_data.get('name', 'Unknown Product'),
            'description': product_data.get('description', ''),
            'short_description': product_data.get('short_description'),
            'price': price,
            'special_price': special_price,
            'currency': product_data.get('currency', 'USD'),
            'category_ids': category_ids,
            'status': int(product_data.get('status', 1)),
            'visibility': int(product_data.get('visibility', 4)),
            'weight': attributes.get('weight'),
            'manufacturer': attributes.get('manufacturer'),
            'color': attributes.get('color'),
            'size': attributes.get('size'),
            'material': attributes.get('material'),
            'style': attributes.get('style'),
            'avg_rating': None,  # Will be calculated from user interactions
            'review_count': 0,
            'view_count': 0,
            'sale_count': 0,
            'stock_qty': product_data.get('stock', {}).get('qty', 0),
            'is_in_stock': product_data.get('stock', {}).get('is_in_stock', True),
            'image_url': product_data.get('image_url', ''),
            'url': product_data.get('url', ''),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    
    async def _calculate_product_similarities(self, products_data: Dict[str, Any]):
        """Calculate and store product similarities for content-based recommendations"""
        try:
            from similarity_calculator import SimilarityCalculator
            
            calculator = SimilarityCalculator()
            await calculator.calculate_similarities(products_data)
            
            logger.info("Product similarities calculated")
            
        except Exception as e:
            logger.warning("Failed to calculate product similarities", error=str(e))
            # Don't fail the entire sync if similarity calculation fails
            pass
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        try:
            session_generator = get_database_session()
            session = await session_generator.__anext__()
            
            try:
                # Count products in database
                result = await session.execute(select(Product.id))
                db_count = len(result.all())
                
                # Count products in search index
                search_products = self._load_products_from_index()
                search_count = len(search_products)
                
                return {
                    "database_products": db_count,
                    "search_index_products": search_count,
                    "sync_needed": db_count != search_count,
                    "last_check": datetime.utcnow().isoformat()
                }
            finally:
                await session.close()
                
        except Exception as e:
            logger.error("Failed to get sync status", error=str(e))
            return {
                "database_products": 0,
                "search_index_products": 0,
                "sync_needed": True,
                "error": str(e)
            }

# Global instance
product_sync_manager = ProductSyncManager()
