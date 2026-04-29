"""
Simple Similar Products Implementation (Disabled: products not in Postgres).
"""

import structlog
from typing import Any, Dict, List

logger = structlog.get_logger()


def get_similar_products_simple(product_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get similar products (Disabled: products not in PostgreSQL)
    """
    logger.warning("Simple similar products lookup skipped - products not in PostgreSQL", product_id=product_id)
    return []
