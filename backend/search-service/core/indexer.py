"""
Product indexing pipeline using Elasticsearch bulk helpers.
"""

from typing import Any, Dict, List, Tuple
import asyncio
import structlog

from .elasticsearch_client import ElasticsearchManager

logger = structlog.get_logger()


class IndexResult:
    def __init__(self, success_count: int, failure_count: int, errors: List[Dict[str, Any]]):
        self.success_count = success_count
        self.failure_count = failure_count
        self.errors = errors


class ProductIndexer:
    def __init__(self, es_client: ElasticsearchManager):
        self.es = es_client
        self.batch_size = 500

    def _doc_id(self, merchant_id: int, product: Dict[str, Any]) -> str:
        product_id = product.get("id") or product.get("product_id") or product.get("sku")
        return f"{merchant_id}_{product_id}"

    def _to_doc(self, merchant_id: int, product: Dict[str, Any]) -> Dict[str, Any]:
        # DIAGNOSTIC: Log input fields vs output fields
        input_fields = set(product.keys())
        
        # Handle stock data (can be dict or boolean)
        stock_data = product.get("stock", {})
        if isinstance(stock_data, dict):
            in_stock = bool(stock_data.get("is_in_stock", True))
            stock_qty = float(stock_data.get("qty", 0))
            manage_stock = stock_data.get("manage_stock")
        else:
            in_stock = bool(stock_data)
            stock_qty = 0
            manage_stock = None
        
        # Normalize categories - Elasticsearch mapping expects list of strings
        raw_categories = product.get("categories", [])
        category_names: List[str] = []
        category_ids: List[str] = []

        if isinstance(raw_categories, list):
            for cat in raw_categories:
                if isinstance(cat, dict):
                    cat_name = cat.get("name") or cat.get("title")
                    if cat_name:
                        category_names.append(str(cat_name))
                    cat_id = cat.get("id")
                    if cat_id is not None and cat_id != "":
                        category_ids.append(str(cat_id))
                elif cat:
                    category_names.append(str(cat))
        elif raw_categories:
            category_names.append(str(raw_categories))

        # Remove duplicates while preserving order
        if category_names:
            seen = set()
            category_names = [name for name in category_names if not (name in seen or seen.add(name))]
        if category_ids:
            seen_ids = set()
            category_ids = [cat_id for cat_id in category_ids if not (cat_id in seen_ids or seen_ids.add(cat_id))]

        # Extract attributes for processing
        attributes_dict = product.get("attributes", {})
        
        # Build comprehensive document with ALL fields from Magento
        doc = {
            "merchant_id": merchant_id,
            "product_id": str(product.get("id", product.get("product_id", ""))),
            "sku": product.get("sku", ""),
            "name": product.get("name", ""),
            "description": product.get("description", ""),
            "short_description": product.get("short_description", ""),
            
            # Pricing - include ALL price fields from Magento
            "price": float(product.get("price", 0.0)) if product.get("price") is not None else 0.0,
            "special_price": float(product.get("special_price")) if product.get("special_price") else None,
            "final_price": float(product.get("final_price", 0.0)) if product.get("final_price") is not None else None,
            "currency": product.get("currency", "USD"),
            
            # Media and URLs
            "url": product.get("url", ""),
            "image_url": product.get("image_url", ""),
            
            # Categorization
            "categories": category_names,
            "category_ids": category_ids,
            "brand": attributes_dict.get("manufacturer") or product.get("brand"),
            
            # Stock information
            "in_stock": in_stock,
            "stock_quantity": stock_qty,
            "manage_stock": manage_stock,
            
            # Reviews and ratings
            "avg_rating": float(product.get("avg_rating")) if product.get("avg_rating") is not None else None,
            "review_count": int(product.get("review_count", 0)) if product.get("review_count") is not None else 0,
            
            # Attributes - preserve all custom attributes
            "attributes": attributes_dict,
            
            # Flattened attributes for faceting - extract from attributes object
            "attr_color": self._extract_attribute_values(attributes_dict, "color"),
            "attr_size": self._extract_attribute_values(attributes_dict, "size"),
            "attr_material": self._extract_attribute_values(attributes_dict, "material"),
            "attr_pattern": self._extract_attribute_values(attributes_dict, "pattern"),
            "attr_climate": self._extract_attribute_values(attributes_dict, "climate"),
            
            # Status and visibility
            "status": int(product.get("status", 1)),
            "visibility": int(product.get("visibility", 4)),
            
            # Store context
            "store_id": int(product.get("store_id")) if product.get("store_id") is not None else None,
            "website_id": int(product.get("website_id")) if product.get("website_id") is not None else None,
            
            # Metadata
            # Note: _version is a reserved Elasticsearch field, don't include it
            "created_at": product.get("created_at"),
            "updated_at": product.get("updated_at"),
        }
        
        # Parse dates - Magento sends "2024-01-01 00:00:00", ES needs ISO format
        if doc.get("created_at"):
            try:
                from datetime import datetime
                created_at = doc["created_at"]
                if isinstance(created_at, str):
                    # Try parsing Magento format "2024-01-01 00:00:00"
                    if ' ' in created_at and len(created_at) > 10:
                        dt = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        doc["created_at"] = dt.isoformat()
            except:
                pass  # Keep original if parsing fails
        
        if doc.get("updated_at"):
            try:
                from datetime import datetime
                updated_at = doc["updated_at"]
                if isinstance(updated_at, str):
                    if ' ' in updated_at and len(updated_at) > 10:
                        dt = datetime.strptime(updated_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        doc["updated_at"] = dt.isoformat()
            except:
                pass
        
        output_fields = set(doc.keys())
        # Fields we intentionally transform/flatten (don't count as unmapped)
        handled_fields = {'id', 'product_id', 'version', 'stock'}
        unmapped_fields = input_fields - handled_fields - output_fields
        
        # DIAGNOSTIC: Log field mapping for first product only (to avoid spam)
        if not hasattr(self, '_diagnostic_logged'):
            self._diagnostic_logged = True
            logger.info("DIAGNOSTIC: ProductIndexer field mapping",
                       input_fields=sorted(list(input_fields)),
                       output_fields=sorted(list(output_fields)),
                       unmapped_fields=sorted(list(unmapped_fields)) if unmapped_fields else [],
                       price_mapping={
                           "input_price": product.get("price"),
                           "input_special": product.get("special_price"),
                           "input_final": product.get("final_price"),
                           "output_price": doc["price"],
                           "output_special": doc["special_price"],
                           "output_final": doc["final_price"]
                       },
                       media_mapping={
                           "input_image": product.get("image_url"),
                           "output_image": doc["image_url"],
                           "input_url": product.get("url"),
                           "output_url": doc["url"]
                       },
                       categories_mapping={
                           "input": raw_categories,
                           "output": doc["categories"],
                           "category_ids": doc.get("category_ids")
                       },
                       stock_mapping={
                           "input": product.get("stock"),
                           "output": {
                               "in_stock": doc["in_stock"],
                               "qty": doc["stock_quantity"],
                               "manage": doc["manage_stock"]
                           }
                       },
                       store_mapping={
                           "store_id": doc["store_id"],
                           "website_id": doc["website_id"]
                       })
        
        return doc

    def _extract_attribute_values(self, attributes: Dict[str, Any], attr_key: str) -> List[str]:
        """Extract attribute values for faceting, handling both single values and arrays"""
        if not attributes or not isinstance(attributes, dict):
            return []
        
        value = attributes.get(attr_key)
        if not value:
            return []
        
        # Handle array values (multiselect attributes)
        if isinstance(value, list):
            # Filter out None, False, empty strings
            return [str(v) for v in value if v is not None and v != '' and v is not False]
        
        # Handle single value
        if value is not None and value != '' and value is not False:
            return [str(value)]
        
        return []

    async def index_products_bulk(self, merchant_id: int, products: List[Dict[str, Any]], refresh: bool = False) -> IndexResult:
        assert self.es.client is not None, "Elasticsearch client not initialized"

        # Ensure index exists (requires settings/mappings provided by caller)
        # Caller should have created index via ElasticsearchManager.ensure_index

        index = self.es.get_index_name(merchant_id)
        actions = []
        for p in products:
            doc_id = self._doc_id(merchant_id, p)
            doc = self._to_doc(merchant_id, p)
            actions.append({
                "_op_type": "index",
                "_index": index,
                "_id": doc_id,
                "_source": doc,
            })

        success_count = 0
        failure_count = 0
        errors: List[Dict[str, Any]] = []

        # Process in batches to control memory
        for i in range(0, len(actions), self.batch_size):
            batch = actions[i:i + self.batch_size]
            try:
                # async_bulk returns (successes, errors)
                successes, batch_errors = await self.es.bulk(batch)
                success_count += int(successes)
                if batch_errors:
                    failure_count += len(batch_errors)
                    errors.extend(batch_errors)
                    # Log first error for debugging with full details
                    if batch_errors and not hasattr(self, '_error_logged'):
                        self._error_logged = True
                        first_error = batch_errors[0]
                        # Extract error reason from Elasticsearch error structure
                        error_reason = "Unknown error"
                        if isinstance(first_error, dict):
                            if 'index' in first_error and 'error' in first_error['index']:
                                es_error = first_error['index']['error']
                                if isinstance(es_error, dict):
                                    error_reason = es_error.get('reason', str(es_error))
                                else:
                                    error_reason = str(es_error)
                            elif 'error' in first_error:
                                error_reason = str(first_error['error'])
                            elif 'exception' in first_error:
                                error_reason = first_error['exception']
                        logger.error("Bulk index error sample", 
                                   merchant_id=merchant_id,
                                   error_reason=error_reason,
                                   full_error=first_error)
                logger.info("Bulk indexed batch", merchant_id=merchant_id, batch_count=len(batch), successes=successes, errors=len(batch_errors or []))
            except Exception as e:
                logger.error("Bulk index failed", merchant_id=merchant_id, error=str(e), error_type=type(e).__name__)
                failure_count += len(batch)
                errors.append({"exception": str(e), "error_type": type(e).__name__})

        if refresh:
            try:
                await self.es.refresh_index(merchant_id)
            except Exception:
                # Non-fatal
                pass

        return IndexResult(success_count=success_count, failure_count=failure_count, errors=errors)

    async def index_product(self, merchant_id: int, product: Dict[str, Any]) -> bool:
        return (await self.index_products_bulk(merchant_id, [product])).failure_count == 0

    async def delete_product(self, merchant_id: int, product_id: str) -> bool:
        assert self.es.client is not None, "Elasticsearch client not initialized"
        index = self.es.get_index_name(merchant_id)
        doc_id = f"{merchant_id}_{product_id}"
        try:
            await self.es._execute_with_retry(self.es.client.delete, index=index, id=doc_id, ignore=[404])
            return True
        except Exception as e:
            logger.error("Delete product failed", merchant_id=merchant_id, product_id=product_id, error=str(e))
            return False

    async def update_product(self, merchant_id: int, product_id: str, partial_doc: Dict[str, Any]) -> bool:
        assert self.es.client is not None, "Elasticsearch client not initialized"
        index = self.es.get_index_name(merchant_id)
        doc_id = f"{merchant_id}_{product_id}"
        try:
            await self.es._execute_with_retry(self.es.client.update, index=index, id=doc_id, doc={"doc": partial_doc})
            return True
        except Exception as e:
            logger.error("Update product failed", merchant_id=merchant_id, product_id=product_id, error=str(e))
            return False



