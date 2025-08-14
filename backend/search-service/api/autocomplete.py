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

# Import updated schemas
try:
    from ..schemas.autocomplete_updated import (
        AutocompleteSuggestion,
        AutocompleteMetadata, 
        AutocompleteResponse as UpdatedAutocompleteResponse,
        AutocompleteRequest as UpdatedAutocompleteRequest,
        AutocompleteErrorResponse
    )
    USE_UPDATED_SCHEMAS = True
except ImportError:
    # Fallback to existing schemas if new ones aren't available
    USE_UPDATED_SCHEMAS = False

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
        product_description = product.get('description', '')
        
        # Check if query matches product name, searchable text, or description
        # Also check individual words for partial matching
        query_words = query_lower.split()
        name_lower = product_name.lower()
        desc_lower = product_description.lower()
        
        match_found = False
        
        # Direct substring match
        if query_lower in name_lower or query_lower in searchable_text or query_lower in desc_lower:
            match_found = True
        
        # Individual word matching for better semantic search
        if not match_found:
            for word in query_words:
                if len(word) > 2:  # Skip very short words
                    if word in name_lower or word in searchable_text or word in desc_lower:
                        match_found = True
                        break
        
        if match_found:
            # Format price for display - try multiple price fields
            price = product.get('price', 0)
            final_price = product.get('final_price', 0)
            special_price = product.get('special_price')
            currency = product.get('currency', 'USD')
            
            # Priority: special_price > final_price > price
            display_price = 0
            
            if special_price and special_price > 0:
                display_price = special_price
            elif final_price and final_price > 0:
                display_price = final_price
            elif price and price > 0:
                display_price = price
            
            if display_price and display_price > 0:
                formatted_price = f"${display_price:.2f}"
            else:
                # Try to extract price from other possible fields
                for field in ['regular_price', 'base_price', 'min_price']:
                    price_str = str(product.get(field, ''))
                    if price_str and price_str != '0' and price_str != '' and price_str != 'None':
                        try:
                            extracted_price = float(price_str)
                            if extracted_price > 0:
                                formatted_price = f"${extracted_price:.2f}"
                                break
                        except (ValueError, TypeError):
                            continue
                else:
                    formatted_price = "Price on request"
            
            # Get primary category name (not ID)
            categories = product.get('categories', [])
            primary_category = 'General'
            
            if categories:
                # If categories is a list of dicts with name/id, extract name
                if isinstance(categories[0], dict):
                    primary_category = categories[0].get('name', categories[0].get('title', 'General'))
                elif isinstance(categories[0], str):
                    # If it's a string, use it directly
                    primary_category = categories[0]
                else:
                    # If it's an ID, we need to map it to a name
                    # Common category mappings (expand as needed)
                    category_map = {
                        '1': 'Root Catalog',
                        '2': 'Default Category',
                        '3': 'Men',
                        '4': 'Women',
                        '5': 'Gear',
                        '6': 'Training',
                        '7': 'Sale',
                        '8': 'What\'s New',
                        '9': 'Tops',
                        '10': 'Bottoms',
                        '11': 'Hoodies & Sweatshirts',
                        '12': 'Jackets',
                        '13': 'Tees',
                        '14': 'Tanks',
                        '15': 'Hoodies & Sweatshirts',  # Main hoodie category
                        '16': 'T-Shirts',
                        '17': 'Jackets & Coats',
                        '18': 'Pants & Shorts',
                        '19': 'Accessories',
                        '20': 'Shoes & Footwear',
                        '21': 'Bags & Luggage',
                        '22': 'Fitness Equipment',
                        '23': 'Electronics',
                        '24': 'Home & Living',
                        '25': 'Watches',
                        '26': 'Fitness',
                        '27': 'Bottoms',
                        '28': 'Pants',
                        '29': 'Shorts'
                    }
                    primary_category = category_map.get(str(categories[0]), f'Category {categories[0]}')
            
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
                'image': _get_proper_image_url(product.get('image_url', '')),
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
        
        # Try OpenAI-enhanced autocomplete first
        try:
            import sys
            import os
            # Add the search-service directory to Python path
            search_service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, search_service_dir)
            from core.openai_nlp import process_query_with_openai
            
            # Process query for typos and intent using OpenAI
            intent, corrections = await process_query_with_openai(q)
            
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
        
        # Convert to response format - ensure Magento compatibility
        suggestions = []
        for item in suggestions_data:
            # Create suggestion dict with all fields Magento expects
            suggestion_dict = {
                'suggestion': item['suggestion'],
                'title': item.get('title', item['suggestion']),
                'type': item['type'],
                'count': item['count'],
                'image': item.get('image', ''),
                'price': item.get('price', '$0.00'),
                'url': item.get('url', '#'),
                'category': item.get('category', 'General'),
                'sku': item.get('sku', ''),
                'id': item.get('id', 0),
                # AI enhancement metadata
                'nlp_enhanced': item.get('nlp_enhanced', False),
                'is_corrected': item.get('is_corrected', False),
                'corrected_from': item.get('corrected_from', ''),
                'corrected_to': item.get('corrected_to', ''),
                'correction_confidence': item.get('correction_confidence', 0),
                'correction_type': item.get('correction_type', ''),
                'intent_type': item.get('intent_type', ''),
                'intent_confidence': item.get('intent_confidence', 0)
            }
            
            suggestions.append(suggestion_dict)
        
        # Prepare metadata for Magento
        autocomplete_metadata = {
            'nlp_processing': any(s.get('nlp_enhanced', False) for s in suggestions),
            'typo_corrections': sum(1 for s in suggestions if s.get('is_corrected', False)),
            'intent_detection': any(s.get('intent_type') for s in suggestions),
            'semantic_search': any(s.get('nlp_enhanced', False) for s in suggestions),
            'total_suggestions': len(suggestions)
        }
        
        logger.info("Returning enhanced autocomplete suggestions", 
                   query=q, 
                   count=len(suggestions),
                   nlp_enhanced=autocomplete_metadata['nlp_processing'])
        
        # Return format that Magento expects
        return {
            'suggestions': suggestions,
            'query': q,
            'autocomplete_metadata': autocomplete_metadata
        }
    except Exception as e:
        logger.error("Error getting autocomplete suggestions", error=str(e))
        # Return empty suggestions instead of raising to prevent API errors
        return {
            'suggestions': [],
            'query': q,
            'autocomplete_metadata': {
                'nlp_processing': False,
                'typo_corrections': 0,
                'intent_detection': False,
                'semantic_search': False,
                'total_suggestions': 0
            },
            'error': str(e)
        }

@router.get("/")
async def get_autocomplete(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, description="Number of suggestions"),
    request: Request = None
):
    """Get autocomplete suggestions via GET"""
    return await _process_autocomplete_request(q, limit)

@router.post("/")
async def post_autocomplete(
    autocomplete_request: AutocompleteRequest = Body(...),
    request: Request = None
):
    """Get autocomplete suggestions via POST with JSON body"""
    query = autocomplete_request.get_query()
    if not query:
        # Return empty suggestions if no query provided
        return {
            'suggestions': [],
            'query': "",
            'autocomplete_metadata': {
                'nlp_processing': False,
                'typo_corrections': 0,
                'intent_detection': False,
                'semantic_search': False,
                'total_suggestions': 0
            }
        }
    return await _process_autocomplete_request(query, autocomplete_request.limit)

@router.post("/form")
async def post_autocomplete_form(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, description="Number of suggestions"),
    request: Request = None
):
    """Get autocomplete suggestions via POST with query parameters (for form submissions)"""
    return await _process_autocomplete_request(q, limit)


def _get_proper_image_url(image_url: str) -> str:
    """Get proper image URL, avoiding placeholders"""
    if not image_url or 'placeholder' in image_url.lower():
        # Return a default product image or empty string
        return ''
    
    # Ensure it's a full URL
    if image_url.startswith('/'):
        return f"https://magento-test.softdemonew.info{image_url}"
    
    return image_url