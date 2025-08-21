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
import re
from rapidfuzz import fuzz, process

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

# Import advanced spell checker
try:
    from ..core.advanced_spell_checker import spell_checker
    SPELL_CHECKER_AVAILABLE = True
except ImportError:
    SPELL_CHECKER_AVAILABLE = False
    logger.warning("Advanced spell checker not available")

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
    """Get real autocomplete suggestions from indexed products with advanced spell correction"""
    # Load current products
    products = load_products()
    
    if not query.strip():
        return []
    
    original_query = query.strip()
    query_lower = original_query.lower()
    suggestions = []
    corrected_query = original_query
    spell_corrections = []
    
    # Check if we have any products
    if not products:
        logger.warning("No products found in index for autocomplete", query=query)
        return []
    
    # Apply advanced spell correction
    if SPELL_CHECKER_AVAILABLE and len(original_query) >= 2:
        correction_result = spell_checker.correct_spelling(original_query, threshold=0.75)
        if correction_result['corrections']:
            corrected_query = correction_result['corrected_query']
            query_lower = corrected_query.lower()
            spell_corrections = correction_result['corrections']
            logger.info("Applied spell corrections", 
                       original=original_query, 
                       corrected=corrected_query,
                       corrections=len(spell_corrections))
    
    # Enhanced matching with both original and corrected queries
    all_suggestions = []
    
    for product_id, product in products.items():
        product_name = product.get('name', '')
        searchable_text = product.get('searchable_text', product_name.lower())
        product_description = product.get('description', '')
        
        name_lower = product_name.lower()
        desc_lower = product_description.lower()
        
        match_found = False
        match_score = 0
        is_corrected = corrected_query != original_query
        
        # Try both original and corrected queries
        queries_to_try = [query_lower]
        if is_corrected:
            queries_to_try.append(corrected_query.lower())
        
        for current_query in queries_to_try:
            query_words = current_query.split()
            
            # Method 1: Direct substring match (highest score)
            if current_query in name_lower:
                match_found = True
                match_score = max(match_score, 100)
                break
            elif current_query in searchable_text or current_query in desc_lower:
                match_found = True
                match_score = max(match_score, 90)
                break
            
            # Method 2: Fuzzy matching for product names (high score)
            name_similarity = fuzz.partial_ratio(current_query, name_lower)
            if name_similarity >= 75:
                match_found = True
                match_score = max(match_score, name_similarity)
                break
            
            # Method 3: Individual word matching
            word_matches = 0
            for word in query_words:
                if len(word) > 2:  # Skip very short words
                    if word in name_lower:
                        word_matches += 2  # Higher weight for name matches
                    elif word in searchable_text or word in desc_lower:
                        word_matches += 1
            
            if word_matches > 0:
                match_found = True
                match_score = max(match_score, min(80, word_matches * 20))
        
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
                # Complete Magento category mappings - actual from database
                category_map = {
                    '1': 'Root Catalog',
                    '2': 'Default Category', 
                    '3': 'Gear',
                    '4': 'Bags',
                    '5': 'Fitness Equipment',
                    '6': 'Watches',
                    '7': 'Collections',
                    '8': 'New Luma Yoga Collection',
                    '9': 'Training',
                    '10': 'Video Download',
                    '11': 'Men',
                    '12': 'Tops',
                    '13': 'Bottoms',
                    '14': 'Jackets',
                    '15': 'Hoodies & Sweatshirts',
                    '16': 'Tees',
                    '17': 'Tanks',
                    '18': 'Pants',
                    '19': 'Shorts',
                    '20': 'Women',
                    '21': 'Tops',
                    '22': 'Bottoms',
                    '23': 'Jackets',
                    '24': 'Hoodies & Sweatshirts',
                    '25': 'Tees',
                    '26': 'Bras & Tanks',
                    '27': 'Pants',
                    '28': 'Shorts',
                    '29': 'Promotions',
                    '30': 'Women Sale',
                    '31': 'Men Sale',
                    '32': 'Pants',
                    '33': 'Tees',
                    '34': 'Erin Recommends',
                    '35': 'Performance Fabrics',
                    '36': 'Eco Friendly',
                    '37': 'Sale',
                    '38': 'What\'s New',
                    '39': 'Performance Sportswear New',
                    '40': 'Eco Collection New'
                }
                
                # Handle different category formats
                if isinstance(categories[0], dict):
                    # Category is a dict with name/id
                    primary_category = categories[0].get('name', categories[0].get('title', 'General'))
                elif isinstance(categories[0], str):
                    # Category is a string ID, map it to name
                    primary_category = category_map.get(str(categories[0]), f'Category {categories[0]}')
                else:
                    # Fallback for any other type
                    primary_category = category_map.get(str(categories[0]), f'Category {categories[0]}')
            
            all_suggestions.append({
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
                'categories': categories,
                'match_score': match_score,
                'nlp_enhanced': True,
                'is_corrected': is_corrected,
                'corrected_from': original_query if is_corrected else '',
                'corrected_to': corrected_query if is_corrected else '',
                'correction_confidence': correction_result.get('confidence', 0) if SPELL_CHECKER_AVAILABLE and is_corrected else 0,
                'correction_type': 'spell_check' if is_corrected else '',
                'intent_type': 'specific',
                'intent_confidence': 0.8 if match_score >= 90 else 0.6
            })
    
    # Sort by match score and relevance
    def relevance_score(item):
        name = item['suggestion'].lower()
        # Use corrected query if available, otherwise original
        search_query = corrected_query.lower() if corrected_query != original_query else query_lower
        pos = name.find(search_query)
        match_score = item.get('match_score', 0)
        
        # Primary sort by match score (descending), then by position (ascending), then by name length (ascending)
        return (-match_score, pos if pos >= 0 else 999, len(name))
    
    all_suggestions.sort(key=relevance_score)
    suggestions = all_suggestions[:limit]
    return suggestions


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
    user_id: Optional[str] = None  # User ID for personalization
    session_id: Optional[str] = None  # Session ID for anonymous personalization
    
    def get_query(self) -> str:
        """Get the query value from either q or query field"""
        return self.q or self.query or ""


async def _process_autocomplete_request(q: str, limit: int = 10, user_id: str = None, session_id: str = None):
    """Internal function to process autocomplete requests with NLP enhancement and personalization"""
    try:
        logger.info("Getting NLP-enhanced and personalized autocomplete suggestions", query=q)
        
        # Try OpenAI-enhanced autocomplete first
        try:
            import sys
            import os
            # Add the search-service directory to Python path
            search_service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, search_service_dir)
            from core.openai_nlp import process_query_with_openai
            from core.personalized_search import personalized_search_engine
            
            # Process query for typos and intent using OpenAI
            intent, corrections = await process_query_with_openai(q)
            
            # Use corrected query if available
            processed_query = intent.processed_query if intent else q
            
            # Get suggestions using processed query
            suggestions_data = get_autocomplete_suggestions(processed_query, limit)
            
            # Apply personalized ranking to suggestions
            if user_id or session_id:
                try:
                    logger.info(f"Applying personalized ranking with user_id={user_id}, session_id={session_id}")
                    original_count = len(suggestions_data)
                    suggestions_data = await personalized_search_engine.apply_personalized_ranking(
                        suggestions_data, user_id, session_id, q
                    )
                    logger.info(f"Applied personalized ranking to {len(suggestions_data)} suggestions (was {original_count})")
                    # Log first few results for debugging
                    for i, item in enumerate(suggestions_data[:3]):
                        logger.info(f"Result {i}: {item.get('suggestion', 'N/A')} - score: {item.get('final_score', 'N/A')}, weight: {item.get('personalization_weight', 'N/A')}")
                except Exception as e:
                    logger.warning(f"Failed to apply personalized ranking: {str(e)}")
                    import traceback
                    logger.warning(f"Traceback: {traceback.format_exc()}")
            
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
    user_id: str = Query(None, description="User ID for personalization"),
    session_id: str = Query(None, description="Session ID for anonymous personalization"),
    request: Request = None
):
    """Get autocomplete suggestions via GET with personalization"""
    return await _process_autocomplete_request(q, limit, user_id, session_id)

@router.post("/")
async def post_autocomplete(
    autocomplete_request: AutocompleteRequest = Body(...),
    request: Request = None
):
    """Get autocomplete suggestions via POST with JSON body and personalization"""
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
    return await _process_autocomplete_request(
        query, 
        autocomplete_request.limit, 
        autocomplete_request.user_id, 
        autocomplete_request.session_id
    )

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