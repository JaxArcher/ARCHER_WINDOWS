"""
Advanced Features Plugins Package

Contains all plug-in implementations for advanced capabilities.
"""

from .visual_qa import VisualQAFeature
from .screen_understanding import ScreenUnderstandingFeature
from .document_extraction import DocumentExtractionFeature
from .predictive_assistance import PredictiveAssistanceFeature
from .analytics_dashboard import AnalyticsDashboardFeature
from .life_logging import LifeLoggingFeature
from .voice_biomarkers import VoiceBiomarkersFeature
from .privacy_modes import PrivacyModesFeature

__all__ = [
    'VisualQAFeature',
    'ScreenUnderstandingFeature',
    'DocumentExtractionFeature',
    'PredictiveAssistanceFeature',
    'AnalyticsDashboardFeature',
    'LifeLoggingFeature',
    'VoiceBiomarkersFeature',
    'PrivacyModesFeature'
]