"""
Advanced NLP Processor for AI Product Discovery Suite
Implements semantic search, intent recognition, typo tolerance, and auto-correct
"""

import re
import string
import asyncio
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from difflib import SequenceMatcher
import structlog
from textdistance import levenshtein, jaro_winkler
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag

# Download required NLTK data
try:
    import ssl
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)
except Exception as e:
    print(f"NLTK download warning: {e}")

logger = structlog.get_logger()


@dataclass
class SearchIntent:
    """Detected search intent"""
    intent_type: str  # buy, compare, browse, specific, question
    confidence: float
    entities: List[Dict[str, Any]]
    keywords: List[str]
    original_query: str
    processed_query: str


@dataclass
class QueryCorrection:
    """Query correction suggestion"""
    original: str
    corrected: str
    confidence: float
    correction_type: str  # typo, spelling, synonym


class AdvancedNLPProcessor:
    """Advanced NLP processor with semantic understanding"""
    
    def __init__(self):
        """Initialize NLP processor"""
        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Intent patterns
        self.intent_patterns = {
            'buy': [
                r'\b(buy|purchase|get|order|shop for|need|want|looking|find)\b',
                r'\b(looking for|searching for|find me)\b.*\b(to buy|to purchase)\b',
                r'\bi want\b.*\b(hoodie|shirt|product|item|comfortable|comfy)\b',
                r'\b(want|need|looking for)\b.*\b(comfortable|comfy|good|nice|quality)\b'
            ],
            'compare': [
                r'\b(compare|vs|versus|difference between|which is better)\b',
                r'\b(show me different|alternatives to|similar to)\b'
            ],
            'browse': [
                r'\b(show me|browse|list|what do you have|categories)\b',
                r'\b(all|everything|collection)\b.*\b(products|items)\b'
            ],
            'question': [
                r'\b(what|how|when|where|why|which|is|does|can|will)\b',
                r'\?$'
            ]
        }
        
        # Common product synonyms
        self.product_synonyms = {
            'hoodie': ['sweatshirt', 'pullover', 'jumper', 'sweater'],
            'shirt': ['tee', 't-shirt', 'top', 'blouse'],
            'pants': ['trousers', 'jeans', 'slacks', 'bottoms'],
            'shoes': ['sneakers', 'footwear', 'boots', 'sandals'],
            'jacket': ['coat', 'blazer', 'outerwear'],
            'bag': ['purse', 'backpack', 'handbag', 'tote'],
            'watch': ['timepiece', 'clock'],
            'phone': ['smartphone', 'mobile', 'cell phone'],
            'laptop': ['computer', 'notebook', 'pc']
        }
        
        # Typo correction dictionary (expandable)
        self.common_typos = {
            'hro': 'hero',
            'hodie': 'hoodie',
            'hoddie': 'hoodie',
            'hoody': 'hoodie',
            'tshrt': 'tshirt',
            'jens': 'jeans',
            'shose': 'shoes',
            'phon': 'phone',
            'labtop': 'laptop',
            'comfy': 'comfortable',
            'comfortble': 'comfortable',
            'buy': '',  # Remove filler words
            'want': '',
            'need': '',
            'looking': '',
            'search': ''
        }
        
        # Brand variations
        self.brand_variations = {
            'nike': ['nike', 'nik', 'nke'],
            'adidas': ['adidas', 'addidas', 'adidass'],
            'hero': ['hero', 'hro', 'herro']
        }

    async def process_search_query(self, query: str) -> Tuple[SearchIntent, List[QueryCorrection]]:
        """
        Process search query with full NLP pipeline
        
        Args:
            query: Raw search query
            
        Returns:
            Tuple of (SearchIntent, List[QueryCorrection])
        """
        logger.info("Processing search query", query=query)
        
        # Step 1: Clean and normalize query
        cleaned_query = self._clean_query(query)
        
        # Step 2: Detect and correct typos
        corrections = await self._detect_typos(cleaned_query)
        corrected_query = corrections[0].corrected if corrections else cleaned_query
        
        # Step 3: Extract intent
        intent = await self._extract_intent(corrected_query, query)
        
        # Step 4: Enhance with synonyms
        enhanced_query = self._expand_with_synonyms(corrected_query)
        intent.processed_query = enhanced_query
        
        logger.info("NLP processing complete", 
                   original=query, 
                   processed=enhanced_query, 
                   intent=intent.intent_type,
                   corrections_count=len(corrections))
        
        return intent, corrections

    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query"""
        # Convert to lowercase
        query = query.lower().strip()
        
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Remove special characters but keep important ones
        query = re.sub(r'[^\w\s\-\']', ' ', query)
        
        return query

    async def _detect_typos(self, query: str) -> List[QueryCorrection]:
        """Detect and suggest corrections for typos"""
        corrections = []
        words = query.split()
        corrected_words = []
        
        for word in words:
            correction = await self._correct_word(word)
            if correction:
                corrections.append(correction)
                corrected_words.append(correction.corrected)
            else:
                corrected_words.append(word)
        
        # If we have corrections, create a full query correction
        if corrections:
            corrected_query = ' '.join(corrected_words)
            full_correction = QueryCorrection(
                original=query,
                corrected=corrected_query,
                confidence=sum(c.confidence for c in corrections) / len(corrections),
                correction_type='spelling'
            )
            return [full_correction] + corrections
        
        return []

    async def _correct_word(self, word: str) -> Optional[QueryCorrection]:
        """Correct a single word using multiple strategies"""
        if len(word) < 2:
            return None
        
        # Check common typos dictionary first
        if word in self.common_typos:
            return QueryCorrection(
                original=word,
                corrected=self.common_typos[word],
                confidence=0.9,
                correction_type='known_typo'
            )
        
        # Check brand variations
        for brand, variations in self.brand_variations.items():
            if word in variations and word != brand:
                return QueryCorrection(
                    original=word,
                    corrected=brand,
                    confidence=0.85,
                    correction_type='brand_variation'
                )
        
        # Check against product synonyms for fuzzy matching
        best_match = None
        best_score = 0.0
        
        all_product_terms = set()
        for main_term, synonyms in self.product_synonyms.items():
            all_product_terms.add(main_term)
            all_product_terms.update(synonyms)
        
        for term in all_product_terms:
            # Use Jaro-Winkler for better phonetic matching
            similarity = jaro_winkler(word, term)
            
            # Also check Levenshtein distance
            lev_distance = levenshtein(word, term)
            lev_similarity = 1 - (lev_distance / max(len(word), len(term)))
            
            # Combined score
            combined_score = (similarity * 0.7) + (lev_similarity * 0.3)
            
            # More lenient threshold for better typo correction
            if combined_score > best_score and combined_score > 0.6:  # Lowered from 0.8 to 0.6
                best_score = combined_score
                best_match = term
        
        if best_match:
            return QueryCorrection(
                original=word,
                corrected=best_match,
                confidence=best_score,
                correction_type='fuzzy_match'
            )
        
        return None

    async def _extract_intent(self, query: str, original_query: str) -> SearchIntent:
        """Extract search intent using pattern matching and NLP"""
        
        # Tokenize and tag parts of speech
        tokens = word_tokenize(query)
        pos_tags = pos_tag(tokens)
        
        # Extract entities (brands, products, etc.)
        entities = self._extract_entities(tokens, pos_tags)
        
        # Extract keywords (remove stop words)
        keywords = [word for word in tokens 
                   if word not in self.stop_words and len(word) > 2]
        
        # Detect intent using patterns
        intent_type = 'specific'  # default
        confidence = 0.5
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, original_query.lower()):
                    intent_type = intent
                    confidence = 0.8
                    break
            if confidence > 0.5:
                break
        
        # Adjust confidence based on query characteristics
        if len(keywords) > 2:
            confidence += 0.1
        if any(entity['type'] == 'brand' for entity in entities):
            confidence += 0.1
        if any(entity['type'] == 'product' for entity in entities):
            confidence += 0.1
        
        confidence = min(confidence, 1.0)
        
        return SearchIntent(
            intent_type=intent_type,
            confidence=confidence,
            entities=entities,
            keywords=keywords,
            original_query=original_query,
            processed_query=query
        )

    def _extract_entities(self, tokens: List[str], pos_tags: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Extract named entities and product-specific entities"""
        entities = []
        
        # Extract brand entities
        for token in tokens:
            for brand, variations in self.brand_variations.items():
                if token.lower() in [v.lower() for v in variations]:
                    entities.append({
                        'text': token,
                        'type': 'brand',
                        'canonical': brand,
                        'confidence': 0.9
                    })
        
        # Extract product type entities
        for token in tokens:
            for product, synonyms in self.product_synonyms.items():
                if token.lower() in [s.lower() for s in synonyms] or token.lower() == product:
                    entities.append({
                        'text': token,
                        'type': 'product',
                        'canonical': product,
                        'confidence': 0.85
                    })
        
        # Extract adjectives (potential product attributes)
        for token, pos in pos_tags:
            if pos.startswith('JJ'):  # Adjective
                entities.append({
                    'text': token,
                    'type': 'attribute',
                    'canonical': token,
                    'confidence': 0.6
                })
        
        return entities

    def _expand_with_synonyms(self, query: str) -> str:
        """Expand query with synonyms for better matching"""
        words = query.lower().split()
        expanded_terms = []
        
        # Remove common filler words first
        filler_words = {'i', 'want', 'to', 'buy', 'a', 'an', 'the', 'some', 'looking', 'for', 'find', 'get', 'need'}
        meaningful_words = [word for word in words if word not in filler_words]
        
        for word in meaningful_words:
            expanded_terms.append(word)
            
            # Add synonyms
            for main_term, synonyms in self.product_synonyms.items():
                if word == main_term:
                    expanded_terms.extend(synonyms[:2])  # Add top 2 synonyms
                elif word in synonyms:
                    expanded_terms.append(main_term)
                    # Add one more synonym
                    other_synonyms = [s for s in synonyms if s != word]
                    if other_synonyms:
                        expanded_terms.append(other_synonyms[0])
        
        # If no meaningful words found, return original query
        if not expanded_terms:
            return query
            
        return ' '.join(expanded_terms)

    def create_search_query(self, intent: SearchIntent) -> Dict[str, Any]:
        """Create optimized search query based on intent"""
        
        base_query = {
            'query': intent.processed_query,
            'boost_fields': [],
            'filters': {},
            'sort': [],
            'highlight': True
        }
        
        # Adjust search strategy based on intent
        if intent.intent_type == 'buy':
            # For buying intent, boost availability and popular products
            base_query['boost_fields'] = ['name^3', 'description^1', 'brand^2']
            base_query['filters']['in_stock'] = True
            base_query['sort'] = [
                {'popularity_score': {'order': 'desc'}},
                {'avg_rating': {'order': 'desc'}},
                {'_score': {'order': 'desc'}}
            ]
        
        elif intent.intent_type == 'compare':
            # For comparison, show diverse results
            base_query['boost_fields'] = ['name^2', 'brand^2', 'category^1']
            base_query['sort'] = [
                {'_score': {'order': 'desc'}},
                {'brand': {'order': 'asc'}}  # Group by brand for comparison
            ]
        
        elif intent.intent_type == 'browse':
            # For browsing, show variety
            base_query['sort'] = [
                {'category': {'order': 'asc'}},
                {'popularity_score': {'order': 'desc'}}
            ]
        
        else:  # specific
            # For specific searches, prioritize exact matches
            base_query['boost_fields'] = ['name^4', 'sku^3', 'brand^2']
            base_query['sort'] = [{'_score': {'order': 'desc'}}]
        
        # Add entity-based boosting
        for entity in intent.entities:
            if entity['type'] == 'brand':
                base_query['boost_fields'].append(f"brand^2.5")
            elif entity['type'] == 'product':
                base_query['boost_fields'].append(f"category^2")
        
        return base_query


class SemanticSearchEngine:
    """Semantic search engine with NLP capabilities"""
    
    def __init__(self):
        self.nlp_processor = AdvancedNLPProcessor()
        self.product_index = {}  # Will be loaded from database/file
    
    async def search(self, query: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Perform semantic search with NLP processing
        
        Args:
            query: User search query
            limit: Maximum results to return
            offset: Results offset for pagination
            
        Returns:
            Search results with NLP insights
        """
        import time
        start_time = time.time()
        
        # Process query with NLP
        intent, corrections = await self.nlp_processor.process_search_query(query)
        
        # Create optimized search query
        search_config = self.nlp_processor.create_search_query(intent)
        
        # Load products from storage
        products = self._load_products()
        
        # Perform semantic search
        results = await self._semantic_search(
            products, 
            intent, 
            search_config, 
            limit, 
            offset
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            'results': results,
            'total': len(results),
            'query': query,
            'processed_query': intent.processed_query,
            'intent': {
                'type': intent.intent_type,
                'confidence': intent.confidence,
                'entities': intent.entities
            },
            'corrections': [
                {
                    'original': c.original,
                    'corrected': c.corrected,
                    'confidence': c.confidence,
                    'type': c.correction_type
                } for c in corrections
            ],
            'took': processing_time
        }
    
    def _load_products(self) -> Dict[str, Any]:
        """Load products from storage"""
        try:
            import json
            import os
            
            products_file = "/tmp/products_index.json"
            if os.path.exists(products_file):
                with open(products_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error("Error loading products", error=str(e))
            return {}
    
    async def _semantic_search(
        self, 
        products: Dict[str, Any], 
        intent: SearchIntent, 
        search_config: Dict[str, Any],
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on products"""
        
        if not products:
            return []
        
        results = []
        query_terms = intent.processed_query.lower().split()
        
        for product_id, product in products.items():
            score = self._calculate_semantic_score(product, intent, query_terms)
            
            if score > 0.1:  # Minimum relevance threshold
                results.append({
                    'product_id': product_id,
                    'title': product.get('name', 'Unknown Product'),
                    'score': score,
                    'metadata': {
                        'price': product.get('price', 0),
                        'currency': product.get('currency', 'USD'),
                        'image_url': product.get('image_url', ''),
                        'url': product.get('url', ''),
                        'brand': product.get('brand', ''),
                        'category': product.get('categories', []),
                        'match_reason': self._get_match_reason(product, intent),
                        'intent_match': intent.intent_type
                    }
                })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply pagination
        return results[offset:offset + limit]
    
    def _calculate_semantic_score(
        self, 
        product: Dict[str, Any], 
        intent: SearchIntent, 
        query_terms: List[str]
    ) -> float:
        """Calculate semantic relevance score"""
        
        score = 0.0
        
        # Product text for matching
        product_text = f"{product.get('name', '')} {product.get('description', '')} {product.get('sku', '')}".lower()
        
        # Direct term matching
        for term in query_terms:
            if term in product_text:
                score += 0.3
        
        # Entity matching
        for entity in intent.entities:
            entity_text = entity['canonical'].lower()
            if entity['type'] == 'brand' and entity_text in product_text:
                score += 0.4 * entity['confidence']
            elif entity['type'] == 'product' and entity_text in product_text:
                score += 0.3 * entity['confidence']
            elif entity['type'] == 'attribute' and entity_text in product_text:
                score += 0.2 * entity['confidence']
        
        # Intent-based scoring
        if intent.intent_type == 'buy':
            # Boost in-stock and popular products
            if product.get('is_in_stock', True):
                score += 0.1
            if product.get('popularity_score', 0) > 0.5:
                score += 0.1
        
        # Fuzzy matching for partial matches
        for term in query_terms:
            if len(term) > 3:
                for word in product_text.split():
                    if len(word) > 3:
                        similarity = jaro_winkler(term, word)
                        if similarity > 0.8:
                            score += 0.15 * similarity
        
        return min(score, 1.0)
    
    def _get_match_reason(self, product: Dict[str, Any], intent: SearchIntent) -> str:
        """Get human-readable match reason"""
        reasons = []
        
        product_text = f"{product.get('name', '')} {product.get('description', '')}".lower()
        
        for entity in intent.entities:
            if entity['canonical'].lower() in product_text:
                if entity['type'] == 'brand':
                    reasons.append(f"Brand match: {entity['canonical']}")
                elif entity['type'] == 'product':
                    reasons.append(f"Product type: {entity['canonical']}")
        
        if not reasons:
            reasons.append(f"Keyword match from '{intent.original_query}'")
        
        return '; '.join(reasons)


# Global instance
semantic_search_engine = SemanticSearchEngine()
