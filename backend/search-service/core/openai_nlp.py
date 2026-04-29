"""
OpenAI-powered NLP Processor for AI Product Discovery Suite
Handles typo correction, semantic search, and intent recognition using OpenAI API
"""

import os
import json
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import structlog
import httpx

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
    corrections: List[str]


@dataclass
class QueryCorrection:
    """Query correction suggestion"""
    original: str
    corrected: str
    confidence: float
    correction_type: str


class OpenAINLPProcessor:
    """OpenAI-powered NLP processor for search queries"""
    
    def __init__(self):
        """Initialize OpenAI NLP processor"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            self.enabled = False
        else:
            self.enabled = True
            
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-3.5-turbo"  # Fast and cost-effective
        
        # Product categories for context
        self.product_categories = [
            "hoodies", "sweatshirts", "t-shirts", "shirts", "jackets", "coats",
            "pants", "jeans", "shorts", "skirts", "dresses", "shoes", "sneakers",
            "boots", "sandals", "accessories", "bags", "watches", "jewelry",
            "electronics", "phones", "laptops", "headphones"
        ]

    async def process_search_query(self, query: str) -> Tuple[SearchIntent, List[QueryCorrection]]:
        """
        Process search query using OpenAI for typo correction and semantic understanding
        """
        if not self.enabled:
            # Fallback to basic processing
            return await self._basic_process_query(query)
            
        try:
            logger.info("Processing query with OpenAI", query=query)
            
            # Create prompt for OpenAI
            prompt = self._create_search_prompt(query)
            
            # Call OpenAI API
            response = await self._call_openai(prompt)
            
            # Parse OpenAI response
            result = self._parse_openai_response(response, query)
            
            logger.info("OpenAI processing completed", 
                       original_query=query,
                       processed_query=result[0].processed_query,
                       corrections=len(result[1]))
            
            return result
            
        except Exception as e:
            logger.error("OpenAI processing failed, using fallback", error=str(e))
            return await self._basic_process_query(query)

    def _create_search_prompt(self, query: str) -> str:
        """Create optimized prompt for OpenAI to process search query"""
        
        categories_str = ", ".join(self.product_categories)
        
        prompt = f"""
You are an AI assistant for an e-commerce search system. Your job is to:
1. Correct any typos or spelling mistakes in the search query
2. Extract the main product intent and keywords
3. Classify the search intent
4. Convert natural language to searchable product terms

Available product categories: {categories_str}

Input query: "{query}"

Please respond with a JSON object containing:
{{
    "corrected_query": "corrected version of the query with typos fixed",
    "product_keywords": ["list", "of", "main", "product", "terms"],
    "search_intent": "buy|compare|browse|specific|question",
    "intent_confidence": 0.8,
    "typo_corrections": [
        {{"original": "word", "corrected": "word", "confidence": 0.9}}
    ],
    "semantic_keywords": ["additional", "related", "terms"],
    "explanation": "brief explanation of what the user is looking for"
}}

Examples:
- "Hro Hodie" → corrected_query: "Hero Hoodie", product_keywords: ["hero", "hoodie"]
- "I want to buy a comfortable hoodie" → corrected_query: "comfortable hoodie", product_keywords: ["comfortable", "hoodie"]
- "best running shoes" → corrected_query: "running shoes", product_keywords: ["running", "shoes"]

Focus on extracting the core product terms and fixing obvious typos.
"""
        return prompt

    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API with the prompt"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant for e-commerce search. Always respond with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Low temperature for consistent results
            "max_tokens": 500,
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                raise ValueError("No choices in OpenAI response")
                
            content = result['choices'][0]['message']['content']
            
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse OpenAI JSON response", content=content, error=str(e))
                raise ValueError(f"Invalid JSON from OpenAI: {e}")

    def _parse_openai_response(self, response: Dict[str, Any], original_query: str) -> Tuple[SearchIntent, List[QueryCorrection]]:
        """Parse OpenAI response into SearchIntent and QueryCorrection objects"""
        
        # Extract data from OpenAI response
        corrected_query = response.get('corrected_query', original_query)
        product_keywords = response.get('product_keywords', [])
        semantic_keywords = response.get('semantic_keywords', [])
        intent_type = response.get('search_intent', 'specific')
        confidence = response.get('intent_confidence', 0.7)
        typo_corrections = response.get('typo_corrections', [])
        
        # Combine all keywords
        all_keywords = product_keywords + semantic_keywords
        
        # Create SearchIntent
        search_intent = SearchIntent(
            intent_type=intent_type,
            confidence=confidence,
            entities=[],  # Could be enhanced to extract entities
            keywords=all_keywords,
            original_query=original_query,
            processed_query=corrected_query,
            corrections=[c.get('corrected', '') for c in typo_corrections]
        )
        
        # Create QueryCorrection objects
        corrections = []
        for correction in typo_corrections:
            if correction.get('original') and correction.get('corrected'):
                corrections.append(QueryCorrection(
                    original=correction['original'],
                    corrected=correction['corrected'],
                    confidence=correction.get('confidence', 0.8),
                    correction_type='openai_correction'
                ))
        
        return search_intent, corrections

    async def _basic_process_query(self, query: str) -> Tuple[SearchIntent, List[QueryCorrection]]:
        """Basic fallback processing when OpenAI is not available"""
        
        # Simple typo corrections
        basic_typos = {
            'hro': 'hero',
            'hodie': 'hoodie',
            'hoddie': 'hoodie',
            'comfortble': 'comfortable',
            'runing': 'running',
            'shose': 'shoes'
        }
        
        corrected_query = query.lower()
        corrections = []
        
        for typo, correction in basic_typos.items():
            if typo in corrected_query:
                corrected_query = corrected_query.replace(typo, correction)
                corrections.append(QueryCorrection(
                    original=typo,
                    corrected=correction,
                    confidence=0.9,
                    correction_type='basic_correction'
                ))
        
        # Extract keywords (remove common words)
        stop_words = {'i', 'want', 'to', 'buy', 'a', 'an', 'the', 'for', 'looking', 'find', 'get', 'need'}
        words = corrected_query.split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Determine intent
        intent_type = 'specific'
        if any(word in query.lower() for word in ['buy', 'purchase', 'want', 'need']):
            intent_type = 'buy'
        elif any(word in query.lower() for word in ['compare', 'vs', 'versus']):
            intent_type = 'compare'
        
        search_intent = SearchIntent(
            intent_type=intent_type,
            confidence=0.6,
            entities=[],
            keywords=keywords,
            original_query=query,
            processed_query=corrected_query,
            corrections=[c.corrected for c in corrections]
        )
        
        return search_intent, corrections


# Create global instance
openai_nlp_processor = OpenAINLPProcessor()


async def process_query_with_openai(query: str) -> Tuple[SearchIntent, List[QueryCorrection]]:
    """Convenience function to process query with OpenAI"""
    return await openai_nlp_processor.process_search_query(query)
