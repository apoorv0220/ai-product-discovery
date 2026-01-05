"""
AI Product Discovery Suite - Export Service

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import csv
import json
import io
from typing import Dict, Any, List, Optional, Iterator, AsyncIterator
from datetime import datetime
from fastapi.responses import StreamingResponse
import structlog

from core.dashboard_queries import DashboardQueryService
from core.report_generator import ReportGenerator
from shared.database.base import AsyncSessionLocal
from shared.models.analytics import AnalyticsEvent
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class ExportService:
    """Service for exporting analytics data to CSV and JSON formats"""
    
    def __init__(self):
        self.query_service = DashboardQueryService()
        self.report_generator = ReportGenerator()
    
    def _build_date_filter(self, merchant_id: int, date_from: Optional[datetime], date_to: Optional[datetime]):
        """Build date range filter conditions"""
        conditions = [AnalyticsEvent.merchant_id == merchant_id]

        if date_from:
            # Convert timezone-aware datetime to naive datetime for database compatibility
            naive_date_from = date_from.replace(tzinfo=None) if date_from.tzinfo else date_from
            conditions.append(AnalyticsEvent.timestamp >= naive_date_from)
        if date_to:
            # Convert timezone-aware datetime to naive datetime for database compatibility
            naive_date_to = date_to.replace(tzinfo=None) if date_to.tzinfo else date_to
            conditions.append(AnalyticsEvent.timestamp <= naive_date_to)

        return and_(*conditions)
    
    async def export_events_csv(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Export events to CSV format with streaming support
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            event_types: Filter by event types (optional)
            limit: Maximum number of events to export (optional)
            
        Yields:
            CSV rows as strings
        """
        session = AsyncSessionLocal()
        
        try:
            # Build query
            date_filter = self._build_date_filter(merchant_id, date_from, date_to)
            
            query = select(AnalyticsEvent).where(date_filter)
            
            if event_types:
                query = query.where(AnalyticsEvent.event_type.in_(event_types))
            
            query = query.order_by(AnalyticsEvent.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
            
            # CSV header
            header = [
                'event_id', 'merchant_id', 'event_type', 'user_id', 'session_id',
                'product_id', 'platform', 'device_type', 'revenue', 'timestamp'
            ]
            yield ','.join(header) + '\n'
            
            # Stream results in chunks
            result = await session.stream_scalars(query)
            
            # Stream rows
            async for event in result:
                row = [
                    str(event.event_id),
                    str(event.merchant_id),
                    event.event_type or '',
                    event.user_id or '',
                    event.session_id or '',
                    str(event.product_id) if event.product_id else '',
                    event.platform or '',
                    event.device_type or '',
                    str(event.revenue) if event.revenue else '0.0',
                    event.timestamp.isoformat() if event.timestamp else ''
                ]
                # Escape CSV values
                escaped_row = [f'"{str(val).replace(chr(34), chr(34)+chr(34))}"' for val in row]
                yield ','.join(escaped_row) + '\n'
                
        except Exception as e:
            logger.error("Error exporting events to CSV", error=str(e), exc_info=True)
            raise
        finally:
            await session.close()
    
    async def export_events_json(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
        streaming: bool = True
    ) -> AsyncIterator[str]:
        """
        Export events to JSON format (JSONL for streaming, pretty JSON for small datasets)
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            event_types: Filter by event types (optional)
            limit: Maximum number of events to export (optional)
            streaming: Use JSONL format for streaming (default: True)
            
        Yields:
            JSON rows as strings
        """
        session = AsyncSessionLocal()
        
        try:
            # Build query
            date_filter = self._build_date_filter(merchant_id, date_from, date_to)
            
            query = select(AnalyticsEvent).where(date_filter)
            
            if event_types:
                query = query.where(AnalyticsEvent.event_type.in_(event_types))
            
            query = query.order_by(AnalyticsEvent.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
            
            # Stream results
            result = await session.stream_scalars(query)
            
            if streaming:
                # JSONL format (one JSON object per line)
                async for event in result:
                    event_dict = {
                        'event_id': str(event.event_id),
                        'merchant_id': event.merchant_id,
                        'event_type': event.event_type,
                        'user_id': event.user_id,
                        'session_id': event.session_id,
                        'product_id': event.product_id,
                        'platform': event.platform,
                        'device_type': event.device_type,
                        'revenue': float(event.revenue) if event.revenue else 0.0,
                        'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                        'properties': event.properties if event.properties else {}
                    }
                    yield json.dumps(event_dict) + '\n'
            else:
                # Pretty JSON format (array of objects)
                events = []
                async for event in result:
                    event_dict = {
                        'event_id': str(event.event_id),
                        'merchant_id': event.merchant_id,
                        'event_type': event.event_type,
                        'user_id': event.user_id,
                        'session_id': event.session_id,
                        'product_id': event.product_id,
                        'platform': event.platform,
                        'device_type': event.device_type,
                        'revenue': float(event.revenue) if event.revenue else 0.0,
                        'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                        'properties': event.properties if event.properties else {}
                    }
                    events.append(event_dict)
                
                yield json.dumps(events, indent=2)
                
        except Exception as e:
            logger.error("Error exporting events to JSON", error=str(e), exc_info=True)
            raise
        finally:
            await session.close()
    
    async def export_time_series_csv(
        self,
        merchant_id: int,
        metric_name: str,
        period: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> AsyncIterator[str]:
        """
        Export time-series data to CSV format
        
        Args:
            merchant_id: Merchant ID
            metric_name: Name of the metric
            period: Time period (hourly, daily, weekly, monthly)
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Yields:
            CSV rows as strings
        """
        try:
            # Get time-series data
            data_points = await self.query_service.get_time_series_data(
                merchant_id,
                metric_name=metric_name,
                period=period,
                date_from=date_from,
                date_to=date_to
            )
            
            # CSV header
            yield f'timestamp,{metric_name}\n'
            
            # Stream rows
            for point in data_points:
                timestamp = point['timestamp'].isoformat() if isinstance(point['timestamp'], datetime) else str(point['timestamp'])
                value = str(point['value'])
                yield f'{timestamp},{value}\n'
                
        except Exception as e:
            logger.error("Error exporting time-series to CSV", error=str(e), exc_info=True)
            raise
    
    async def export_time_series_json(
        self,
        merchant_id: int,
        metric_name: str,
        period: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> str:
        """
        Export time-series data to JSON format
        
        Args:
            merchant_id: Merchant ID
            metric_name: Name of the metric
            period: Time period (hourly, daily, weekly, monthly)
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            JSON string
        """
        try:
            # Get time-series data
            data_points = await self.query_service.get_time_series_data(
                merchant_id,
                metric_name=metric_name,
                period=period,
                date_from=date_from,
                date_to=date_to
            )
            
            # Format data points
            formatted_points = [
                {
                    'timestamp': point['timestamp'].isoformat() if isinstance(point['timestamp'], datetime) else str(point['timestamp']),
                    'value': point['value']
                }
                for point in data_points
            ]
            
            return json.dumps({
                'metric_name': metric_name,
                'period': period,
                'data_points': formatted_points
            }, indent=2)
            
        except Exception as e:
            logger.error("Error exporting time-series to JSON", error=str(e), exc_info=True)
            raise
    
    async def export_report_csv(
        self,
        merchant_id: int,
        report_type: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> AsyncIterator[str]:
        """
        Export report data to CSV format
        
        Args:
            merchant_id: Merchant ID
            report_type: Type of report (performance, user_behavior)
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Yields:
            CSV rows as strings
        """
        try:
            if report_type == 'performance':
                report = await self.report_generator.generate_performance_report(
                    merchant_id,
                    date_from=date_from,
                    date_to=date_to
                )
            elif report_type == 'user_behavior':
                report = await self.report_generator.generate_user_behavior_report(
                    merchant_id,
                    date_from=date_from,
                    date_to=date_to
                )
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            # Convert report to CSV format
            # This is a simplified version - can be enhanced with proper CSV formatting
            yield f'report_type,{report_type}\n'
            yield f'period_start,{report.get("period", {}).get("start", "")}\n'
            yield f'period_end,{report.get("period", {}).get("end", "")}\n'
            yield f'generated_at,{report.get("generated_at", "")}\n'
            
            # Export main data sections
            for section, data in report.items():
                if section not in ['report_type', 'period', 'generated_at', 'merchant_id']:
                    yield f'\n[{section}]\n'
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (dict, list)):
                                value = json.dumps(value)
                            yield f'{key},{value}\n'
                    else:
                        yield f'value,{data}\n'
                        
        except Exception as e:
            logger.error("Error exporting report to CSV", error=str(e), exc_info=True)
            raise
    
    async def export_report_json(
        self,
        merchant_id: int,
        report_type: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> str:
        """
        Export report data to JSON format
        
        Args:
            merchant_id: Merchant ID
            report_type: Type of report (performance, user_behavior)
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            JSON string
        """
        try:
            if report_type == 'performance':
                report = await self.report_generator.generate_performance_report(
                    merchant_id,
                    date_from=date_from,
                    date_to=date_to
                )
            elif report_type == 'user_behavior':
                report = await self.report_generator.generate_user_behavior_report(
                    merchant_id,
                    date_from=date_from,
                    date_to=date_to
                )
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            return json.dumps(report, indent=2, default=str)
            
        except Exception as e:
            logger.error("Error exporting report to JSON", error=str(e), exc_info=True)
            raise

