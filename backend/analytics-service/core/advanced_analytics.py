"""
Advanced Real-Time Analytics Engine
Implements behavioral analytics, predictive insights, A/B testing, and conversion optimization
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import structlog
import json
import uuid
from enum import Enum
import statistics
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings('ignore')

logger = structlog.get_logger()


class EventType(str, Enum):
    """Analytics event types"""
    PAGE_VIEW = "page_view"
    PRODUCT_VIEW = "product_view"
    SEARCH = "search"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    PURCHASE = "purchase"
    WISHLIST_ADD = "wishlist_add"
    RECOMMENDATION_CLICK = "recommendation_click"
    FILTER_APPLY = "filter_apply"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class AnalyticsEvent:
    """Analytics event data structure"""
    event_id: str
    user_id: Optional[str]
    session_id: str
    event_type: EventType
    timestamp: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    page_url: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


@dataclass
class UserSegment:
    """User behavioral segment"""
    segment_id: str
    name: str
    description: str
    criteria: Dict[str, Any]
    user_count: int = 0
    conversion_rate: float = 0.0
    avg_order_value: float = 0.0
    characteristics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionFunnel:
    """Conversion funnel analysis"""
    funnel_id: str
    name: str
    steps: List[Dict[str, Any]]
    conversion_rates: List[float]
    drop_off_points: List[Dict[str, Any]]
    total_users: int
    completed_users: int


@dataclass
class ABTestResult:
    """A/B test results"""
    test_id: str
    test_name: str
    variants: Dict[str, Dict[str, Any]]
    winner: Optional[str] = None
    confidence: float = 0.0
    lift: float = 0.0
    statistical_significance: bool = False


class RealTimeAnalyticsEngine:
    """Real-time analytics processing engine"""
    
    def __init__(self):
        self.event_buffer = deque(maxlen=10000)  # Recent events buffer
        self.session_data = {}  # Active sessions
        self.user_profiles = {}  # User behavioral profiles
        self.segments = {}  # User segments
        self.ab_tests = {}  # Active A/B tests
        self.conversion_funnels = {}  # Conversion funnels
        self.real_time_metrics = {}  # Real-time metrics cache
        self.predictive_models = {}  # ML models for predictions
        
        # Time windows for aggregations
        self.time_windows = {
            'real_time': timedelta(minutes=5),
            'hourly': timedelta(hours=1),
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1)
        }
    
    async def initialize(self) -> None:
        """Initialize the analytics engine"""
        try:
            logger.info("Initializing advanced analytics engine")
            
            # Load existing segments
            await self._load_user_segments()
            
            # Load A/B tests
            await self._load_ab_tests()
            
            # Load conversion funnels
            await self._load_conversion_funnels()
            
            # Initialize predictive models
            await self._initialize_predictive_models()
            
            # Start background tasks
            asyncio.create_task(self._process_events_continuously())
            asyncio.create_task(self._update_real_time_metrics())
            asyncio.create_task(self._process_user_segmentation())
            
            logger.info("Advanced analytics engine initialized")
            
        except Exception as e:
            logger.error("Error initializing analytics engine", error=str(e))
    
    async def track_event(self, event: AnalyticsEvent) -> None:
        """Track a new analytics event"""
        try:
            # Add to event buffer
            self.event_buffer.append(event)
            
            # Process event immediately for real-time metrics
            await self._process_event_real_time(event)
            
            # Update session data
            await self._update_session(event)
            
            # Update user profile
            await self._update_user_profile(event)
            
            # Check A/B test participation
            await self._process_ab_test_event(event)
            
            # Update conversion funnels
            await self._update_conversion_funnels(event)
            
            logger.debug("Event tracked", event_type=event.event_type, 
                        user_id=event.user_id, session_id=event.session_id)
            
        except Exception as e:
            logger.error("Error tracking event", error=str(e))
    
    async def _process_event_real_time(self, event: AnalyticsEvent) -> None:
        """Process event for real-time metrics"""
        current_time = datetime.utcnow()
        time_bucket = current_time.replace(second=0, microsecond=0)
        
        # Initialize metrics for this time bucket
        if time_bucket not in self.real_time_metrics:
            self.real_time_metrics[time_bucket] = {
                'total_events': 0,
                'unique_users': set(),
                'page_views': 0,
                'product_views': 0,
                'searches': 0,
                'add_to_carts': 0,
                'purchases': 0,
                'revenue': 0.0,
                'conversion_rate': 0.0
            }
        
        metrics = self.real_time_metrics[time_bucket]
        
        # Update metrics
        metrics['total_events'] += 1
        if event.user_id:
            metrics['unique_users'].add(event.user_id)
        
        if event.event_type == EventType.PAGE_VIEW:
            metrics['page_views'] += 1
        elif event.event_type == EventType.PRODUCT_VIEW:
            metrics['product_views'] += 1
        elif event.event_type == EventType.SEARCH:
            metrics['searches'] += 1
        elif event.event_type == EventType.ADD_TO_CART:
            metrics['add_to_carts'] += 1
        elif event.event_type == EventType.PURCHASE:
            metrics['purchases'] += 1
            # Add revenue if available
            if 'order_value' in event.properties:
                metrics['revenue'] += event.properties['order_value']
        
        # Calculate conversion rate
        if metrics['unique_users']:
            metrics['conversion_rate'] = metrics['purchases'] / len(metrics['unique_users'])
    
    async def _update_session(self, event: AnalyticsEvent) -> None:
        """Update session data"""
        session_id = event.session_id
        
        if session_id not in self.session_data:
            self.session_data[session_id] = {
                'user_id': event.user_id,
                'start_time': event.timestamp,
                'last_activity': event.timestamp,
                'page_views': 0,
                'events': [],
                'total_duration': 0,
                'pages_visited': set(),
                'products_viewed': set(),
                'searches': [],
                'cart_additions': 0,
                'purchases': 0,
                'bounce': True
            }
        
        session = self.session_data[session_id]
        
        # Update session data
        session['last_activity'] = event.timestamp
        session['events'].append({
            'event_type': event.event_type,
            'timestamp': event.timestamp,
            'properties': event.properties
        })
        
        # Calculate session duration
        session['total_duration'] = (event.timestamp - session['start_time']).total_seconds()
        
        # Track specific event types
        if event.event_type == EventType.PAGE_VIEW:
            session['page_views'] += 1
            if event.page_url:
                session['pages_visited'].add(event.page_url)
            # Update bounce status
            if session['page_views'] > 1:
                session['bounce'] = False
        
        elif event.event_type == EventType.PRODUCT_VIEW:
            if 'product_id' in event.properties:
                session['products_viewed'].add(event.properties['product_id'])
        
        elif event.event_type == EventType.SEARCH:
            if 'query' in event.properties:
                session['searches'].append(event.properties['query'])
        
        elif event.event_type == EventType.ADD_TO_CART:
            session['cart_additions'] += 1
            session['bounce'] = False
        
        elif event.event_type == EventType.PURCHASE:
            session['purchases'] += 1
            session['bounce'] = False
    
    async def _update_user_profile(self, event: AnalyticsEvent) -> None:
        """Update user behavioral profile"""
        if not event.user_id:
            return
        
        user_id = event.user_id
        
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'first_seen': event.timestamp,
                'last_seen': event.timestamp,
                'total_sessions': 0,
                'total_page_views': 0,
                'total_product_views': 0,
                'total_searches': 0,
                'total_cart_additions': 0,
                'total_purchases': 0,
                'total_revenue': 0.0,
                'avg_session_duration': 0.0,
                'preferred_categories': defaultdict(int),
                'search_terms': defaultdict(int),
                'device_types': defaultdict(int),
                'time_of_day_activity': defaultdict(int),
                'day_of_week_activity': defaultdict(int),
                'conversion_probability': 0.5,
                'customer_lifetime_value': 0.0,
                'churn_probability': 0.5
            }
        
        profile = self.user_profiles[user_id]
        
        # Update basic metrics
        profile['last_seen'] = event.timestamp
        
        if event.event_type == EventType.PAGE_VIEW:
            profile['total_page_views'] += 1
        elif event.event_type == EventType.PRODUCT_VIEW:
            profile['total_product_views'] += 1
            # Track category preferences
            if 'category' in event.properties:
                profile['preferred_categories'][event.properties['category']] += 1
        elif event.event_type == EventType.SEARCH:
            profile['total_searches'] += 1
            if 'query' in event.properties:
                profile['search_terms'][event.properties['query']] += 1
        elif event.event_type == EventType.ADD_TO_CART:
            profile['total_cart_additions'] += 1
        elif event.event_type == EventType.PURCHASE:
            profile['total_purchases'] += 1
            if 'order_value' in event.properties:
                profile['total_revenue'] += event.properties['order_value']
        
        # Track temporal patterns
        hour = event.timestamp.hour
        day_of_week = event.timestamp.weekday()
        profile['time_of_day_activity'][hour] += 1
        profile['day_of_week_activity'][day_of_week] += 1
        
        # Track device type
        if 'device_type' in event.properties:
            profile['device_types'][event.properties['device_type']] += 1
    
    async def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Get real-time dashboard metrics"""
        try:
            current_time = datetime.utcnow()
            
            # Get metrics for the last 5 minutes
            recent_metrics = []
            for i in range(5):
                time_bucket = current_time - timedelta(minutes=i)
                time_bucket = time_bucket.replace(second=0, microsecond=0)
                if time_bucket in self.real_time_metrics:
                    metrics = self.real_time_metrics[time_bucket].copy()
                    metrics['unique_users'] = len(metrics['unique_users'])
                    metrics['timestamp'] = time_bucket.isoformat()
                    recent_metrics.append(metrics)
            
            # Calculate aggregated metrics
            total_users = len(set(uid for uid in self.user_profiles.keys()))
            active_sessions = len([s for s in self.session_data.values() 
                                 if (current_time - s['last_activity']).total_seconds() < 300])
            
            # User segmentation summary
            segment_summary = {}
            for segment_id, segment in self.segments.items():
                segment_summary[segment_id] = {
                    'name': segment.name,
                    'user_count': segment.user_count,
                    'conversion_rate': segment.conversion_rate
                }
            
            return {
                'timestamp': current_time.isoformat(),
                'real_time_metrics': recent_metrics,
                'summary': {
                    'total_users': total_users,
                    'active_sessions': active_sessions,
                    'total_events_last_hour': sum(m['total_events'] for m in recent_metrics[-12:]),
                    'conversion_rate_last_hour': statistics.mean([m['conversion_rate'] for m in recent_metrics[-12:] if m['conversion_rate'] > 0]) if recent_metrics else 0
                },
                'user_segments': segment_summary,
                'ab_tests': {test_id: test.test_name for test_id, test in self.ab_tests.items()}
            }
            
        except Exception as e:
            logger.error("Error generating real-time dashboard", error=str(e))
            return {}
    
    async def create_user_segments(self) -> None:
        """Create user segments using ML clustering"""
        try:
            logger.info("Creating user segments using ML clustering")
            
            if not self.user_profiles:
                logger.warning("No user profiles available for segmentation")
                return
            
            # Prepare data for clustering
            features = []
            user_ids = []
            
            for user_id, profile in self.user_profiles.items():
                # Create feature vector
                feature_vector = [
                    profile['total_page_views'],
                    profile['total_product_views'],
                    profile['total_searches'],
                    profile['total_cart_additions'],
                    profile['total_purchases'],
                    profile['total_revenue'],
                    profile['avg_session_duration'],
                    len(profile['preferred_categories']),
                    profile['conversion_probability'],
                    profile['customer_lifetime_value']
                ]
                
                features.append(feature_vector)
                user_ids.append(user_id)
            
            if len(features) < 10:  # Need minimum data for clustering
                logger.warning("Insufficient data for user segmentation")
                return
            
            # Standardize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Perform K-means clustering
            n_clusters = min(5, len(features) // 10)  # Dynamic cluster count
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Create segments
            self.segments = {}
            for cluster_id in range(n_clusters):
                cluster_users = [user_ids[i] for i, label in enumerate(cluster_labels) if label == cluster_id]
                
                if not cluster_users:
                    continue
                
                # Analyze cluster characteristics
                cluster_profiles = [self.user_profiles[uid] for uid in cluster_users]
                
                avg_purchases = statistics.mean([p['total_purchases'] for p in cluster_profiles])
                avg_revenue = statistics.mean([p['total_revenue'] for p in cluster_profiles])
                avg_page_views = statistics.mean([p['total_page_views'] for p in cluster_profiles])
                
                # Determine segment name based on characteristics
                if avg_purchases > 5:
                    segment_name = "High-Value Customers"
                elif avg_purchases > 1:
                    segment_name = "Regular Customers"
                elif avg_page_views > 10:
                    segment_name = "Engaged Browsers"
                else:
                    segment_name = "New Visitors"
                
                segment = UserSegment(
                    segment_id=f"segment_{cluster_id}",
                    name=segment_name,
                    description=f"Cluster {cluster_id} - {len(cluster_users)} users",
                    criteria={"cluster_id": cluster_id},
                    user_count=len(cluster_users),
                    conversion_rate=sum(1 for p in cluster_profiles if p['total_purchases'] > 0) / len(cluster_profiles),
                    avg_order_value=avg_revenue / max(avg_purchases, 1),
                    characteristics={
                        "avg_purchases": avg_purchases,
                        "avg_revenue": avg_revenue,
                        "avg_page_views": avg_page_views
                    }
                )
                
                self.segments[segment.segment_id] = segment
            
            logger.info("User segmentation completed", segments_count=len(self.segments))
            
        except Exception as e:
            logger.error("Error creating user segments", error=str(e))
    
    async def predict_user_behavior(self, user_id: str) -> Dict[str, Any]:
        """Predict user behavior using ML models"""
        try:
            if user_id not in self.user_profiles:
                return {"error": "User profile not found"}
            
            profile = self.user_profiles[user_id]
            
            # Prepare features for prediction
            features = np.array([[
                profile['total_page_views'],
                profile['total_product_views'],
                profile['total_searches'],
                profile['total_cart_additions'],
                profile['total_purchases'],
                profile['total_revenue'],
                len(profile['preferred_categories']),
                (datetime.utcnow() - profile['last_seen']).days
            ]])
            
            predictions = {}
            
            # Predict conversion probability
            if 'conversion_model' in self.predictive_models:
                conversion_prob = self.predictive_models['conversion_model'].predict_proba(features)[0][1]
                predictions['conversion_probability'] = float(conversion_prob)
            
            # Predict churn probability
            if 'churn_model' in self.predictive_models:
                churn_prob = self.predictive_models['churn_model'].predict_proba(features)[0][1]
                predictions['churn_probability'] = float(churn_prob)
            
            # Calculate customer lifetime value prediction
            if profile['total_purchases'] > 0:
                avg_order_value = profile['total_revenue'] / profile['total_purchases']
                predicted_orders = max(1, int(predictions.get('conversion_probability', 0.5) * 10))
                predictions['predicted_lifetime_value'] = avg_order_value * predicted_orders
            else:
                predictions['predicted_lifetime_value'] = 0.0
            
            # Recommend segment
            user_segment = await self._classify_user_segment(user_id)
            predictions['recommended_segment'] = user_segment
            
            return predictions
            
        except Exception as e:
            logger.error("Error predicting user behavior", error=str(e))
            return {"error": str(e)}
    
    async def create_ab_test(self, test_name: str, variants: List[Dict[str, Any]], 
                           allocation: Dict[str, float] = None) -> str:
        """Create a new A/B test"""
        try:
            test_id = str(uuid.uuid4())
            
            # Default equal allocation if not provided
            if not allocation:
                allocation = {variant['name']: 1.0/len(variants) for variant in variants}
            
            test_variants = {}
            for variant in variants:
                variant_name = variant['name']
                test_variants[variant_name] = {
                    'name': variant_name,
                    'config': variant.get('config', {}),
                    'allocation': allocation.get(variant_name, 0.0),
                    'users': set(),
                    'conversions': 0,
                    'total_revenue': 0.0,
                    'events': []
                }
            
            ab_test = ABTestResult(
                test_id=test_id,
                test_name=test_name,
                variants=test_variants
            )
            
            self.ab_tests[test_id] = ab_test
            
            logger.info("A/B test created", test_id=test_id, test_name=test_name, 
                       variants_count=len(variants))
            
            return test_id
            
        except Exception as e:
            logger.error("Error creating A/B test", error=str(e))
            raise
    
    async def get_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get A/B test results with statistical analysis"""
        try:
            if test_id not in self.ab_tests:
                return {"error": "A/B test not found"}
            
            test = self.ab_tests[test_id]
            
            results = {
                'test_id': test_id,
                'test_name': test.test_name,
                'variants': {},
                'statistical_analysis': {}
            }
            
            # Calculate metrics for each variant
            for variant_name, variant_data in test.variants.items():
                user_count = len(variant_data['users'])
                conversion_rate = variant_data['conversions'] / user_count if user_count > 0 else 0
                avg_revenue = variant_data['total_revenue'] / user_count if user_count > 0 else 0
                
                results['variants'][variant_name] = {
                    'users': user_count,
                    'conversions': variant_data['conversions'],
                    'conversion_rate': conversion_rate,
                    'total_revenue': variant_data['total_revenue'],
                    'avg_revenue_per_user': avg_revenue
                }
            
            # Statistical significance analysis
            if len(test.variants) == 2:
                variant_names = list(test.variants.keys())
                control = results['variants'][variant_names[0]]
                treatment = results['variants'][variant_names[1]]
                
                # Simple statistical significance test (chi-square)
                from scipy.stats import chi2_contingency
                
                if control['users'] > 0 and treatment['users'] > 0:
                    contingency_table = [
                        [control['conversions'], control['users'] - control['conversions']],
                        [treatment['conversions'], treatment['users'] - treatment['conversions']]
                    ]
                    
                    try:
                        chi2, p_value, dof, expected = chi2_contingency(contingency_table)
                        
                        results['statistical_analysis'] = {
                            'p_value': p_value,
                            'statistically_significant': p_value < 0.05,
                            'confidence_level': (1 - p_value) * 100,
                            'lift': (treatment['conversion_rate'] - control['conversion_rate']) / control['conversion_rate'] * 100 if control['conversion_rate'] > 0 else 0
                        }
                        
                        # Determine winner
                        if p_value < 0.05:
                            winner = variant_names[1] if treatment['conversion_rate'] > control['conversion_rate'] else variant_names[0]
                            results['winner'] = winner
                    except:
                        results['statistical_analysis'] = {"error": "Insufficient data for statistical analysis"}
            
            return results
            
        except Exception as e:
            logger.error("Error getting A/B test results", error=str(e))
            return {"error": str(e)}
    
    async def _classify_user_segment(self, user_id: str) -> str:
        """Classify user into appropriate segment"""
        if user_id not in self.user_profiles:
            return "unknown"
        
        profile = self.user_profiles[user_id]
        
        # Simple rule-based classification
        if profile['total_purchases'] > 5:
            return "high_value"
        elif profile['total_purchases'] > 1:
            return "regular_customer"
        elif profile['total_page_views'] > 10:
            return "engaged_browser"
        else:
            return "new_visitor"
    
    async def _process_ab_test_event(self, event: AnalyticsEvent) -> None:
        """Process event for A/B test tracking"""
        if not event.user_id:
            return
        
        for test_id, test in self.ab_tests.items():
            # Check if user is assigned to a variant
            user_variant = None
            for variant_name, variant_data in test.variants.items():
                if event.user_id in variant_data['users']:
                    user_variant = variant_name
                    break
            
            # Assign user to variant if not already assigned
            if not user_variant and event.event_type in [EventType.PAGE_VIEW, EventType.PRODUCT_VIEW]:
                user_variant = self._assign_user_to_variant(event.user_id, test)
                if user_variant:
                    test.variants[user_variant]['users'].add(event.user_id)
            
            # Track conversion events
            if user_variant and event.event_type == EventType.PURCHASE:
                test.variants[user_variant]['conversions'] += 1
                if 'order_value' in event.properties:
                    test.variants[user_variant]['total_revenue'] += event.properties['order_value']
    
    def _assign_user_to_variant(self, user_id: str, test: ABTestResult) -> Optional[str]:
        """Assign user to A/B test variant based on allocation"""
        import random
        
        # Use user_id hash for consistent assignment
        hash_value = hash(user_id + test.test_id) % 100 / 100.0
        
        cumulative_allocation = 0.0
        for variant_name, variant_data in test.variants.items():
            cumulative_allocation += variant_data['allocation']
            if hash_value <= cumulative_allocation:
                return variant_name
        
        return None
    
    async def _initialize_predictive_models(self) -> None:
        """Initialize ML models for predictions"""
        try:
            # These would be trained with historical data
            # For now, create placeholder models
            self.predictive_models = {
                'conversion_model': LogisticRegression(),
                'churn_model': RandomForestClassifier(n_estimators=100)
            }
            
            logger.info("Predictive models initialized")
            
        except Exception as e:
            logger.error("Error initializing predictive models", error=str(e))
    
    async def _load_user_segments(self) -> None:
        """Load user segments from storage"""
        # Implementation would load from database
        pass
    
    async def _load_ab_tests(self) -> None:
        """Load active A/B tests from storage"""
        # Implementation would load from database
        pass
    
    async def _load_conversion_funnels(self) -> None:
        """Load conversion funnels from storage"""
        # Implementation would load from database
        pass
    
    async def _process_events_continuously(self) -> None:
        """Background task to process events"""
        while True:
            try:
                await asyncio.sleep(60)  # Process every minute
                # Batch process events, update aggregations, etc.
                logger.debug("Processing events batch")
            except Exception as e:
                logger.error("Error in continuous event processing", error=str(e))
    
    async def _update_real_time_metrics(self) -> None:
        """Background task to update real-time metrics"""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Clean old metrics (keep only last hour)
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                old_keys = [k for k in self.real_time_metrics.keys() if k < cutoff_time]
                for key in old_keys:
                    del self.real_time_metrics[key]
                
            except Exception as e:
                logger.error("Error updating real-time metrics", error=str(e))
                await asyncio.sleep(60)
    
    async def _process_user_segmentation(self) -> None:
        """Background task to update user segmentation"""
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                await self.create_user_segments()
            except Exception as e:
                logger.error("Error in user segmentation processing", error=str(e))
                await asyncio.sleep(3600)
    
    async def _update_conversion_funnels(self, event: AnalyticsEvent) -> None:
        """Update conversion funnel metrics"""
        # Implementation for funnel tracking
        pass


# Global instance
advanced_analytics_engine = RealTimeAnalyticsEngine()
