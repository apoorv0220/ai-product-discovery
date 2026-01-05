"""
AI Product Discovery Suite - Analytics Service Schemas

@category    Backend
@package     Analytics Service
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from .events import EventRequest, EventResponse, EventData
from .dashboard import DashboardRequest, DashboardResponse, DashboardData
from .reports import ReportRequest, ReportResponse, ReportData
from .tracking import ProductViewRequest, SearchQueryRequest, SearchClickRequest, TrackingResponse

__all__ = [
    'EventRequest', 'EventResponse', 'EventData',
    'DashboardRequest', 'DashboardResponse', 'DashboardData',
    'ReportRequest', 'ReportResponse', 'ReportData',
    'ProductViewRequest', 'SearchQueryRequest', 'SearchClickRequest', 'TrackingResponse'
]