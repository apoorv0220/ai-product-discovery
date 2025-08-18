"""
Advanced Spell Checker with OpenAI Integration
Provides intelligent spelling correction for product search queries
"""

import os
import json
import re
from typing import List, Dict, Tuple, Optional
import structlog
from rapidfuzz import fuzz, process
from spellchecker import SpellChecker
import nltk
from Levenshtein import distance as levenshtein_distance

logger = structlog.get_logger()

class AdvancedSpellChecker:
    def __init__(self):
        self.spell = SpellChecker()
        self.products_cache = {}
        self.product_names = []
        self.product_words = set()
        self.custom_dictionary = set()
        
        # Initialize NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('wordnet', quiet=True)
        except Exception as e:
            logger.warning("Failed to download NLTK data", error=str(e))
        
        # Load product data for context-aware corrections
        self._load_product_data()
        
        # Common brand names and product terms to add to dictionary
        self._initialize_custom_dictionary()
    
    def _load_product_data(self):
        """Load product data to build a context-aware dictionary"""
        try:
            products_file = "/tmp/products_index.json"
            if os.path.exists(products_file):
                with open(products_file, 'r') as f:
                    products = json.load(f)
                    
                for product_id, product in products.items():
                    name = product.get('name', '')
                    if name:
                        self.product_names.append(name.lower())
                        # Add individual words from product names
                        words = re.findall(r'\b[a-zA-Z]{2,}\b', name.lower())
                        self.product_words.update(words)
                        
                        # Store full product data for reference
                        self.products_cache[product_id] = product
                        
                logger.info("Loaded product data for spell checking", 
                          products=len(products), 
                          unique_words=len(self.product_words))
        except Exception as e:
            logger.error("Failed to load product data for spell checking", error=str(e))
    
    def _initialize_custom_dictionary(self):
        """Initialize custom dictionary with common brand names and product terms"""
        common_terms = {
            # Common brand variations and product terms
            'fusion', 'typhon', 'orion', 'olivia', 'hyperion', 'neve', 'marco', 'stark',
            'daphne', 'teton', 'chaz', 'joust', 'strive', 'crown', 'summit',
            # Product types
            'hoodie', 'hoodies', 'jacket', 'jackets', 'backpack', 'backpacks',
            'tee', 'tees', 'tank', 'tanks', 'pants', 'shorts', 'bag', 'bags',
            'pullover', 'fleece', 'performance', 'lightweight', 'fitted',
            # Materials and features
            'cotton', 'polyester', 'fleece', 'mesh', 'breathable', 'moisture',
            'wicking', 'thermal', 'insulated', 'waterproof', 'windproof',
            # Colors
            'black', 'white', 'blue', 'red', 'green', 'gray', 'grey', 'navy',
            'purple', 'orange', 'yellow', 'pink', 'brown', 'beige'
        }
        
        self.custom_dictionary.update(common_terms)
        self.custom_dictionary.update(self.product_words)
        
        # Add to spell checker
        self.spell.word_frequency.load_words(self.custom_dictionary)
    
    def correct_spelling(self, query: str, threshold: float = 0.8) -> Dict[str, any]:
        """
        Correct spelling in the query using multiple methods
        
        Args:
            query: Input search query
            threshold: Similarity threshold for corrections
            
        Returns:
            Dict with corrected query and metadata
        """
        if not query or len(query.strip()) < 2:
            return {
                'corrected_query': query,
                'corrections': [],
                'confidence': 1.0,
                'method': 'no_correction_needed'
            }
        
        original_query = query.strip()
        words = re.findall(r'\b[a-zA-Z]+\b', original_query.lower())
        
        if not words:
            return {
                'corrected_query': original_query,
                'corrections': [],
                'confidence': 1.0,
                'method': 'no_words_found'
            }
        
        corrections = []
        corrected_words = []
        total_confidence = 0
        
        for word in words:
            correction_result = self._correct_word(word, threshold)
            corrected_words.append(correction_result['corrected_word'])
            
            if correction_result['was_corrected']:
                corrections.append({
                    'original': word,
                    'corrected': correction_result['corrected_word'],
                    'confidence': correction_result['confidence'],
                    'method': correction_result['method']
                })
            
            total_confidence += correction_result['confidence']
        
        # Reconstruct the query maintaining original case and punctuation
        corrected_query = self._reconstruct_query(original_query, words, corrected_words)
        
        # Try to find direct product name matches for better context
        product_match = self._find_product_name_match(corrected_query, threshold)
        if product_match:
            corrected_query = product_match['corrected']
            corrections.append(product_match['correction'])
        
        avg_confidence = total_confidence / len(words) if words else 1.0
        
        return {
            'corrected_query': corrected_query,
            'corrections': corrections,
            'confidence': min(avg_confidence, 1.0),
            'method': 'advanced_spell_check',
            'original_query': original_query
        }
    
    def _correct_word(self, word: str, threshold: float) -> Dict[str, any]:
        """Correct a single word using multiple methods"""
        if len(word) < 2:
            return {
                'corrected_word': word,
                'was_corrected': False,
                'confidence': 1.0,
                'method': 'too_short'
            }
        
        # Method 1: Check if word is already correct
        if word in self.custom_dictionary or word in self.spell:
            return {
                'corrected_word': word,
                'was_corrected': False,
                'confidence': 1.0,
                'method': 'already_correct'
            }
        
        # Method 2: Product name fuzzy matching (highest priority)
        product_correction = self._fuzzy_match_product_words(word, threshold)
        if product_correction and product_correction['confidence'] >= threshold:
            return product_correction
        
        # Method 3: Standard spell checker
        spell_correction = self._standard_spell_check(word)
        if spell_correction and spell_correction['confidence'] >= threshold:
            return spell_correction
        
        # Method 4: Phonetic matching for brand names
        phonetic_correction = self._phonetic_match(word, threshold)
        if phonetic_correction and phonetic_correction['confidence'] >= threshold:
            return phonetic_correction
        
        # Method 5: Character-level fuzzy matching
        fuzzy_correction = self._character_fuzzy_match(word, threshold)
        if fuzzy_correction and fuzzy_correction['confidence'] >= threshold:
            return fuzzy_correction
        
        # If no good correction found, return original
        return {
            'corrected_word': word,
            'was_corrected': False,
            'confidence': 0.5,
            'method': 'no_correction_found'
        }
    
    def _fuzzy_match_product_words(self, word: str, threshold: float) -> Optional[Dict[str, any]]:
        """Match against product-specific words with high accuracy"""
        if not self.product_words:
            return None
        
        # Use rapidfuzz for efficient fuzzy matching
        matches = process.extract(
            word, 
            list(self.product_words), 
            scorer=fuzz.ratio,
            limit=3
        )
        
        if matches and matches[0][1] >= (threshold * 100):
            best_match = matches[0][0]
            confidence = matches[0][1] / 100.0
            
            return {
                'corrected_word': best_match,
                'was_corrected': True,
                'confidence': confidence,
                'method': 'product_fuzzy_match'
            }
        
        return None
    
    def _standard_spell_check(self, word: str) -> Optional[Dict[str, any]]:
        """Use standard spell checker"""
        candidates = self.spell.candidates(word)
        if candidates:
            # Get the most likely candidate
            best_candidate = min(candidates, key=lambda x: levenshtein_distance(word, x))
            distance = levenshtein_distance(word, best_candidate)
            
            # Calculate confidence based on edit distance
            confidence = max(0, 1 - (distance / max(len(word), len(best_candidate))))
            
            if confidence >= 0.6 and distance <= 2:  # Maximum 2 character changes
                return {
                    'corrected_word': best_candidate,
                    'was_corrected': True,
                    'confidence': confidence,
                    'method': 'standard_spell_check'
                }
        
        return None
    
    def _phonetic_match(self, word: str, threshold: float) -> Optional[Dict[str, any]]:
        """Phonetic matching for brand names and unique terms"""
        try:
            from soundex import Soundex
            soundex = Soundex()
            word_soundex = soundex(word)
            
            for product_word in self.product_words:
                if len(product_word) >= 3:  # Only check longer words
                    if soundex(product_word) == word_soundex:
                        # Additional check with edit distance
                        distance = levenshtein_distance(word, product_word)
                        if distance <= 3:  # Allow up to 3 character differences
                            confidence = max(0.6, 1 - (distance / max(len(word), len(product_word))))
                            
                            return {
                                'corrected_word': product_word,
                                'was_corrected': True,
                                'confidence': confidence,
                                'method': 'phonetic_match'
                            }
        except Exception as e:
            logger.debug("Phonetic matching failed", error=str(e))
        
        return None
    
    def _character_fuzzy_match(self, word: str, threshold: float) -> Optional[Dict[str, any]]:
        """Character-level fuzzy matching as last resort"""
        best_match = None
        best_score = 0
        
        # Check against custom dictionary
        for dict_word in self.custom_dictionary:
            if len(dict_word) >= 3 and abs(len(word) - len(dict_word)) <= 3:
                score = fuzz.ratio(word, dict_word) / 100.0
                
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = dict_word
        
        if best_match and best_score >= threshold:
            return {
                'corrected_word': best_match,
                'was_corrected': True,
                'confidence': best_score,
                'method': 'character_fuzzy_match'
            }
        
        return None
    
    def _find_product_name_match(self, query: str, threshold: float) -> Optional[Dict[str, any]]:
        """Find direct product name matches for complete correction"""
        if not self.product_names:
            return None
        
        # Use rapidfuzz to find the best matching product name
        matches = process.extract(
            query.lower(),
            self.product_names,
            scorer=fuzz.partial_ratio,
            limit=3
        )
        
        if matches and matches[0][1] >= (threshold * 100):
            best_match = matches[0][0]
            confidence = matches[0][1] / 100.0
            
            # Only suggest if it's a significant improvement
            if confidence >= 0.85:
                return {
                    'corrected': best_match.title(),
                    'correction': {
                        'original': query,
                        'corrected': best_match.title(),
                        'confidence': confidence,
                        'method': 'product_name_match'
                    }
                }
        
        return None
    
    def _reconstruct_query(self, original: str, original_words: List[str], corrected_words: List[str]) -> str:
        """Reconstruct query maintaining original formatting"""
        if len(original_words) != len(corrected_words):
            return ' '.join(corrected_words)
        
        result = original
        for orig_word, corr_word in zip(original_words, corrected_words):
            if orig_word != corr_word:
                # Replace with case-sensitive substitution
                pattern = r'\b' + re.escape(orig_word) + r'\b'
                result = re.sub(pattern, corr_word, result, flags=re.IGNORECASE)
        
        return result

# Global instance
spell_checker = AdvancedSpellChecker()
