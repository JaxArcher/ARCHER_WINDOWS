"""
Automation Remote Access Integration for ARCHER.

Provides secure remote control capabilities integrating with the existing
remote access system and automation controller.
"""

import logging
import json
import threading
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

# Import existing remote access and automation controller
try:
    from src.extensions.remote_access import RemoteAccessServer, start_remote_access, stop_remote_access
    from src.automation.controller import AutomationController, get_automation_controller
except ImportError:
    # Fallback for testing
    class RemoteAccessServer:
        def __init__(self):
            self.running = False
        
        def start(self):
            self.running = True
        
        def stop(self):
            self.running = False
    
    class AutomationController:
        def __init__(self):
            pass
        
        def halt_all(self):
            pass
    
    def start_remote_access():
        return RemoteAccessServer()
    
    def stop_remote_access():
        pass
    
    def get_automation_controller():
        return AutomationController()

logger = logging.getLogger(__name__)


class AutomationRemoteController:
    """
    Remote automation controller that integrates with the existing remote access system.
    
    Features:
    - Secure remote automation command execution
    - Integration with existing FastAPI remote access server
    - Enhanced security for automation commands
    - Real-time monitoring and control
    """
    
    def __init__(self, remote_server: Optional[RemoteAccessServer] = None):
        self.remote_server = remote_server or RemoteAccessServer()
        self.automation_controller = get_automation_controller()
        self.remote_commands = {}
        self.command_history = []
        
        # Security settings
        self.allowed_remote_commands = [
            "mouse_move", "mouse_click", "keyboard_type", "keyboard_press",
            "window_maximize", "window_minimize", "get_system_info",
            "list_files", "read_file", "halt_all"
        ]
        
        logger.info("Automation Remote Controller initialized")
    
    def register_remote_command(self, command_name: str, handler: callable):
        """Register a remote command handler."""
        self.remote_commands[command_name] = handler
        logger.info(f"Registered remote command: {command_name}")
    
    def execute_remote_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a remote automation command with security checks."""
        try:
            command_name = command.get("command")
            params = command.get("params", {})
            
            # Security check
            if command_name not in self.allowed_remote_commands:
                logger.warning(f"Blocked unauthorized remote command: {command_name}")
                return {
                    "success": False,
                    "error": "Command not allowed for remote execution",
                    "command": command_name
                }
            
            # Execute command
            if command_name == "mouse_move":
                result = self.automation_controller.mouse_move(
                    params.get("x", 0),
                    params.get("y", 0),
                    params.get("duration", 0.5)
                )
            
            elif command_name == "mouse_click":
                result = self.automation_controller.mouse_click(
                    params.get("button", "left")
                )
            
            elif command_name == "keyboard_type":
                result = self.automation_controller.keyboard_type(
                    params.get("text", ""),
                    params.get("interval", 0.02)
                )
            
            elif command_name == "keyboard_press":
                result = self.automation_controller.keyboard_press(
                    params.get("key", "")
                )
            
            elif command_name == "window_maximize":
                result = self.automation_controller.maximize_window()
            
            elif command_name == "window_minimize":
                result = self.automation_controller.minimize_window()
            
            elif command_name == "get_system_info":
                result = self.automation_controller.get_system_info()
            
            elif command_name == "list_files":
                result = self.automation_controller.list_files(
                    params.get("directory", "."),
                    params.get("pattern", "*")
                )
            
            elif command_name == "read_file":
                result = self.automation_controller.read_file(
                    params.get("file_path", "")
                )
            
            elif command_name == "halt_all":
                result = True
                self.automation_controller.halt_all()
            
            else:
                return {
                    "success": False,
                    "error": "Unknown command",
                    "command": command_name
                }
            
            # Log command execution
            self._log_remote_command(command_name, params, result)
            
            return {
                "success": True,
                "result": result,
                "command": command_name
            }
            
        except Exception as e:
            logger.error(f"Remote command execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command.get("command", "unknown")
            }
    
    def _log_remote_command(self, command_name: str, params: Dict[str, Any], result: Any):
        """Log remote command execution."""
        log_entry = {
            "timestamp": time.time(),
            "command": command_name,
            "params": params,
            "result": result,
            "source": "remote"
        }
        
        self.command_history.append(log_entry)
        
        # Keep history size manageable
        if len(self.command_history) > 1000:
            self.command_history = self.command_history[-1000:]
        
        # Save to file
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            with open(log_dir / "automation_remote_commands.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to log remote command: {e}")
    
    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent remote command history."""
        return self.command_history[-limit:]
    
    def add_allowed_command(self, command_name: str):
        """Add a command to the allowed remote commands list."""
        if command_name not in self.allowed_remote_commands:
            self.allowed_remote_commands.append(command_name)
            logger.info(f"Added allowed remote command: {command_name}")
    
    def remove_allowed_command(self, command_name: str):
        """Remove a command from the allowed remote commands list."""
        if command_name in self.allowed_remote_commands:
            self.allowed_remote_commands.remove(command_name)
            logger.info(f"Removed allowed remote command: {command_name}")
    
    def start_remote_automation(self):
        """Start the remote automation system."""
        try:
            # Start the remote access server
            self.remote_server.start()
            
            # Register automation-specific endpoints
            self._register_automation_endpoints()
            
            logger.info("Remote automation system started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start remote automation: {e}")
            return False
    
    def stop_remote_automation(self):
        """Stop the remote automation system."""
        try:
            self.remote_server.stop()
            logger.info("Remote automation system stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop remote automation: {e}")
            return False
    
    def _register_automation_endpoints(self):
        """Register automation-specific endpoints with the remote server."""
        # This would be implemented by extending the FastAPI routes
        # in the existing remote access server
        pass
    
    def get_remote_status(self) -> Dict[str, Any]:
        """Get remote automation system status."""
        return {
            "automation_ready": True,
            "remote_server_running": self.remote_server.running if hasattr(self.remote_server, 'running') else False,
            "allowed_commands": len(self.allowed_remote_commands),
            "command_history_count": len(self.command_history)
        }


# Integration with existing remote access system

def extend_remote_access_with_automation():
    """Extend the existing remote access system with automation capabilities."""
    try:
        # Get the existing remote access server
        remote_server = start_remote_access()
        
        # Create automation remote controller
        automation_remote = AutomationRemoteController(remote_server)
        
        # Add automation-specific API endpoints
        if hasattr(remote_server, 'app') and remote_server.app:
            from fastapi import APIRouter
            
            automation_router = APIRouter(prefix="/automation", tags=["automation"])
            
            @automation_router.post("/command")
            async def execute_automation_command(
                command: dict,
                api_key: str = Depends(remote_server.security.verify_api_key)
            ):
                """Execute automation command via remote API."""
                result = automation_remote.execute_remote_command(command)
                return result
            
            @automation_router.get("/status")
            async def get_automation_status(
                api_key: str = Depends(remote_server.security.verify_api_key)
            ):
                """Get automation system status."""
                return {
                    "status": "online",
                    "automation_ready": True,
                    **automation_remote.get_remote_status()
                }
            
            @automation_router.get("/history")
            async def get_command_history(
                limit: int = 50,
                api_key: str = Depends(remote_server.security.verify_api_key)
            ):
                """Get recent automation command history."""
                return {
                    "history": automation_remote.get_command_history(limit),
                    "total_commands": len(automation_remote.command_history)
                }
            
            # Include the router in the main app
            remote_server.app.include_router(automation_router)
            
            logger.info("Extended remote access with automation endpoints")
            return automation_remote
        
    except Exception as e:
        logger.error(f"Failed to extend remote access with automation: {e}")
        return None


# Global instance
automation_remote_controller = None


def get_automation_remote_controller() -> AutomationRemoteController:
    """Get the global automation remote controller instance."""
    global automation_remote_controller
    if automation_remote_controller is None:
        automation_remote_controller = AutomationRemoteController()
    return automation_remote_controller


def start_automation_remote_system():
    """Start the complete automation remote system."""
    global automation_remote_controller
    if automation_remote_controller is None:
        automation_remote_controller = extend_remote_access_with_automation()
    return automation_remote_controller


def stop_automation_remote_system():
    """Stop the automation remote system."""
    global automation_remote_controller
    if automation_remote_controller:
        automation_remote_controller.stop_remote_automation()
        automation_remote_controller = None