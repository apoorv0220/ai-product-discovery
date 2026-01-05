"""
Session Tracker
Tracks and manages user sessions for analytics
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.models.analytics import SessionAnalytics
from shared.database.base import AsyncSessionLocal

logger = structlog.get_logger()


class SessionTracker:
    """Tracks user sessions for analytics"""
    
    # Session timeout: 30 minutes of inactivity
    SESSION_TIMEOUT_MINUTES = 30
    
    def __init__(self):
        pass
    
    async def get_or_create_session(
        self,
        merchant_id: int,
        session_id: Optional[str] = None,
        user_id: Optional[Union[str, int]] = None,
        device_type: Optional[str] = None,
        platform: Optional[str] = None,
        entry_page: Optional[str] = None,
        db_session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get or create session analytics record

        Args:
            merchant_id: Merchant ID
            session_id: Optional session identifier (can be None for user-only tracking)
            user_id: Optional user ID (string or int)
            device_type: Optional device type
            platform: Optional platform
            entry_page: Optional entry page URL
            db_session: Optional database session

        Returns:
            Session data dictionary
        """
        use_external_session = db_session is not None
        if not db_session:
            db_session = AsyncSessionLocal()

        try:
            # For user-only tracking (no session_id), create a virtual session
            if not session_id and user_id:
                session_id = f"user_session_{str(user_id)}_{datetime.utcnow().strftime('%Y%m%d')}"

            if not session_id:
                # Cannot create session without any identifier
                return {
                    'session_id': None,
                    'start_time': datetime.utcnow(),
                    'page_views': 0,
                    'product_views': 0,
                    'searches': 0,
                    'add_to_carts': 0,
                    'purchases': 0,
                    'revenue': 0.0,
                    'bounce': True
                }

            # Try to find existing session
            result = await db_session.execute(
                select(SessionAnalytics).where(
                    and_(
                        SessionAnalytics.merchant_id == merchant_id,
                        SessionAnalytics.session_id == session_id
                    )
                )
            )
            session = result.scalar_one_or_none()

            if session:
                # Check if session has timed out
                timeout_threshold = datetime.utcnow() - timedelta(minutes=self.SESSION_TIMEOUT_MINUTES)
                if session.updated_at < timeout_threshold:
                    # Session timed out, create new session
                    await db_session.delete(session)
                    await db_session.commit()
                    session = None

            if not session:
                # Create new session
                session = SessionAnalytics(
                    merchant_id=merchant_id,
                    session_id=session_id,
                    user_id=None,  # We'll resolve this later if needed
                    start_time=datetime.utcnow(),
                    page_views=0,
                    product_views=0,
                    searches=0,
                    add_to_carts=0,
                    purchases=0,
                    revenue=0.0,
                    entry_page=entry_page,
                    device_type=device_type,
                    platform=platform,
                    bounce='true',
                    journey=[]
                )
                db_session.add(session)
                await db_session.commit()
                await db_session.refresh(session)
            
            return {
                'session_id': session.session_id,
                'start_time': session.start_time,
                'page_views': session.page_views,
                'product_views': session.product_views,
                'searches': session.searches,
                'add_to_carts': session.add_to_carts,
                'purchases': session.purchases,
                'revenue': session.revenue,
                'bounce': session.bounce == 'true'
            }
            
        except Exception as e:
            logger.error("Error getting/creating session", error=str(e))
            # Return minimal session data on error
            return {
                'session_id': session_id,
                'start_time': datetime.utcnow(),
                'page_views': 0,
                'product_views': 0,
                'searches': 0,
                'add_to_carts': 0,
                'purchases': 0,
                'revenue': 0.0,
                'bounce': True
            }
        finally:
            if not use_external_session:
                await db_session.close()
    
    async def update_session(
        self,
        merchant_id: int,
        session_id: Optional[str],
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        db_session: Optional[AsyncSession] = None
    ) -> bool:
        """
        Update session with new event

        Args:
            merchant_id: Merchant ID
            session_id: Optional session identifier
            event_type: Event type
            event_data: Optional event data
            db_session: Optional database session

        Returns:
            True if session was updated successfully
        """
        use_external_session = db_session is not None
        if not db_session:
            db_session = AsyncSessionLocal()

        try:
            # For user-only tracking, generate session_id from user_id
            if not session_id and event_data and event_data.get('user_id'):
                session_id = f"user_session_{str(event_data['user_id'])}_{datetime.utcnow().strftime('%Y%m%d')}"

            if not session_id:
                # Cannot update session without session_id
                return False

            result = await db_session.execute(
                select(SessionAnalytics).where(
                    and_(
                        SessionAnalytics.merchant_id == merchant_id,
                        SessionAnalytics.session_id == session_id
                    )
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                # Session doesn't exist, create it first
                await self.get_or_create_session(
                    merchant_id=merchant_id,
                    session_id=session_id,
                    user_id=event_data.get('user_id') if event_data else None,
                    db_session=db_session
                )

                # Try to get it again
                result = await db_session.execute(
                    select(SessionAnalytics).where(
                        and_(
                            SessionAnalytics.merchant_id == merchant_id,
                            SessionAnalytics.session_id == session_id
                        )
                    )
                )
                session = result.scalar_one_or_none()

                if not session:
                    return False
            
            # Update session metrics based on event type
            if event_type in ['page_view', 'product_view']:
                session.page_views += 1
                if event_type == 'product_view':
                    session.product_views += 1
            elif event_type == 'search':
                session.searches += 1
            elif event_type == 'add_to_cart':
                session.add_to_carts += 1
            elif event_type == 'purchase':
                session.purchases += 1
                if event_data and 'revenue' in event_data:
                    session.revenue += float(event_data['revenue'] or 0)
            
            # Mark as not bounced if we have multiple events
            if session.page_views > 1:
                session.bounce = 'false'
            
            # Add to journey
            if not session.journey:
                session.journey = []
            
            # Serialize event_data to ensure all datetime objects are converted to strings
            serialized_data = self._serialize_event_data(event_data or {})
            
            journey_entry = {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': serialized_data
            }
            session.journey.append(journey_entry)
            
            # Update duration
            if session.start_time:
                session.duration = (datetime.utcnow() - session.start_time).total_seconds()
            
            session.updated_at = datetime.utcnow()
            
            await db_session.commit()
            return True
            
        except Exception as e:
            logger.error("Error updating session", error=str(e))
            await db_session.rollback()
            return False
        finally:
            if not use_external_session:
                await db_session.close()
    
    async def end_session(
        self,
        merchant_id: int,
        session_id: Optional[str] = None,
        user_id: Optional[Union[str, int]] = None,
        exit_page: Optional[str] = None,
        db_session: Optional[AsyncSession] = None
    ) -> bool:
        """
        End a session

        Args:
            merchant_id: Merchant ID
            session_id: Optional session identifier
            user_id: Optional user ID (for user-only tracking)
            exit_page: Optional exit page URL
            db_session: Optional database session

        Returns:
            True if session was ended successfully
        """
        use_external_session = db_session is not None
        if not db_session:
            db_session = AsyncSessionLocal()

        try:
            # For user-only tracking, generate session_id from user_id
            if not session_id and user_id:
                session_id = f"user_session_{str(user_id)}_{datetime.utcnow().strftime('%Y%m%d')}"

            if not session_id:
                return False

            result = await db_session.execute(
                select(SessionAnalytics).where(
                    and_(
                        SessionAnalytics.merchant_id == merchant_id,
                        SessionAnalytics.session_id == session_id
                    )
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                return False
            
            session.end_time = datetime.utcnow()
            if exit_page:
                session.exit_page = exit_page
            
            # Calculate final duration
            if session.start_time:
                session.duration = (session.end_time - session.start_time).total_seconds()
            
            session.updated_at = datetime.utcnow()
            
            await db_session.commit()
            return True
            
        except Exception as e:
            logger.error("Error ending session", error=str(e))
            await db_session.rollback()
            return False
        finally:
            if not use_external_session:
                await db_session.close()


    def _serialize_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize event data to ensure JSON compatibility"""
        if not data:
            return {}
        
        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_event_data(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_event_data(item) if isinstance(item, dict)
                    else item.isoformat() if isinstance(item, datetime)
                    else item
                    for item in value
                ]
            else:
                serialized[key] = value
        
        return serialized


# Global session tracker instance
session_tracker = SessionTracker()

