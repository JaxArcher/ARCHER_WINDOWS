"""
Advanced Features Main Class

Central coordinator for all advanced and experimental features.
Implements plug-in architecture and orchestrator integration.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class AdvancedFeatures:
    """
    Main class for advanced features with plug-in architecture.
    """
    
    def __init__(self):
        """Initialize advanced features system."""
        self.plugins: Dict[str, Any] = {}
        self.enabled_features: Dict[str, bool] = {}
        self.memory = None
        
        # Initialize memory integration
        self._initialize_memory()
        
        logger.info("AdvancedFeatures system initialized")
    
    def _initialize_memory(self):
        """Initialize memory integration with 4-tier system."""
        try:
            from src.memory.unified_vector_memory import UnifiedVectorMemory
            self.memory = UnifiedVectorMemory(
                collection_name="agent_adv",
                use_pinecone=False  # Use ChromaDB for local processing
            )
            logger.info("Advanced features memory initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize advanced features memory: {e}")
            self.memory = None
    
    def register_plugin(self, name: str, plugin_instance: Any, enabled: bool = True):
        """
        Register a plug-in with the advanced features system.
        
        Args:
            name: Unique name for the plug-in
            plugin_instance: The plug-in instance
            enabled: Whether the plug-in is enabled by default
        """
        if not name or not isinstance(name, str):
            raise ValueError("Plugin name must be a non-empty string")
            
        if not plugin_instance:
            raise ValueError("Plugin instance cannot be None")
            
        if name in self.plugins:
            logger.warning(f"Plugin '{name}' already registered, overwriting")
        
        # Register the plug-in
        self.plugins[name] = plugin_instance
        self.enabled_features[name] = enabled
        
        logger.info(f"Plugin '{name}' registered and {'enabled' if enabled else 'disabled'}")
        
        return True
    
    def enable_plugin(self, name: str):
        """Enable a registered plug-in."""
        if name not in self.plugins:
            raise ValueError(f"Plugin '{name}' not found")
        
        self.enabled_features[name] = True
        logger.info(f"Plugin '{name}' enabled")
    
    def disable_plugin(self, name: str):
        """Disable a registered plug-in."""
        if name not in self.plugins:
            raise ValueError(f"Plugin '{name}' not found")
        
        self.enabled_features[name] = False
        logger.info(f"Plugin '{name}' disabled")
    
    def execute_plugin(self, name: str, *args, **kwargs) -> Any:
        """
        Execute a plug-in if it's enabled.
        
        Args:
            name: Name of the plug-in to execute
            *args: Positional arguments for the plug-in
            **kwargs: Keyword arguments for the plug-in
            
        Returns:
            Result from plug-in execution or error if disabled/not found
        """
        if name not in self.plugins:
            return {"error": f"Plugin '{name}' not found"}
            
        if not self.enabled_features.get(name, False):
            return {"error": f"Plugin '{name}' is disabled"}
            
        try:
            plugin = self.plugins[name]
            if hasattr(plugin, 'execute'):
                result = plugin.execute(*args, **kwargs)
            else:
                # Try to call the plugin directly
                result = plugin(*args, **kwargs)
            
            return result
        except Exception as e:
            logger.error(f"Error executing plugin '{name}': {e}")
            return {"error": f"Plugin execution failed: {str(e)}"}
    
    def get_registered_plugins(self) -> List[str]:
        """Get list of registered plug-ins."""
        return list(self.plugins.keys())
    
    def get_plugin_status(self, name: str) -> Dict[str, Any]:
        """Get status information about a plug-in."""
        if name not in self.plugins:
            return {"error": f"Plugin '{name}' not found"}
        
        return {
            "name": name,
            "enabled": self.enabled_features.get(name, False),
            "has_execute": hasattr(self.plugins[name], 'execute')
        }
    
    def register_with_orchestrator(self, orchestrator):
        """
        Register all enabled plug-ins with the main orchestrator.
        
        Args:
            orchestrator: The main orchestrator instance
        """
        if not orchestrator:
            raise ValueError("Orchestrator cannot be None")
        
        for plugin_name, plugin_instance in self.plugins.items():
            if self.enabled_features.get(plugin_name, False):
                try:
                    # Register with orchestrator
                    orchestrator.register_agent(
                        name=f"adv_{plugin_name}",
                        agent_instance=plugin_instance,
                        metadata={
                            "type": "advanced_feature",
                            "feature_name": plugin_name,
                            "enabled": True
                        }
                    )
                    logger.info(f"Registered plugin '{plugin_name}' with orchestrator")
                except Exception as e:
                    logger.error(f"Failed to register plugin '{plugin_name}' with orchestrator: {e}")
    
    def __repr__(self) -> str:
        """String representation of the advanced features system."""
        enabled_count = sum(1 for status in self.enabled_features.values() if status)
        return f"AdvancedFeatures(plugins={len(self.plugins)}, enabled={enabled_count})"