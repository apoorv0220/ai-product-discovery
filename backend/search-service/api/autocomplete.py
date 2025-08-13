"""
AI Product Discovery Suite - Search Service Autocomplete API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, Query, Body
from pydantic import BaseModel
from typing import List, Optional
import structlog
import json
import os

logger = structlog.get_logger()
router = APIRouter()

# Use the same storage as the index API
PRODUCTS_FILE = "/tmp/products_index.json"

def load_products():
    """Load products from storage"""
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error("Error loading products for autocomplete", error=str(e))
    return {}

def get_autocomplete_suggestions(query: str, limit: int = 10):
    """Get real autocomplete suggestions from indexed products"""
    # Load current products
    products = load_products()
    
    if not query.strip():
        return []
    
    query_lower = query.lower()
    suggestions = []
    
    # Check if we have any products
    if not products:
        logger.warning("No products found in index for autocomplete", query=query)
        return []
    
    for product_id, product in products.items():
        product_name = product.get('name', '')
        searchable_text = product.get('searchable_text', product_name.lower())
        
        # Check if query matches product name or searchable text
        if query_lower in product_name.lower() or query_lower in searchable_text:
            # Format price for display
            price = product.get('price', 0)
            currency = product.get('currency', 'USD')
            formatted_price = f"${price:.2f}" if price else "$0.00"
            
            # Get primary category name (not ID)
            categories = product.get('categories', [])
            if categories:
                # If categories is a list of dicts with name/id, extract name
                if isinstance(categories[0], dict):
                    primary_category = categories[0].get('name', categories[0].get('title', 'General'))
                else:
                    # If it's just a list of strings/names
                    primary_category = categories[0]
            else:
                primary_category = 'General'
            
            suggestions.append({
                'suggestion': product_name,
                'title': product_name,
                'type': 'product',
                'count': 1,
                'id': product.get('id', 0),
                'sku': product.get('sku', ''),
                'price': formatted_price,
                'raw_price': price,
                'currency': currency,
                'image': product.get('image_url', ''),
                'url': product.get('url', ''),
                'category': primary_category,
                'categories': categories
            })
    
    # Sort by relevance (how close the match is to the beginning of the name)
    def relevance_score(item):
        name = item['suggestion'].lower()
        pos = name.find(query_lower)
        return (-pos if pos >= 0 else 999, len(name))  # Prefer matches at start, then shorter names
    
    suggestions.sort(key=relevance_score)
    return suggestions[:limit]


class AutocompleteResult(BaseModel):
    """Autocomplete result model"""
    suggestion: str
    type: str  # 'product', 'category', 'brand'
    count: int
    # Extended fields for Magento compatibility
    title: Optional[str] = None
    image: Optional[str] = None
    price: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    id: Optional[int] = None


class AutocompleteResponse(BaseModel):
    """Autocomplete response model"""
    suggestions: List[AutocompleteResult]
    query: str

class AutocompleteRequest(BaseModel):
    """Autocomplete request model for POST requests"""
    q: Optional[str] = None
    query: Optional[str] = None  # Alternative field name for compatibility
    limit: Optional[int] = 10
    
    def get_query(self) -> str:
        """Get the query value from either q or query field"""
        return self.q or self.query or ""


async def _process_autocomplete_request(q: str, limit: int = 10):
    """Internal function to process autocomplete requests with NLP enhancement"""
    try:
        logger.info("Getting NLP-enhanced autocomplete suggestions", query=q)
        
        # Try NLP-enhanced autocomplete first
        try:
            from ..core.nlp_processor import AdvancedNLPProcessor
            nlp_processor = AdvancedNLPProcessor()
            
            # Process query for typos and intent
            intent, corrections = await nlp_processor.process_search_query(q)
            
            # Use corrected query if available
            processed_query = intent.processed_query if intent else q
            
            # Get suggestions using processed query
            suggestions_data = get_autocomplete_suggestions(processed_query, limit)
            
            # If original query had typos, prioritize corrected suggestions
            if corrections and len(corrections) > 0:
                # Get the best correction
                best_correction = corrections[0]
                
                if best_correction.corrected.lower() != q.lower():
                    logger.info("Using typo correction", 
                               original=q, 
                               corrected=best_correction.corrected,
                               confidence=best_correction.confidence)
                    
                    # Get suggestions for both original and corrected queries
                    original_suggestions = get_autocomplete_suggestions(q, limit//2)
                    corrected_suggestions = get_autocomplete_suggestions(best_correction.corrected, limit)
                    
                    # Merge suggestions and mark corrected ones
                    all_suggestions_data = []
                    
                    # Prioritize corrected suggestions (they come first)
                    for item in corrected_suggestions:
                        item['is_corrected'] = True
                        item['corrected_from'] = q
                        item['corrected_to'] = best_correction.corrected
                        item['correction_confidence'] = best_correction.confidence
                        item['correction_type'] = best_correction.correction_type
                        all_suggestions_data.append(item)
                    
                    # Add original suggestions (if any) but mark them as original
                    for item in original_suggestions:
                        # Check if this suggestion is already in corrected results
                        if not any(existing['suggestion'].lower() == item['suggestion'].lower() 
                                 for existing in all_suggestions_data):
                            item['is_corrected'] = False
                            item['original_query'] = q
                            all_suggestions_data.append(item)
                else:
                    # No significant correction needed
                    all_suggestions_data = suggestions_data
                    for item in all_suggestions_data:
                        item['is_corrected'] = False
                
                # Remove duplicates and limit results
                seen = set()
                unique_suggestions = []
                for item in all_suggestions_data:
                    if item['suggestion'] not in seen:
                        seen.add(item['suggestion'])
                        unique_suggestions.append(item)
                
                suggestions_data = unique_suggestions[:limit]
            
            # Add NLP metadata
            for item in suggestions_data:
                item['nlp_enhanced'] = True
                if intent:
                    item['intent_type'] = intent.intent_type
                    item['intent_confidence'] = intent.confidence
            
            logger.info("NLP-enhanced autocomplete processed", 
                       query=q, 
                       processed_query=processed_query,
                       suggestions_count=len(suggestions_data),
                       corrections_count=len(corrections))
            
        except Exception as nlp_error:
            logger.warning("NLP processing failed, using basic autocomplete", error=str(nlp_error))
            # Fallback to basic autocomplete
            suggestions_data = get_autocomplete_suggestions(q, limit)
            for item in suggestions_data:
                item['nlp_enhanced'] = False
        
        # Convert to response format
        suggestions = []
        for item in suggestions_data:
            # Create the AutocompleteResult with all required fields
            suggestion_obj = AutocompleteResult(
                suggestion=item['suggestion'],
                type=item['type'],
                count=item['count'],
                title=item.get('title', item['suggestion']),
                image=item.get('image', ''),
                price=item.get('price', '$0.00'),
                url=item.get('url', '#'),
                category=item.get('category', 'General'),
                sku=item.get('sku', ''),
                id=item.get('id', 0)
            )
            
            # Add additional metadata as extra fields
            if 'nlp_enhanced' in item:
                suggestion_obj.__dict__['nlp_enhanced'] = item['nlp_enhanced']
            if 'is_corrected' in item:
                suggestion_obj.__dict__['is_corrected'] = item['is_corrected']
            if 'corrected_from' in item:
                suggestion_obj.__dict__['corrected_from'] = item['corrected_from']
            if 'intent_type' in item:
                suggestion_obj.__dict__['intent_type'] = item['intent_type']
                
            suggestions.append(suggestion_obj)
        
        logger.info("Returning enhanced autocomplete suggestions", query=q, count=len(suggestions))
        
        return AutocompleteResponse(
            suggestions=suggestions,
            query=q
        )
    except Exception as e:
        logger.error("Error getting autocomplete suggestions", error=str(e))
        # Return empty suggestions instead of raising to prevent API errors
        return AutocompleteResponse(
            suggestions=[],
            query=q
        )

@router.get("/", response_model=AutocompleteResponse)
async def get_autocomplete(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, description="Number of suggestions"),
    request: Request = None
):
    """Get autocomplete suggestions via GET"""
    return await _process_autocomplete_request(q, limit)

@router.post("/", response_model=AutocompleteResponse)
async def post_autocomplete(
    autocomplete_request: AutocompleteRequest = Body(...),
    request: Request = None
):
    """Get autocomplete suggestions via POST with JSON body"""
    query = autocomplete_request.get_query()
    if not query:
        # Return empty suggestions if no query provided
        return AutocompleteResponse(suggestions=[], query="")
    return await _process_autocomplete_request(query, autocomplete_request.limit)

@router.post("/form", response_model=AutocompleteResponse)
async def post_autocomplete_form(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, description="Number of suggestions"),
    request: Request = None
):
    """Get autocomplete suggestions via POST with query parameters (for form submissions)"""
    return await _process_autocomplete_request(q, limit)