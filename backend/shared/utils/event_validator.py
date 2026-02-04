"""
Event Validator Utility
Validates, sanitizes, and deduplicates analytics events
"""

import re
import html
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from shared.schemas.analytics import (
    AnalyticsEventSchema,
    EventValidationResult,
    EventDeduplicationKey,
    EventType,
)

logger = structlog.get_logger()


class EventValidator:
    """Event validation and sanitization"""
    
    # IP address regex patterns
    IPV4_PATTERN = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    IPV6_PATTERN = re.compile(
        r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$'
    )
    
    # User ID patterns (allow integers and string UUIDs)
    USER_ID_PATTERN = re.compile(r'^[0-9a-zA-Z\-_]+$')
    
    # URL pattern for referrer validation
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    def __init__(self):
        self.max_property_size = 10000  # 10KB
        self.max_string_length = 500
    
    def validate_event(self, event_data: Dict[str, Any]) -> EventValidationResult:
        """
        Validate an analytics event
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            EventValidationResult with validation status and errors
        """
        errors: List[str] = []
        
        try:
            # Validate using Pydantic schema
            event = AnalyticsEventSchema(**event_data)
            
            # Additional custom validations
            additional_errors = self._custom_validation(event)
            errors.extend(additional_errors)
            
            if errors:
                return EventValidationResult(
                    is_valid=False,
                    errors=errors,
                    sanitized_event=None
                )
            
            # Sanitize the event
            sanitized_event = self.sanitize_event(event)
            
            return EventValidationResult(
                is_valid=True,
                errors=[],
                sanitized_event=sanitized_event
            )
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.warning("Event validation failed", error=error_msg, event_data=event_data)
            return EventValidationResult(
                is_valid=False,
                errors=[error_msg],
                sanitized_event=None
            )
    
    def _custom_validation(self, event: AnalyticsEventSchema) -> List[str]:
        """Perform additional custom validations"""
        errors: List[str] = []
        
        # Validate IP address format if provided
        if event.ip_address:
            if not self._is_valid_ip(event.ip_address):
                errors.append(f"Invalid IP address format: {event.ip_address}")
        
        # Validate referrer URL format if provided
        if event.referrer:
            if not self._is_valid_url(event.referrer):
                errors.append(f"Invalid referrer URL format: {event.referrer}")
        
        # Validate user_id format if provided
        if event.user_id:
            if isinstance(event.user_id, int):
                if event.user_id < 1:
                    errors.append(f"Invalid user_id: must be positive integer")
            elif isinstance(event.user_id, str):
                # Validate string user_id format
                if not self.USER_ID_PATTERN.match(event.user_id):
                    errors.append(f"Invalid user_id format: must contain only alphanumeric characters, hyphens, and underscores")
                if len(event.user_id) > 255:
                    errors.append(f"Invalid user_id: cannot exceed 255 characters")
            else:
                errors.append(f"Invalid user_id type: must be string or integer")
        
        # Validate merchant_id
        if event.merchant_id < 1:
            errors.append(f"Invalid merchant_id: must be positive integer")
        
        # Validate revenue for purchase events
        if event.event_type == EventType.PURCHASE:
            if event.revenue is not None and event.revenue < 0:
                errors.append("Revenue cannot be negative for purchase events")
        
        # Validate properties size
        if event.properties:
            properties_str = str(event.properties)
            if len(properties_str) > self.max_property_size:
                errors.append(f"Properties size exceeds maximum of {self.max_property_size} bytes")
        
        return errors
    
    def sanitize_event(self, event: AnalyticsEventSchema) -> AnalyticsEventSchema:
        """
        Sanitize event data to prevent XSS and data injection
        
        Args:
            event: AnalyticsEventSchema to sanitize
            
        Returns:
            Sanitized AnalyticsEventSchema
        """
        event_dict = event.dict()
        
        # Sanitize string fields
        # Note: session_id is not HTML-escaped here to maintain correlation with external systems,
        # but it is still stripped of null bytes and control characters.
        string_fields = ['platform', 'device_type', 'user_agent', 'referrer']
        for field in string_fields:
            if event_dict.get(field):
                event_dict[field] = self._sanitize_string(event_dict[field])
        
        if event_dict.get('session_id'):
            # Basic technical sanitization for session_id without HTML escaping
            val = str(event_dict['session_id'])
            val = val.replace('\x00', '')
            val = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', val)
            event_dict['session_id'] = val.strip()
        
        # Sanitize properties (recursively sanitize string values)
        if event_dict.get('properties'):
            event_dict['properties'] = self._sanitize_dict(event_dict['properties'])
        
        # Truncate strings that exceed maximum length
        if event_dict.get('user_agent') and len(event_dict['user_agent']) > self.max_string_length:
            event_dict['user_agent'] = event_dict['user_agent'][:self.max_string_length]
        
        if event_dict.get('referrer') and len(event_dict['referrer']) > self.max_string_length:
            event_dict['referrer'] = event_dict['referrer'][:self.max_string_length]
        
        # Create sanitized event
        return AnalyticsEventSchema(**event_dict)
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize a string value to prevent XSS"""
        if not value:
            return value
        
        # HTML escape to prevent XSS
        sanitized = html.escape(value)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Remove control characters (except newline, tab, carriage return)
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        return sanitized.strip()
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values"""
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            sanitized_key = self._sanitize_string(str(key)) if isinstance(key, str) else key
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[sanitized_key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[sanitized_key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[sanitized_key] = [
                    self._sanitize_string(item) if isinstance(item, str)
                    else self._sanitize_dict(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[sanitized_key] = value
        
        return sanitized
    
    def _is_valid_ip(self, ip_address: str) -> bool:
        """Validate IP address format (IPv4 or IPv6)"""
        if not ip_address:
            return False
        
        # Check IPv4
        if self.IPV4_PATTERN.match(ip_address):
            return True
        
        # Check IPv6 (simplified check)
        if ':' in ip_address:
            # Basic IPv6 validation
            parts = ip_address.split(':')
            if len(parts) <= 8:
                return True
        
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        if not url:
            return False
        
        # Basic URL validation
        return bool(self.URL_PATTERN.match(url))
    
    def create_deduplication_key(
        self,
        event_id: str,
        merchant_id: int,
        session_id: str,
        timestamp: datetime,
        event_type: EventType
    ) -> EventDeduplicationKey:
        """Create deduplication key for event"""
        return EventDeduplicationKey(
            event_id=event_id,
            merchant_id=merchant_id,
            session_id=session_id,
            timestamp=timestamp,
            event_type=event_type
        )


# Global validator instance
event_validator = EventValidator()

