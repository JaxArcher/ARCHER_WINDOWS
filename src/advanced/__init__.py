"""
Advanced Features Module for ARCHER

Plug-in architecture for experimental and advanced capabilities including:
- Visual Question Answering (VQA)
- Screen Content Understanding
- Document Extraction
- Predictive Assistance
- Personal Analytics
- Life Logging
- Voice Biomarkers
- Privacy Modes

Each feature is implemented as a separate plug-in that can be enabled/disabled.
"""

from .advanced_features import AdvancedFeatures
from .plugins.visual_qa import VisualQAFeature
from .plugins.screen_understanding import ScreenUnderstandingFeature
from .plugins.document_extraction import DocumentExtractionFeature
from .plugins.predictive_assistance import PredictiveAssistanceFeature
from .plugins.analytics_dashboard import AnalyticsDashboardFeature
from .plugins.life_logging import LifeLoggingFeature
from .plugins.voice_biomarkers import VoiceBiomarkersFeature
from .plugins.privacy_modes import PrivacyModesFeature

__all__ = [
    'AdvancedFeatures',
    'VisualQAFeature',
    'ScreenUnderstandingFeature',
    'DocumentExtractionFeature',
    'PredictiveAssistanceFeature',
    'AnalyticsDashboardFeature',
    'LifeLoggingFeature',
    'VoiceBiomarkersFeature',
    'PrivacyModesFeature'
]