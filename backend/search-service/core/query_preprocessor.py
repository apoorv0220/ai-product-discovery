"""
Query preprocessing for normalization and simple intent detection.
"""

import re
import unicodedata


class QueryPreprocessor:
    def normalize_query(self, query: str) -> str:
        q = (query or "").strip().lower()
        q = unicodedata.normalize("NFC", q)
        q = re.sub(r"[^\w\s\-]", " ", q)
        q = re.sub(r"\s+", " ", q)
        return q

    def detect_intent(self, query: str) -> str:
        q = (query or "").lower()
        if any(k in q for k in ["buy", "cheap", "discount", "sale"]):
            return "buy"
        if any(k in q for k in ["compare", "vs", "versus"]):
            return "compare"
        return "browse"

    def expand_synonyms(self, query: str) -> str:
        # Phase 1: rely on ES synonyms; keep as passthrough
        return query



