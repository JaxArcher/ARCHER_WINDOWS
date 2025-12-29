"""
Privacy Manager for ARCHER Vision System

Manages user consent and feature access control for vision-based features.
Ensures compliance with privacy requirements and user preferences.
"""

import logging
from typing import List, Dict, Optional
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class PrivacyManager:
    """
    Privacy Manager for vision system features.
    
    Features:
    - User consent management
    - Feature-level access control
    - Privacy preference persistence
    - Audit logging
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize Privacy Manager."""
        if config_file is None:
            config_file = Path("config/vision_privacy.json")
            
        self.config_file = config_file
        self.consent_given = False
        self.disabled_features: List[str] = []
        self.privacy_preferences: Dict[str, Any] = {}
        
        # Load saved preferences
        self._load_preferences()
        
        logger.info("Privacy Manager initialized")
        
    def _load_preferences(self):
        """Load privacy preferences from disk."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    preferences = json.load(f)
                    self.consent_given = preferences.get("consent_given", False)
                    self.disabled_features = preferences.get("disabled_features", [])
                    self.privacy_preferences = preferences.get("preferences", {})
                    
                logger.info(f"Loaded privacy preferences: consent={self.consent_given}, disabled={len(self.disabled_features)} features")
            else:
                logger.info("No existing privacy preferences found, using defaults")
                
        except Exception as e:
            logger.error(f"Failed to load privacy preferences: {e}")
            # Use defaults on error
            self.consent_given = False
            self.disabled_features = []
            self.privacy_preferences = {}
    
    def _save_preferences(self):
        """Save privacy preferences to disk."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            preferences = {
                "consent_given": self.consent_given,
                "disabled_features": self.disabled_features,
                "preferences": self.privacy_preferences
            }
            
            with open(self.config_file, "w") as f:
                json.dump(preferences, f, indent=2)
                
            logger.debug("Privacy preferences saved")
            
        except Exception as e:
            logger.error(f"Failed to save privacy preferences: {e}")
    
    def set_consent(self, consent: bool):
        """Set user consent for vision features."""
        self.consent_given = consent
        self._save_preferences()
        
        event_type = "vision.consent.granted" if consent else "vision.consent.revoked"
        logger.info(f"User consent {'granted' if consent else 'revoked'} for vision features")
        
        # Publish consent change event
        try:
            from src.events.bus import bus
            bus.publish(event_type, {"consent": consent})
        except ImportError:
            logger.warning("Event bus not available, cannot publish consent event")
    
    def is_vision_allowed(self, feature: str) -> bool:
        """
        Check if a specific vision feature is allowed.
        
        Args:
            feature: Feature name (e.g., 'face_recognition', 'gesture_detection')
            
        Returns:
            True if feature is allowed, False otherwise
        """
        if not self.consent_given:
            logger.debug(f"Feature '{feature}' blocked: no consent")
            return False
            
        if feature in self.disabled_features:
            logger.debug(f"Feature '{feature}' blocked: disabled by user")
            return False
            
        logger.debug(f"Feature '{feature}' allowed")
        return True
    
    def disable_feature(self, feature: str):
        """Disable a specific vision feature."""
        if feature not in self.disabled_features:
            self.disabled_features.append(feature)
            self._save_preferences()
            logger.info(f"Disabled vision feature: {feature}")
            
            # Publish feature disabled event
            try:
                from src.events.bus import bus
                bus.publish("vision.feature.disabled", {"feature": feature})
            except ImportError:
                pass
    
    def enable_feature(self, feature: str):
        """Enable a previously disabled vision feature."""
        if feature in self.disabled_features:
            self.disabled_features.remove(feature)
            self._save_preferences()
            logger.info(f"Enabled vision feature: {feature}")
            
            # Publish feature enabled event
            try:
                from src.events.bus import bus
                bus.publish("vision.feature.enabled", {"feature": feature})
            except ImportError:
                pass
    
    def get_disabled_features(self) -> List[str]:
        """Get list of disabled features."""
        return self.disabled_features.copy()
    
    def get_consent_status(self) -> bool:
        """Get current consent status."""
        return self.consent_given
    
    def set_preference(self, key: str, value: Any):
        """Set a privacy preference."""
        self.privacy_preferences[key] = value
        self._save_preferences()
        logger.debug(f"Set privacy preference: {key} = {value}")
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a privacy preference."""
        return self.privacy_preferences.get(key, default)
    
    def reset_to_defaults(self):
        """Reset all privacy settings to defaults."""
        self.consent_given = False
        self.disabled_features = []
        self.privacy_preferences = {}
        self._save_preferences()
        logger.info("Privacy settings reset to defaults")
        
        # Publish reset event
        try:
            from src.events.bus import bus
            bus.publish("vision.privacy.reset", {})
        except ImportError:
            pass
    
    def get_privacy_summary(self) -> Dict[str, Any]:
        """Get summary of privacy settings."""
        return {
            "consent_given": self.consent_given,
            "disabled_features": self.disabled_features.copy(),
            "preferences": self.privacy_preferences.copy(),
            "config_file": str(self.config_file)
        }


# Global instance for easy access
privacy_manager = PrivacyManager()