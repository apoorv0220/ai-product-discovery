"""
Advanced Conversational AI Shopping Assistant
Implements natural language processing, product discovery chat, guided shopping flows, and multi-turn conversations
"""

import asyncio
import re
import json
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog
from textdistance import jaro_winkler
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tag import pos_tag
import random

logger = structlog.get_logger()


class ConversationState(str, Enum):
    """Conversation states"""
    GREETING = "greeting"
    INTENT_DETECTION = "intent_detection"
    PRODUCT_DISCOVERY = "product_discovery"
    PRODUCT_COMPARISON = "product_comparison"
    CART_ASSISTANCE = "cart_assistance"
    CHECKOUT_GUIDANCE = "checkout_guidance"
    SUPPORT = "support"
    RECOMMENDATION = "recommendation"
    ENDING = "ending"


class UserIntent(str, Enum):
    """User intent types"""
    PRODUCT_SEARCH = "product_search"
    PRODUCT_COMPARISON = "product_comparison"
    PRICE_INQUIRY = "price_inquiry"
    AVAILABILITY_CHECK = "availability_check"
    RECOMMENDATION_REQUEST = "recommendation_request"
    CART_HELP = "cart_help"
    ORDER_STATUS = "order_status"
    RETURN_INQUIRY = "return_inquiry"
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    GOODBYE = "goodbye"


@dataclass
class ConversationContext:
    """Conversation context and memory"""
    session_id: str
    user_id: Optional[str]
    state: ConversationState
    intent: Optional[UserIntent]
    entities: Dict[str, Any] = field(default_factory=dict)
    products_discussed: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_cart: List[Dict[str, Any]] = field(default_factory=list)
    last_interaction: datetime = field(default_factory=datetime.utcnow)
    conversation_flow: List[str] = field(default_factory=list)


@dataclass
class AIResponse:
    """AI assistant response"""
    message: str
    state: ConversationState
    suggested_actions: List[Dict[str, Any]] = field(default_factory=list)
    product_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NaturalLanguageProcessor:
    """Advanced NLP processor for conversation understanding"""
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Intent patterns
        self.intent_patterns = {
            UserIntent.PRODUCT_SEARCH: [
                r'\b(looking for|find|search|need|want|buy|purchase|get)\b.*\b(product|item|thing)\b',
                r'\b(show me|find me|get me)\b.*',
                r'\b(where can i find|how do i get)\b.*',
                r'\b(i need|i want|i\'m looking for)\b.*'
            ],
            UserIntent.PRODUCT_COMPARISON: [
                r'\b(compare|vs|versus|difference|better|best)\b',
                r'\b(which is better|what\'s the difference)\b',
                r'\b(pros and cons|advantages|disadvantages)\b'
            ],
            UserIntent.PRICE_INQUIRY: [
                r'\b(price|cost|how much|expensive|cheap|affordable)\b',
                r'\b(what does.*cost|how much is)\b',
                r'\b(budget|price range)\b'
            ],
            UserIntent.AVAILABILITY_CHECK: [
                r'\b(available|in stock|out of stock|stock)\b',
                r'\b(do you have|is.*available)\b',
                r'\b(when will.*be available)\b'
            ],
            UserIntent.RECOMMENDATION_REQUEST: [
                r'\b(recommend|suggest|advice|what should)\b',
                r'\b(best.*for|good.*for|right.*for)\b',
                r'\b(help me choose|help me decide)\b'
            ],
            UserIntent.CART_HELP: [
                r'\b(cart|basket|add to cart|remove from cart)\b',
                r'\b(checkout|order|buy now)\b'
            ],
            UserIntent.GREETING: [
                r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b',
                r'\b(how are you|what\'s up|greetings)\b'
            ],
            UserIntent.GOODBYE: [
                r'\b(bye|goodbye|see you|thanks|thank you|that\'s all)\b',
                r'\b(i\'m done|nothing else|no more questions)\b'
            ]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'product_type': [
                r'\b(hoodie|shirt|jacket|pants|shoes|watch|phone|laptop|bag)\b',
                r'\b(t-shirt|sweater|jeans|sneakers|boots|dress|skirt)\b'
            ],
            'brand': [
                r'\b(nike|adidas|apple|samsung|sony|hero|zara|h&m)\b'
            ],
            'color': [
                r'\b(red|blue|green|yellow|black|white|gray|grey|pink|purple|orange|brown)\b'
            ],
            'size': [
                r'\b(small|medium|large|xl|xxl|xs|s|m|l)\b',
                r'\b(size \d+|us \d+|uk \d+)\b'
            ],
            'price_range': [
                r'\$\d+[\-\s]*\$?\d*',
                r'\b(under|below|less than|more than|above|over)\s*\$?\d+\b',
                r'\b(cheap|expensive|affordable|budget|premium|luxury)\b'
            ]
        }
        
        # Conversation templates
        self.response_templates = {
            ConversationState.GREETING: [
                "Hello! I'm your AI shopping assistant. How can I help you find the perfect product today?",
                "Hi there! I'm here to help you discover amazing products. What are you looking for?",
                "Welcome! I'm your personal shopping assistant. What can I help you find today?"
            ],
            ConversationState.PRODUCT_DISCOVERY: [
                "I found some great options for you! Let me show you what I discovered.",
                "Based on what you're looking for, here are some perfect matches:",
                "I think you'll love these products that match your needs:"
            ],
            ConversationState.PRODUCT_COMPARISON: [
                "Let me help you compare these products to find the best option:",
                "Here's a detailed comparison to help you decide:",
                "I'll break down the differences to help you choose:"
            ],
            ConversationState.RECOMMENDATION: [
                "Based on your preferences, I recommend these products:",
                "I think you might also like these similar items:",
                "Customers with similar tastes also loved these products:"
            ]
        }
    
    async def process_message(self, message: str, context: ConversationContext) -> Tuple[UserIntent, Dict[str, Any]]:
        """Process user message to extract intent and entities"""
        try:
            message_lower = message.lower().strip()
            
            # Extract intent
            intent = await self._extract_intent(message_lower)
            
            # Extract entities
            entities = await self._extract_entities(message_lower)
            
            # Update context entities
            for entity_type, values in entities.items():
                if entity_type not in context.entities:
                    context.entities[entity_type] = []
                context.entities[entity_type].extend(values)
            
            logger.debug("Processed message", intent=intent, entities=entities)
            
            return intent, entities
            
        except Exception as e:
            logger.error("Error processing message", error=str(e))
            return UserIntent.GENERAL_QUESTION, {}
    
    async def _extract_intent(self, message: str) -> UserIntent:
        """Extract user intent from message"""
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return intent
        
        return UserIntent.GENERAL_QUESTION
    
    async def _extract_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract entities from message"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            entity_values = []
            for pattern in patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                entity_values.extend(matches)
            
            if entity_values:
                entities[entity_type] = list(set(entity_values))  # Remove duplicates
        
        return entities
    
    def generate_response_template(self, state: ConversationState, custom_message: str = None) -> str:
        """Generate response template based on conversation state"""
        if custom_message:
            return custom_message
        
        templates = self.response_templates.get(state, ["I understand. How can I help you further?"])
        return random.choice(templates)


class ConversationalAI:
    """Main conversational AI shopping assistant"""
    
    def __init__(self):
        self.nlp_processor = NaturalLanguageProcessor()
        self.conversation_contexts = {}  # session_id -> ConversationContext
        self.product_catalog = {}  # Cached product data
        self.conversation_flows = {}  # Predefined conversation flows
        
        # Initialize conversation flows
        self._initialize_conversation_flows()
    
    def _initialize_conversation_flows(self):
        """Initialize predefined conversation flows"""
        self.conversation_flows = {
            'product_discovery': [
                ConversationState.INTENT_DETECTION,
                ConversationState.PRODUCT_DISCOVERY,
                ConversationState.RECOMMENDATION,
                ConversationState.CART_ASSISTANCE
            ],
            'comparison_flow': [
                ConversationState.INTENT_DETECTION,
                ConversationState.PRODUCT_COMPARISON,
                ConversationState.RECOMMENDATION,
                ConversationState.CART_ASSISTANCE
            ],
            'support_flow': [
                ConversationState.INTENT_DETECTION,
                ConversationState.SUPPORT,
                ConversationState.ENDING
            ]
        }
    
    async def process_conversation(self, session_id: str, user_id: Optional[str], 
                                 message: str, context_data: Dict[str, Any] = None) -> AIResponse:
        """Process conversation turn and generate AI response"""
        try:
            # Get or create conversation context
            context = await self._get_or_create_context(session_id, user_id)
            
            # Update context with any external data
            if context_data:
                context.entities.update(context_data.get('entities', {}))
                if 'current_cart' in context_data:
                    context.current_cart = context_data['current_cart']
            
            # Add user message to history
            context.conversation_history.append({
                'role': 'user',
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'intent': None  # Will be filled after processing
            })
            
            # Process message with NLP
            intent, entities = await self.nlp_processor.process_message(message, context)
            
            # Update intent in conversation history
            context.conversation_history[-1]['intent'] = intent
            
            # Update context
            context.intent = intent
            context.last_interaction = datetime.utcnow()
            
            # Generate response based on intent and state
            response = await self._generate_response(context, intent, entities, message)
            
            # Add AI response to history
            context.conversation_history.append({
                'role': 'assistant',
                'message': response.message,
                'timestamp': datetime.utcnow().isoformat(),
                'state': response.state,
                'products_recommended': len(response.product_recommendations)
            })
            
            # Update conversation state
            context.state = response.state
            context.conversation_flow.append(response.state)
            
            logger.info("Processed conversation turn", 
                       session_id=session_id, intent=intent, state=response.state)
            
            return response
            
        except Exception as e:
            logger.error("Error processing conversation", error=str(e))
            return AIResponse(
                message="I apologize, but I'm having trouble understanding. Could you please rephrase your question?",
                state=ConversationState.INTENT_DETECTION
            )
    
    async def _get_or_create_context(self, session_id: str, user_id: Optional[str]) -> ConversationContext:
        """Get existing context or create new one"""
        if session_id not in self.conversation_contexts:
            self.conversation_contexts[session_id] = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                state=ConversationState.GREETING
            )
        
        return self.conversation_contexts[session_id]
    
    async def _generate_response(self, context: ConversationContext, intent: UserIntent, 
                               entities: Dict[str, Any], message: str) -> AIResponse:
        """Generate AI response based on intent and context"""
        
        if intent == UserIntent.GREETING or context.state == ConversationState.GREETING:
            return await self._handle_greeting(context)
        
        elif intent == UserIntent.PRODUCT_SEARCH:
            return await self._handle_product_search(context, entities, message)
        
        elif intent == UserIntent.PRODUCT_COMPARISON:
            return await self._handle_product_comparison(context, entities)
        
        elif intent == UserIntent.RECOMMENDATION_REQUEST:
            return await self._handle_recommendation_request(context, entities)
        
        elif intent == UserIntent.PRICE_INQUIRY:
            return await self._handle_price_inquiry(context, entities)
        
        elif intent == UserIntent.AVAILABILITY_CHECK:
            return await self._handle_availability_check(context, entities)
        
        elif intent == UserIntent.CART_HELP:
            return await self._handle_cart_assistance(context, entities)
        
        elif intent == UserIntent.GOODBYE:
            return await self._handle_goodbye(context)
        
        else:
            return await self._handle_general_question(context, message)
    
    async def _handle_greeting(self, context: ConversationContext) -> AIResponse:
        """Handle greeting and conversation start"""
        greeting_message = self.nlp_processor.generate_response_template(ConversationState.GREETING)
        
        return AIResponse(
            message=greeting_message,
            state=ConversationState.INTENT_DETECTION,
            suggested_actions=[
                {"action": "search_products", "label": "Search for products"},
                {"action": "get_recommendations", "label": "Get product recommendations"},
                {"action": "view_cart", "label": "View my cart"},
                {"action": "browse_categories", "label": "Browse categories"}
            ]
        )
    
    async def _handle_product_search(self, context: ConversationContext, 
                                   entities: Dict[str, Any], message: str) -> AIResponse:
        """Handle product search requests"""
        try:
            # Build search query from entities and message
            search_query = await self._build_search_query(entities, message)
            
            # Search for products
            products = await self._search_products(search_query, context)
            
            if not products:
                return AIResponse(
                    message="I couldn't find any products matching your criteria. Could you try a different search or be more specific?",
                    state=ConversationState.PRODUCT_DISCOVERY,
                    suggested_actions=[
                        {"action": "refine_search", "label": "Refine search criteria"},
                        {"action": "browse_categories", "label": "Browse categories instead"},
                        {"action": "get_recommendations", "label": "Get general recommendations"}
                    ]
                )
            
            # Generate response message
            if len(products) == 1:
                response_message = f"I found the perfect product for you! Here's a {products[0]['name']} that matches what you're looking for."
            else:
                response_message = f"Great! I found {len(products)} products that match your search. Here are the top options:"
            
            # Add personalized touch based on entities
            if 'brand' in entities:
                response_message += f" I noticed you mentioned {', '.join(entities['brand'])}, so I prioritized those brands."
            
            return AIResponse(
                message=response_message,
                state=ConversationState.PRODUCT_DISCOVERY,
                product_recommendations=products,
                suggested_actions=[
                    {"action": "view_product", "label": "View product details"},
                    {"action": "compare_products", "label": "Compare similar products"},
                    {"action": "add_to_cart", "label": "Add to cart"},
                    {"action": "refine_search", "label": "Refine search"}
                ],
                metadata={
                    "search_query": search_query,
                    "entities_used": entities,
                    "products_found": len(products)
                }
            )
            
        except Exception as e:
            logger.error("Error handling product search", error=str(e))
            return AIResponse(
                message="I'm having trouble searching for products right now. Let me help you in another way.",
                state=ConversationState.INTENT_DETECTION
            )
    
    async def _handle_product_comparison(self, context: ConversationContext, 
                                       entities: Dict[str, Any]) -> AIResponse:
        """Handle product comparison requests"""
        try:
            # Get products to compare from context or entities
            products_to_compare = []
            
            if context.products_discussed:
                # Use recently discussed products
                products_to_compare = await self._get_products_by_ids(context.products_discussed[-3:])
            else:
                # Search for products based on entities
                search_query = await self._build_search_query(entities, "")
                products_to_compare = await self._search_products(search_query, context, limit=3)
            
            if len(products_to_compare) < 2:
                return AIResponse(
                    message="I need at least 2 products to compare. Could you tell me which specific products you'd like to compare?",
                    state=ConversationState.PRODUCT_COMPARISON,
                    suggested_actions=[
                        {"action": "search_products", "label": "Search for products first"},
                        {"action": "get_recommendations", "label": "Get product recommendations"}
                    ]
                )
            
            # Generate comparison
            comparison = await self._generate_product_comparison(products_to_compare)
            
            return AIResponse(
                message=f"Here's a detailed comparison of {len(products_to_compare)} products to help you decide:",
                state=ConversationState.PRODUCT_COMPARISON,
                product_recommendations=products_to_compare,
                metadata={
                    "comparison": comparison,
                    "products_compared": [p['id'] for p in products_to_compare]
                },
                suggested_actions=[
                    {"action": "view_product", "label": "View detailed specs"},
                    {"action": "add_to_cart", "label": "Add preferred product to cart"},
                    {"action": "get_more_options", "label": "See more options"}
                ]
            )
            
        except Exception as e:
            logger.error("Error handling product comparison", error=str(e))
            return AIResponse(
                message="I'm having trouble comparing products right now. Could you try searching for specific products first?",
                state=ConversationState.PRODUCT_DISCOVERY
            )
    
    async def _handle_recommendation_request(self, context: ConversationContext, 
                                           entities: Dict[str, Any]) -> AIResponse:
        """Handle recommendation requests"""
        try:
            # Get personalized recommendations
            recommendations = await self._get_personalized_recommendations(context, entities)
            
            if not recommendations:
                return AIResponse(
                    message="I'd love to give you personalized recommendations! Could you tell me more about what you're looking for or your preferences?",
                    state=ConversationState.RECOMMENDATION,
                    suggested_actions=[
                        {"action": "tell_preferences", "label": "Tell me your preferences"},
                        {"action": "browse_popular", "label": "Show popular products"},
                        {"action": "search_specific", "label": "Search for something specific"}
                    ]
                )
            
            # Generate personalized message
            message = "Based on your interests and preferences, I think you'll love these products:"
            
            if 'product_type' in entities:
                message += f" I focused on {', '.join(entities['product_type'])} since that's what you mentioned."
            
            return AIResponse(
                message=message,
                state=ConversationState.RECOMMENDATION,
                product_recommendations=recommendations,
                suggested_actions=[
                    {"action": "view_product", "label": "View product details"},
                    {"action": "add_to_cart", "label": "Add to cart"},
                    {"action": "get_more_recommendations", "label": "See more recommendations"},
                    {"action": "refine_preferences", "label": "Refine preferences"}
                ],
                metadata={
                    "recommendation_reason": "personalized",
                    "entities_considered": entities
                }
            )
            
        except Exception as e:
            logger.error("Error handling recommendation request", error=str(e))
            return AIResponse(
                message="Let me show you some popular products that might interest you!",
                state=ConversationState.RECOMMENDATION
            )
    
    async def _handle_price_inquiry(self, context: ConversationContext, 
                                  entities: Dict[str, Any]) -> AIResponse:
        """Handle price-related questions"""
        if not context.products_discussed:
            return AIResponse(
                message="I'd be happy to help with pricing! Which product are you asking about? You can search for a product or ask me for recommendations.",
                state=ConversationState.PRODUCT_DISCOVERY,
                suggested_actions=[
                    {"action": "search_products", "label": "Search for products"},
                    {"action": "browse_categories", "label": "Browse by category"}
                ]
            )
        
        # Get price information for recently discussed products
        latest_product_id = context.products_discussed[-1]
        product = await self._get_product_by_id(latest_product_id)
        
        if not product:
            return AIResponse(
                message="I couldn't find pricing information for that product. Let me help you find something else.",
                state=ConversationState.PRODUCT_DISCOVERY
            )
        
        price_message = f"The {product['name']} is priced at ${product.get('price', 'N/A')}"
        
        # Add price context
        if product.get('special_price'):
            price_message += f" (on sale from ${product['original_price']})"
        
        if 'price_range' in entities:
            budget_range = entities['price_range'][0]
            price_message += f". Based on your budget of {budget_range}, this might be a good fit!"
        
        return AIResponse(
            message=price_message,
            state=ConversationState.PRODUCT_DISCOVERY,
            product_recommendations=[product],
            suggested_actions=[
                {"action": "add_to_cart", "label": "Add to cart"},
                {"action": "compare_prices", "label": "Compare with similar products"},
                {"action": "check_deals", "label": "Check for deals and discounts"}
            ]
        )
    
    async def _handle_availability_check(self, context: ConversationContext, 
                                       entities: Dict[str, Any]) -> AIResponse:
        """Handle availability and stock inquiries"""
        if not context.products_discussed:
            return AIResponse(
                message="I can check availability for you! Which product are you interested in?",
                state=ConversationState.PRODUCT_DISCOVERY
            )
        
        latest_product_id = context.products_discussed[-1]
        product = await self._get_product_by_id(latest_product_id)
        
        if not product:
            return AIResponse(
                message="I couldn't find that product. Let me help you search for something else.",
                state=ConversationState.PRODUCT_DISCOVERY
            )
        
        is_in_stock = product.get('is_in_stock', True)
        stock_quantity = product.get('quantity', 0)
        
        if is_in_stock and stock_quantity > 10:
            availability_message = f"Great news! The {product['name']} is in stock and ready to ship."
        elif is_in_stock and stock_quantity > 0:
            availability_message = f"The {product['name']} is in stock, but only {stock_quantity} left!"
        else:
            availability_message = f"Sorry, the {product['name']} is currently out of stock. Let me suggest some similar alternatives."
        
        return AIResponse(
            message=availability_message,
            state=ConversationState.PRODUCT_DISCOVERY,
            product_recommendations=[product] if is_in_stock else [],
            suggested_actions=[
                {"action": "add_to_cart", "label": "Add to cart"} if is_in_stock else {"action": "notify_when_available", "label": "Notify when available"},
                {"action": "find_alternatives", "label": "Find similar products"},
                {"action": "check_other_sizes", "label": "Check other sizes/variants"}
            ]
        )
    
    async def _handle_cart_assistance(self, context: ConversationContext, 
                                    entities: Dict[str, Any]) -> AIResponse:
        """Handle cart-related assistance"""
        cart_items = len(context.current_cart)
        
        if cart_items == 0:
            return AIResponse(
                message="Your cart is empty. Let me help you find some great products to add!",
                state=ConversationState.CART_ASSISTANCE,
                suggested_actions=[
                    {"action": "search_products", "label": "Search for products"},
                    {"action": "get_recommendations", "label": "Get recommendations"},
                    {"action": "browse_categories", "label": "Browse categories"}
                ]
            )
        
        cart_value = sum(item.get('price', 0) * item.get('quantity', 1) for item in context.current_cart)
        
        cart_message = f"You have {cart_items} item{'s' if cart_items > 1 else ''} in your cart (total: ${cart_value:.2f}). "
        cart_message += "Would you like to proceed to checkout or need help with anything else?"
        
        return AIResponse(
            message=cart_message,
            state=ConversationState.CART_ASSISTANCE,
            suggested_actions=[
                {"action": "view_cart", "label": "View cart details"},
                {"action": "checkout", "label": "Proceed to checkout"},
                {"action": "add_more_items", "label": "Add more items"},
                {"action": "get_cart_recommendations", "label": "Get recommendations based on cart"}
            ],
            metadata={
                "cart_items": cart_items,
                "cart_value": cart_value
            }
        )
    
    async def _handle_goodbye(self, context: ConversationContext) -> AIResponse:
        """Handle conversation ending"""
        goodbye_messages = [
            "Thank you for shopping with us! I hope I was able to help you find what you were looking for. Have a great day!",
            "It was my pleasure helping you today! Feel free to come back anytime if you need more assistance. Happy shopping!",
            "Thanks for chatting with me! I'm always here to help with your shopping needs. Take care!"
        ]
        
        return AIResponse(
            message=random.choice(goodbye_messages),
            state=ConversationState.ENDING,
            suggested_actions=[
                {"action": "view_cart", "label": "View cart before leaving"},
                {"action": "save_conversation", "label": "Save this conversation"},
                {"action": "start_new_chat", "label": "Start new conversation"}
            ]
        )
    
    async def _handle_general_question(self, context: ConversationContext, message: str) -> AIResponse:
        """Handle general questions and provide helpful responses"""
        
        # Try to provide helpful information based on message content
        helpful_responses = {
            "hours": "Our online store is available 24/7! You can browse and shop anytime.",
            "shipping": "We offer free shipping on orders over $50, with standard delivery in 3-5 business days.",
            "return": "We have a 30-day return policy. Items must be in original condition for a full refund.",
            "contact": "You can reach our customer service team through this chat, email, or phone during business hours.",
            "size": "Each product page has a detailed size guide. I can also help you find the right size!",
            "material": "Product materials and care instructions are listed on each product page."
        }
        
        message_lower = message.lower()
        for keyword, response in helpful_responses.items():
            if keyword in message_lower:
                return AIResponse(
                    message=response + " Is there anything specific I can help you find?",
                    state=ConversationState.INTENT_DETECTION,
                    suggested_actions=[
                        {"action": "search_products", "label": "Search for products"},
                        {"action": "get_recommendations", "label": "Get recommendations"},
                        {"action": "contact_support", "label": "Contact customer support"}
                    ]
                )
        
        # Default helpful response
        return AIResponse(
            message="I understand you have a question! While I specialize in helping you find and discover products, I'm here to assist. What are you looking for today?",
            state=ConversationState.INTENT_DETECTION,
            suggested_actions=[
                {"action": "search_products", "label": "Search for products"},
                {"action": "get_recommendations", "label": "Get product recommendations"},
                {"action": "browse_categories", "label": "Browse categories"},
                {"action": "contact_support", "label": "Contact human support"}
            ]
        )
    
    async def _build_search_query(self, entities: Dict[str, Any], message: str) -> str:
        """Build search query from entities and message"""
        query_parts = []
        
        # Add product types
        if 'product_type' in entities:
            query_parts.extend(entities['product_type'])
        
        # Add brands
        if 'brand' in entities:
            query_parts.extend(entities['brand'])
        
        # Add colors
        if 'color' in entities:
            query_parts.extend(entities['color'])
        
        # Extract additional keywords from message
        message_words = [word for word in message.lower().split() 
                        if word not in self.nlp_processor.stop_words and len(word) > 2]
        query_parts.extend(message_words[:3])  # Add up to 3 additional keywords
        
        return ' '.join(query_parts) if query_parts else message
    
    async def _search_products(self, query: str, context: ConversationContext, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for products using the search service"""
        try:
            # This would integrate with the search service
            # For now, return mock data structure
            mock_products = [
                {
                    'id': 'prod_1',
                    'name': f'Product matching {query}',
                    'price': 99.99,
                    'image_url': '/images/product1.jpg',
                    'description': f'Great product for {query}',
                    'is_in_stock': True,
                    'rating': 4.5,
                    'reviews_count': 123
                }
            ]
            
            # Update context with discussed products
            for product in mock_products:
                if product['id'] not in context.products_discussed:
                    context.products_discussed.append(product['id'])
            
            return mock_products[:limit]
            
        except Exception as e:
            logger.error("Error searching products", error=str(e))
            return []
    
    async def _get_personalized_recommendations(self, context: ConversationContext, 
                                             entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get personalized product recommendations"""
        try:
            # This would integrate with the recommendation service
            # Consider user preferences, conversation history, and current context
            
            recommendations = []
            
            # If user has discussed products, recommend similar ones
            if context.products_discussed:
                # Get similar products
                pass
            
            # If user has specified entities, use them for recommendations
            if entities:
                # Get products matching entities
                pass
            
            # Default recommendations based on user profile
            mock_recommendations = [
                {
                    'id': 'rec_1',
                    'name': 'Recommended Product 1',
                    'price': 79.99,
                    'image_url': '/images/rec1.jpg',
                    'description': 'Personalized recommendation',
                    'is_in_stock': True,
                    'rating': 4.7,
                    'recommendation_reason': 'Based on your preferences'
                }
            ]
            
            return mock_recommendations
            
        except Exception as e:
            logger.error("Error getting recommendations", error=str(e))
            return []
    
    async def _get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by ID"""
        # This would fetch from product catalog
        return self.product_catalog.get(product_id)
    
    async def _get_products_by_ids(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple products by IDs"""
        products = []
        for product_id in product_ids:
            product = await self._get_product_by_id(product_id)
            if product:
                products.append(product)
        return products
    
    async def _generate_product_comparison(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate detailed product comparison"""
        comparison = {
            'products': products,
            'comparison_matrix': {},
            'winner_categories': {},
            'summary': ''
        }
        
        # Compare key attributes
        attributes = ['price', 'rating', 'reviews_count']
        
        for attr in attributes:
            values = [p.get(attr, 0) for p in products]
            if attr == 'price':
                # Lower price wins
                best_idx = values.index(min(values))
            else:
                # Higher value wins
                best_idx = values.index(max(values))
            
            comparison['winner_categories'][attr] = products[best_idx]['name']
            comparison['comparison_matrix'][attr] = values
        
        return comparison


# Global instance
conversational_ai = ConversationalAI()
