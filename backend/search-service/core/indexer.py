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
        return {
            "merchant_id": merchant_id,
            "product_id": str(product.get("id", product.get("product_id", ""))),
            "sku": product.get("sku", ""),
            "name": product.get("name", ""),
            "description": product.get("description", ""),
            "short_description": product.get("short_description", ""),
            "price": product.get("price", 0.0),
            "special_price": product.get("special_price"),
            "currency": product.get("currency", "USD"),
            "categories": product.get("categories", []),
            "brand": product.get("brand"),
            "status": product.get("status", 1),
            "visibility": product.get("visibility", 4),
            "in_stock": bool(product.get("stock", {}).get("is_in_stock", True)),
            "stock_quantity": product.get("stock", {}).get("qty", 0),
            "attributes": product.get("attributes", {}),
            "url": product.get("url", ""),
            "image_url": product.get("image_url", ""),
            "_version": int(product.get("version", 1)),
            "created_at": product.get("created_at"),
            "updated_at": product.get("updated_at"),
        }

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
                logger.info("Bulk indexed batch", merchant_id=merchant_id, batch_count=len(batch), successes=successes, errors=len(batch_errors or []))
            except Exception as e:
                logger.error("Bulk index failed", merchant_id=merchant_id, error=str(e))
                failure_count += len(batch)
                errors.append({"exception": str(e)})

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



