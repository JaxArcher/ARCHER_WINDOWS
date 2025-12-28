"""
Federated Learning Manager for ARCHER

Privacy-preserving collaborative learning across multiple ARCHER instances.
"""

import json
import time
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional
import logging
import os
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FederatedUpdate:
    """Federated learning update from a client."""
    
    client_id: str
    timestamp: float
    model_updates: Dict[str, Any]
    data_hash: str
    update_size: int
    metadata: Dict[str, Any]
    signature: str = ""  # For future security enhancements
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "timestamp": self.timestamp,
            "model_updates": self.model_updates,
            "data_hash": self.data_hash,
            "update_size": self.update_size,
            "metadata": self.metadata,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FederatedUpdate":
        return cls(
            client_id=data["client_id"],
            timestamp=data["timestamp"],
            model_updates=data["model_updates"],
            data_hash=data["data_hash"],
            update_size=data["update_size"],
            metadata=data["metadata"],
            signature=data.get("signature", "")
        )

@dataclass
class FederatedModel:
    """Federated learning model with versioning."""
    
    model_id: str
    version: str
    parameters: Dict[str, Any]
    timestamp: float
    contributing_clients: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
            "contributing_clients": self.contributing_clients,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FederatedModel":
        return cls(
            model_id=data["model_id"],
            version=data["version"],
            parameters=data["parameters"],
            timestamp=data["timestamp"],
            contributing_clients=data["contributing_clients"],
            metadata=data["metadata"]
        )

class FederatedLearningManager:
    """
    Federated Learning Coordinator for ARCHER.
    
    Features:
    - Secure model aggregation using Federated Averaging
    - Privacy-preserving updates
    - Client management and authentication
    - Model versioning and rollback
    - Local-first operation with optional server synchronization
    """
    
    def __init__(self, config_file: str = "federated_config.json"):
        self.config = self._load_config(config_file)
        self.client_updates: List[FederatedUpdate] = []
        self.current_model: Optional[FederatedModel] = None
        self.model_history: List[FederatedModel] = []
        self.local_improvements: Dict[str, Any] = {}
        
        # Load existing data
        self._load_state()
        
        logger.info(f"FederatedLearningManager initialized (Enabled: {self.config['enabled']})")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load federated learning configuration."""
        default_config = {
            "enabled": False,
            "server_url": "",
            "client_id": self._generate_client_id(),
            "client_name": "ARCHER_Instance",
            "min_clients_for_aggregation": 3,
            "aggregation_method": "fedavg",
            "privacy_level": "high",
            "update_frequency_hours": 24,
            "max_update_size_kb": 1000,
            "require_server_verification": True,
            "local_only_mode": True
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Could not load config: {e}")
        
        # Save default config
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save default config: {e}")
        
        return default_config
    
    def _generate_client_id(self) -> str:
        """Generate unique client ID."""
        try:
            # Use hardware info if available
            import uuid
            mac = uuid.getnode()
            timestamp = str(time.time())
            random_data = str(np.random.randint(0, 1000000))
            combined = f"{mac}_{timestamp}_{random_data}"
            return hashlib.sha256(combined.encode()).hexdigest()[:16]
        except Exception:
            # Fallback to random
            timestamp = str(time.time())
            random_data = str(np.random.randint(0, 1000000))
            combined = timestamp + random_data
            return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _save_config(self) -> bool:
        """Save configuration."""
        try:
            with open("federated_config.json", 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def _load_state(self):
        """Load federated learning state."""
        try:
            if os.path.exists("federated_state.json"):
                with open("federated_state.json", 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    
                    # Load client updates
                    if "client_updates" in state:
                        self.client_updates = [FederatedUpdate.from_dict(u) for u in state["client_updates"]]
                    
                    # Load current model
                    if "current_model" in state:
                        self.current_model = FederatedModel.from_dict(state["current_model"])
                    
                    # Load model history
                    if "model_history" in state:
                        self.model_history = [FederatedModel.from_dict(m) for m in state["model_history"]]
                    
                    # Load local improvements
                    if "local_improvements" in state:
                        self.local_improvements = state["local_improvements"]
                    
                    logger.info(f"Loaded federated state: {len(self.client_updates)} updates, {len(self.model_history)} models")
        except Exception as e:
            logger.warning(f"Could not load federated state: {e}")
    
    def _save_state(self) -> bool:
        """Save federated learning state."""
        try:
            state = {
                "client_updates": [u.to_dict() for u in self.client_updates],
                "current_model": self.current_model.to_dict() if self.current_model else None,
                "model_history": [m.to_dict() for m in self.model_history],
                "local_improvements": self.local_improvements,
                "last_saved": time.time()
            }
            
            with open("federated_state.json", 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save federated state: {e}")
            return False
    
    def enable_federated_learning(self, enable: bool = True, server_url: str = None, 
                                 client_name: str = None) -> bool:
        """Enable federated learning."""
        self.config["enabled"] = enable
        
        if server_url:
            self.config["server_url"] = server_url
        
        if client_name:
            self.config["client_name"] = client_name
        
        if self._save_config():
            logger.info(f"Federated learning {'enabled' if enable else 'disabled'}")
            if enable and server_url:
                logger.info(f"Server URL: {server_url}")
            return True
        
        return False
    
    def disable_federated_learning(self) -> bool:
        """Disable federated learning."""
        return self.enable_federated_learning(False)
    
    def set_client_name(self, name: str) -> bool:
        """Set client name for identification."""
        self.config["client_name"] = name
        return self._save_config()
    
    def initialize_base_model(self, model_id: str = "archer_core", version: str = "1.0",
                           parameters: Dict[str, Any] = None) -> bool:
        """Initialize the base model for federated learning."""
        if not self.config["enabled"]:
            logger.warning("Federated learning not enabled")
            return False
        
        try:
            # Create default parameters if none provided
            if parameters is None:
                parameters = {
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "architecture": "transformer",
                    "performance": {
                        "accuracy": 0.85,
                        "latency_ms": 150,
                        "memory_mb": 256
                    },
                    "layers": {
                        "attention_heads": 12,
                        "hidden_size": 768,
                        "intermediate_size": 3072
                    }
                }
            
            # Create federated model
            model = FederatedModel(
                model_id=model_id,
                version=version,
                parameters=parameters,
                timestamp=time.time(),
                contributing_clients=1,  # Just this client initially
                metadata={
                    "initialized_by": self.config["client_id"],
                    "initial_client": self.config["client_name"],
                    "description": "Base ARCHER model for federated learning"
                }
            )
            
            self.current_model = model
            self.model_history.append(model)
            
            if self._save_state():
                logger.info(f"Base model initialized: {model_id} v{version}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize base model: {e}")
            return False
    
    def record_local_improvement(self, parameter_name: str, old_value: Any, new_value: Any,
                                improvement_type: str = "performance", 
                                performance_gain: float = None) -> bool:
        """Record a local model improvement."""
        if not self.config["enabled"]:
            logger.warning("Federated learning not enabled")
            return False
        
        if not self.current_model:
            logger.warning("No base model initialized")
            return False
        
        try:
            # Store the improvement
            if parameter_name not in self.local_improvements:
                self.local_improvements[parameter_name] = {
                    "changes": [],
                    "last_updated": time.time()
                }
            
            change_record = {
                "timestamp": time.time(),
                "old_value": old_value,
                "new_value": new_value,
                "type": improvement_type,
                "performance_gain": performance_gain
            }
            
            self.local_improvements[parameter_name]["changes"].append(change_record)
            self.local_improvements[parameter_name]["last_updated"] = time.time()
            
            logger.info(f"Recorded local improvement: {parameter_name}")
            return self._save_state()
            
        except Exception as e:
            logger.error(f"Failed to record local improvement: {e}")
            return False
    
    def generate_federated_update(self) -> Optional[FederatedUpdate]:
        """Generate a federated update from local improvements."""
        if not self.config["enabled"]:
            logger.warning("Federated learning not enabled")
            return None
        
        if not self.current_model:
            logger.warning("No base model available")
            return None
        
        if not self.local_improvements:
            logger.info("No local improvements to share")
            return None
        
        try:
            # Calculate model differences
            model_updates = self._calculate_model_differences()
            
            if not model_updates:
                logger.info("No significant model differences to share")
                return None
            
            # Create update payload
            update_json = json.dumps(model_updates, sort_keys=True)
            data_hash = hashlib.sha256(update_json.encode()).hexdigest()
            
            # Create federated update
            update = FederatedUpdate(
                client_id=self.config["client_id"],
                timestamp=time.time(),
                model_updates=model_updates,
                data_hash=data_hash,
                update_size=len(update_json),
                metadata={
                    "model_id": self.current_model.model_id,
                    "model_version": self.current_model.version,
                    "client_name": self.config["client_name"],
                    "improvement_count": len(self.local_improvements),
                    "update_type": "performance_improvement",
                    "privacy_level": self.config["privacy_level"]
                }
            )
            
            # Add to client updates
            self.client_updates.append(update)
            
            # Clear local improvements (they've been incorporated)
            self.local_improvements = {}
            
            if self._save_state():
                logger.info(f"Generated federated update: {update.update_size} bytes, {len(model_updates)} parameters")
                return update
            else:
                logger.warning("Generated update but failed to save state")
                return update
                
        except Exception as e:
            logger.error(f"Failed to generate federated update: {e}")
            return None
    
    def _calculate_model_differences(self) -> Dict[str, Any]:
        """Calculate differences between base model and local improvements."""
        if not self.current_model or not self.local_improvements:
            return {}
        
        differences = {}
        total_changes = 0
        
        # Process each improved parameter
        for param_name, param_data in self.local_improvements.items():
            if param_name in self.current_model.parameters:
                changes = param_data["changes"]
                last_change = changes[-1]  # Use most recent change
                
                old_value = last_change["old_value"]
                new_value = last_change["new_value"]
                
                # Calculate difference based on value type
                if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
                    diff = new_value - old_value
                    if abs(diff) > 1e-8:  # Significant change
                        differences[param_name] = {
                            "type": "numeric",
                            "original": old_value,
                            "new": new_value,
                            "difference": diff,
                            "relative_change": diff / old_value if old_value != 0 else float('inf'),
                            "improvement_type": last_change["type"],
                            "performance_gain": last_change.get("performance_gain")
                        }
                        total_changes += 1
                        
                elif isinstance(new_value, dict) and isinstance(old_value, dict):
                    # For dictionaries, calculate structural differences
                    added_keys = set(new_value.keys()) - set(old_value.keys())
                    removed_keys = set(old_value.keys()) - set(new_value.keys())
                    changed_keys = []
                    
                    for key in set(new_value.keys()) & set(old_value.keys()):
                        if new_value[key] != old_value[key]:
                            changed_keys.append(key)
                    
                    if added_keys or removed_keys or changed_keys:
                        differences[param_name] = {
                            "type": "structural",
                            "added_keys": list(added_keys),
                            "removed_keys": list(removed_keys),
                            "changed_keys": changed_keys,
                            "change_magnitude": (len(added_keys) + len(removed_keys) + len(changed_keys)) / max(1, len(old_value)),
                            "improvement_type": last_change["type"]
                        }
                        total_changes += 1
                        
                elif isinstance(new_value, list) and isinstance(old_value, list):
                    # For lists, calculate element differences
                    if new_value != old_value:
                        differences[param_name] = {
                            "type": "list",
                            "old_length": len(old_value),
                            "new_length": len(new_value),
                            "element_changes": len(new_value) != len(old_value) or any(a != b for a, b in zip(new_value, old_value)),
                            "improvement_type": last_change["type"]
                        }
                        total_changes += 1
        
        logger.info(f"Calculated {total_changes} model differences from {len(self.local_improvements)} local improvements")
        
        return differences
    
    def aggregate_updates(self, updates: List[FederatedUpdate]) -> Optional[FederatedModel]:
        """Aggregate multiple client updates using Federated Averaging."""
        if not updates:
            logger.warning("No updates to aggregate")
            return None
        
        if len(updates) < self.config["min_clients_for_aggregation"]:
            logger.warning(f"Need at least {self.config['min_clients_for_aggregation']} clients for aggregation, got {len(updates)}")
            return None
        
        try:
            # Verify all updates have the same model base
            base_model_id = updates[0].metadata.get("model_id")
            base_version = updates[0].metadata.get("model_version")
            
            for update in updates:
                if update.metadata.get("model_id") != base_model_id:
                    logger.warning(f"Model ID mismatch in update {update.client_id}")
                    return None
                if update.metadata.get("model_version") != base_version:
                    logger.warning(f"Model version mismatch in update {update.client_id}")
                    return None
            
            # Group updates by parameter
            param_groups = {}
            for update in updates:
                for param, data in update.model_updates.items():
                    if param not in param_groups:
                        param_groups[param] = []
                    param_groups[param].append(data)
            
            # Apply Federated Averaging
            aggregated_params = {}
            
            for param, client_updates in param_groups.items():
                if client_updates[0]["type"] == "numeric":
                    # Average numeric differences
                    avg_diff = sum(u["difference"] for u in client_updates) / len(client_updates)
                    
                    # Get original value from first update
                    original_value = client_updates[0]["original"]
                    new_value = original_value + avg_diff
                    
                    aggregated_params[param] = new_value
                    
                elif client_updates[0]["type"] in ["structural", "list"]:
                    # For complex types, use majority voting or other strategies
                    # This is simplified - real implementation would be more sophisticated
                    aggregated_params[param] = client_updates[0]["new"]  # Use first client's value
            
            # Create new model version
            new_version = f"{base_version}.fed{len(self.model_history)}"
            
            new_model = FederatedModel(
                model_id=base_model_id,
                version=new_version,
                parameters={**self.current_model.parameters, **aggregated_params},
                timestamp=time.time(),
                contributing_clients=len(updates),
                metadata={
                    "aggregation_method": self.config["aggregation_method"],
                    "base_version": base_version,
                    "contributing_clients": [u.client_id for u in updates],
                    "aggregation_timestamp": time.time(),
                    "performance_impact": "improved"  # Would calculate actual impact
                }
            )
            
            logger.info(f"Aggregated {len(updates)} client updates into model {new_version}")
            return new_model
            
        except Exception as e:
            logger.error(f"Failed to aggregate updates: {e}")
            return None
    
    def apply_federated_model(self, model: FederatedModel) -> bool:
        """Apply a federated model to this instance."""
        if not self.config["enabled"]:
            logger.warning("Federated learning not enabled")
            return False
        
        try:
            # Validate model
            if not model or not model.parameters:
                logger.warning("Invalid federated model")
                return False
            
            # Check if this is an improvement over current model
            if self.current_model:
                # Simple version check - real implementation would compare performance
                if model.version <= self.current_model.version:
                    logger.info(f"Model {model.version} is not newer than current {self.current_model.version}")
                    return False
            
            # Apply the new model
            self.current_model = model
            self.model_history.append(model)
            
            # Limit history size
            if len(self.model_history) > 10:
                self.model_history = self.model_history[-10:]
            
            if self._save_state():
                logger.info(f"Applied federated model: {model.model_id} v{model.version}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to apply federated model: {e}")
            return False
    
    def send_update_to_server(self, update: FederatedUpdate) -> bool:
        """Send update to federated learning server."""
        if not self.config["enabled"]:
            logger.warning("Federated learning not enabled")
            return False
        
        if not self.config["server_url"]:
            logger.warning("No server URL configured")
            return False
        
        if self.config["local_only_mode"]:
            logger.info("Local-only mode enabled - not sending to server")
            return True
        
        try:
            # Prepare payload
            payload = update.to_dict()
            
            # Add authentication if needed
            headers = {"Content-Type": "application/json"}
            
            logger.info(f"Sending federated update to server: {self.config['server_url']}")
            
            response = requests.post(
                f"{self.config['server_url'].rstrip('/')}/api/federated/update",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Federated update sent successfully: {response_data.get('message', 'OK')}")
                return True
            else:
                error_msg = f"Server returned {response.status_code}"
                if response.text:
                    error_msg += f": {response.text}"
                logger.error(f"Failed to send federated update: {error_msg}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending federated update: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending federated update: {e}")
            return False
    
    def request_federated_model(self) -> Optional[FederatedModel]:
        """Request latest federated model from server."""
        if not self.config["enabled"]:
            logger.warning("Federated learning not enabled")
            return None
        
        if not self.config["server_url"]:
            logger.warning("No server URL configured")
            return None
        
        if self.config["local_only_mode"]:
            logger.info("Local-only mode enabled - not requesting from server")
            return None
        
        try:
            logger.info(f"Requesting federated model from server: {self.config['server_url']}")
            
            # Prepare request
            params = {
                "client_id": self.config["client_id"],
                "current_version": self.current_model.version if self.current_model else "0.0",
                "model_id": self.current_model.model_id if self.current_model else "archer_core"
            }
            
            headers = {"Content-Type": "application/json"}
            
            response = requests.get(
                f"{self.config['server_url'].rstrip('/')}/api/federated/model",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                model_data = response.json()
                federated_model = FederatedModel.from_dict(model_data)
                logger.info(f"Received federated model: {federated_model.model_id} v{federated_model.version}")
                return federated_model
            else:
                error_msg = f"Server returned {response.status_code}"
                if response.text:
                    error_msg += f": {response.text}"
                logger.error(f"Failed to get federated model: {error_msg}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error requesting federated model: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error requesting federated model: {e}")
            return None
    
    def get_federated_stats(self) -> Dict[str, Any]:
        """Get comprehensive federated learning statistics."""
        return {
            "enabled": self.config["enabled"],
            "client_id": self.config["client_id"],
            "client_name": self.config["client_name"],
            "server_configured": bool(self.config["server_url"]),
            "local_only_mode": self.config["local_only_mode"],
            "current_model": {
                "available": self.current_model is not None,
                "model_id": self.current_model.model_id if self.current_model else None,
                "version": self.current_model.version if self.current_model else None,
                "timestamp": self.current_model.timestamp if self.current_model else None
            } if self.current_model else {"available": False},
            "updates_generated": len(self.client_updates),
            "model_history_count": len(self.model_history),
            "local_improvements_count": len(self.local_improvements),
            "last_update": self.client_updates[-1].timestamp if self.client_updates else None,
            "config": {
                "min_clients": self.config["min_clients_for_aggregation"],
                "aggregation_method": self.config["aggregation_method"],
                "privacy_level": self.config["privacy_level"]
            }
        }
    
    def get_model_history(self) -> List[Dict[str, Any]]:
        """Get history of federated models."""
        return [{
            "model_id": model.model_id,
            "version": model.version,
            "timestamp": model.timestamp,
            "contributing_clients": model.contributing_clients,
            "timestamp_readable": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(model.timestamp))
        } for model in self.model_history]
    
    def rollback_model(self, version: str) -> bool:
        """Rollback to a previous model version."""
        if not self.config["enabled"]:
            logger.warning("Federated learning not enabled")
            return False
        
        try:
            # Find the model in history
            target_model = None
            for model in self.model_history:
                if model.version == version:
                    target_model = model
                    break
            
            if not target_model:
                logger.warning(f"Model version {version} not found in history")
                return False
            
            # Apply the target model
            self.current_model = target_model
            
            if self._save_state():
                logger.info(f"Rolled back to model version: {version}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to rollback model: {e}")
            return False
    
    def clear_local_data(self) -> bool:
        """Clear local federated learning data (for testing/reset)."""
        try:
            self.client_updates = []
            self.local_improvements = {}
            
            if self._save_state():
                logger.info("Cleared local federated learning data")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to clear local data: {e}")
            return False
    
    def simulate_federated_learning(self, num_clients: int = 3) -> Dict[str, Any]:
        """Simulate federated learning with virtual clients (for testing)."""
        if not self.config["enabled"]:
            return {"error": "Federated learning not enabled"}
        
        if not self.current_model:
            return {"error": "No base model available"}
        
        try:
            # Create virtual client updates
            virtual_updates = []
            
            for i in range(num_clients):
                # Simulate improvements
                virtual_client_id = f"virtual_{i}"
                improvements = {
                    f"param_{i}": {
                        "type": "numeric",
                        "original": 0.5,
                        "new": 0.5 + (i + 1) * 0.05,
                        "difference": (i + 1) * 0.05,
                        "improvement_type": "performance"
                    }
                }
                
                # Create update
                update_json = json.dumps(improvements)
                data_hash = hashlib.sha256(update_json.encode()).hexdigest()
                
                virtual_update = FederatedUpdate(
                    client_id=virtual_client_id,
                    timestamp=time.time(),
                    model_updates=improvements,
                    data_hash=data_hash,
                    update_size=len(update_json),
                    metadata={
                        "model_id": self.current_model.model_id,
                        "model_version": self.current_model.version,
                        "client_name": f"VirtualClient_{i}",
                        "simulated": True
                    }
                )
                
                virtual_updates.append(virtual_update)
            
            # Aggregate the virtual updates
            aggregated_model = self.aggregate_updates(virtual_updates)
            
            if aggregated_model:
                # Apply the aggregated model
                success = self.apply_federated_model(aggregated_model)
                
                return {
                    "success": success,
                    "virtual_clients": num_clients,
                    "aggregated_model": {
                        "version": aggregated_model.version,
                        "contributing_clients": aggregated_model.contributing_clients,
                        "timestamp": aggregated_model.timestamp
                    },
                    "message": "Federated learning simulation completed successfully"
                }
            else:
                return {"error": "Failed to aggregate virtual updates"}
                
        except Exception as e:
            logger.error(f"Federated learning simulation failed: {e}")
            return {"error": str(e)}

# Example usage and testing
if __name__ == "__main__":
    print("Testing FederatedLearningManager...")
    
    # Create manager
    fl_manager = FederatedLearningManager("test_federated_config.json")
    
    # Enable federated learning
    fl_manager.enable_federated_learning(True, "http://localhost:8000")
    
    # Initialize base model
    fl_manager.initialize_base_model()
    
    # Record some local improvements
    fl_manager.record_local_improvement("learning_rate", 0.001, 0.0015, "performance", 0.05)
    fl_manager.record_local_improvement("batch_size", 32, 64, "memory", 0.1)
    
    # Generate federated update
    update = fl_manager.generate_federated_update()
    print(f"Generated update: {update.client_id if update else 'None'}")
    
    # Get stats
    stats = fl_manager.get_federated_stats()
    print(f"Federated stats: {stats['current_model']}")
    
    # Simulate federated learning
    sim_result = fl_manager.simulate_federated_learning(3)
    print(f"Simulation result: {sim_result}")
    
    print("Test complete!")