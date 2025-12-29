"""
ARCHER Automation Package

Provides comprehensive system control, automation, and remote access capabilities.

Modules:
- controller: Main AutomationController class with window management, mouse/keyboard control,
  macro recording/playback, file management, and system-level automation
- remote: Remote automation integration with security and API endpoints

Usage:
    from src.automation.controller import start_automation_system
    controller = start_automation_system()
    controller.mouse_move(100, 100)
    controller.keyboard_type("Hello ARCHER!")
"""

from .controller import (
    AutomationController,
    start_automation_system,
    stop_automation_system,
    get_automation_controller
)

from .remote import (
    AutomationRemoteController,
    start_automation_remote_system,
    stop_automation_remote_system,
    get_automation_remote_controller,
    extend_remote_access_with_automation
)

__all__ = [
    # Controller
    'AutomationController',
    'start_automation_system',
    'stop_automation_system',
    'get_automation_controller',
    
    # Remote
    'AutomationRemoteController',
    'start_automation_remote_system',
    'stop_automation_remote_system',
    'get_automation_remote_controller',
    'extend_remote_access_with_automation'
]

# Version information
__version__ = "1.0.0"
__author__ = "Agent_AUTO (Automation & System Control Developer)"
__description__ = "ARCHER Automation System - Comprehensive computer control and automation"
__license__ = "MIT"