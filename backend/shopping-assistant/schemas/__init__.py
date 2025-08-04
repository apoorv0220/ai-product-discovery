"""
AI Product Discovery Suite - Shopping Assistant Schemas

@category    Backend
@package     Shopping Assistant
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from .chat import ChatRequest, ChatResponse, ChatMessage
from .sessions import SessionRequest, SessionResponse, SessionData

__all__ = [
    'ChatRequest', 'ChatResponse', 'ChatMessage',
    'SessionRequest', 'SessionResponse', 'SessionData'
]