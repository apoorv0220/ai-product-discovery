"""
Models package for AI Product Discovery Suite
Contains database models for various services
"""

from .user_interactions import (
    Base,
    UserSearchHistory,
    UserProductViews,
    UserSearchClicks,
    PersonalizedSearchWeights
)

__all__ = [
    'Base',
    'UserSearchHistory',
    'UserProductViews',
    'UserSearchClicks',
    'PersonalizedSearchWeights'
]
