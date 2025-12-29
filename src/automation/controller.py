"""
Automation Controller for ARCHER.

Provides comprehensive computer control, window management, macro recording/playback,
file management, and system-level automation with memory integration and security.
"""

import logging
import os
import subprocess
import threading
import time
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

# Import memory system for integration
try:
    from src.memory.episodic_memory import EpisodicMemory
except ImportError:
    # Fallback for testing
    class EpisodicMemory:
        def __init__(self):
            self.events = []
        
        def store_event(self, event_type, data, metadata=None):
            event = {
                "event_type": event_type,
                "data": data,
                "metadata": metadata or {},
                "timestamp": time.time()
            }
            self.events.append(event)
            logging.info(f"Stored event: {event_type}")

logger = logging.getLogger(__name__)


class AutomationController:
    """
    Comprehensive automation controller with memory integration and security.
    
    Features:
    - Window management (pyautogui-based)
    - Mouse/keyboard control
    - Macro recording and playback
    - File management
    - System-level triggers
    - Memory integration (episodic logging)
    - Security checks and permission system
    """
    
    def __init__(self):
        self.halt_event = threading.Event()
        self.active_commands = []
        self.lock = threading.Lock()
        self.macro_recording = False
        self.recorded_macro = []
        self.security_enabled = True
        
        # Initialize memory system
        self.episodic_memory = EpisodicMemory()
        
        # Security settings
        self.destructive_commands = [
            "rm", "del", "format", "shutdown", "reboot", "reg delete",
            "taskkill", "sc delete", "net user", "wmic", "powershell -c"
        ]
        
        # Window management settings
        self.window_positions = {}
        self.active_window = None
        
        logger.info("Automation Controller initialized with memory integration")
        
        # Log initialization event
        self._log_automation_event("initialization", {"status": "success"})
    
    def _log_automation_event(self, event_type: str, data: Dict[str, Any]):
        """Log automation events to episodic memory."""
        try:
            self.episodic_memory.store_event(
                event_type=f"automation_{event_type}",
                data=data,
                metadata={
                    "agent": "agent_auto",
                    "timestamp": datetime.now().isoformat(),
                    "security_level": "info"
                }
            )
        except Exception as e:
            logger.error(f"Failed to log automation event: {e}")
    
    def _is_destructive_command(self, command: str) -> bool:
        """Check if a command is potentially destructive."""
        command_lower = command.lower()
        return any(dc in command_lower for dc in self.destructive_commands)
    
    def _request_permission(self, command: str) -> bool:
        """Request permission for destructive commands."""
        if not self.security_enabled:
            return True
        
        # In production, this would prompt user or check permissions
        # For now, log and deny by default
        logger.warning(f"Destructive command requires permission: {command}")
        self._log_automation_event("security_alert", {
            "command": command,
            "action": "blocked",
            "reason": "destructive_command_detected"
        })
        return False
    
    # ===== Window Management =====
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the active window."""
        if self.halt_event.is_set():
            return None
        
        try:
            # Windows-specific implementation
            import win32gui
            import win32process
            
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                window_text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                
                # Get process info
                thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
                
                self.active_window = {
                    "title": window_text,
                    "class": class_name,
                    "process_id": process_id,
                    "thread_id": thread_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                self._log_automation_event("window_focus", {
                    "window": window_text,
                    "process_id": process_id
                })
                
                return self.active_window
            
            return None
            
        except ImportError:
            logger.warning("win32gui not available - window management limited")
            return None
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
            return None
    
    def move_window(self, x: int, y: int, width: int = None, height: int = None) -> bool:
        """Move and resize the active window."""
        if self.halt_event.is_set():
            return False
        
        try:
            import win32gui
            import win32con
            
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                if width and height:
                    win32gui.MoveWindow(hwnd, x, y, width, height, True)
                else:
                    # Just move, keep current size
                    rect = win32gui.GetWindowRect(hwnd)
                    current_width = rect[2] - rect[0]
                    current_height = rect[3] - rect[1]
                    win32gui.MoveWindow(hwnd, x, y, current_width, current_height, True)
                
                self._log_automation_event("window_move", {
                    "position": {"x": x, "y": y},
                    "size": {"width": width, "height": height}
                })
                return True
            
            return False
            
        except ImportError:
            logger.warning("win32gui not available - window movement disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to move window: {e}")
            return False
    
    def maximize_window(self) -> bool:
        """Maximize the active window."""
        if self.halt_event.is_set():
            return False
        
        try:
            import win32gui
            import win32con
            
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                self._log_automation_event("window_maximize", {})
                return True
            
            return False
            
        except ImportError:
            logger.warning("win32gui not available - window maximize disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
            return False
    
    def minimize_window(self) -> bool:
        """Minimize the active window."""
        if self.halt_event.is_set():
            return False
        
        try:
            import win32gui
            import win32con
            
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                self._log_automation_event("window_minimize", {})
                return True
            
            return False
            
        except ImportError:
            logger.warning("win32gui not available - window minimize disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
            return False
    
    # ===== Mouse Control =====
    
    def mouse_move(self, x: int, y: int, duration: float = 0.5) -> bool:
        """Move mouse to coordinates."""
        if self.halt_event.is_set():
            return False
        
        try:
            import pyautogui
            
            pyautogui.moveTo(x, y, duration=duration)
            self._log_automation_event("mouse_move", {
                "position": {"x": x, "y": y},
                "duration": duration
            })
            return True
            
        except ImportError:
            logger.warning("pyautogui not available - mouse control disabled")
            return False
        except Exception as e:
            logger.error(f"Mouse move failed: {e}")
            return False
    
    def mouse_click(self, button: str = 'left') -> bool:
        """Click mouse button."""
        if self.halt_event.is_set():
            return False
        
        try:
            import pyautogui
            
            if button == 'left':
                pyautogui.click()
            elif button == 'right':
                pyautogui.rightClick()
            elif button == 'middle':
                pyautogui.middleClick()
            else:
                logger.warning(f"Unknown mouse button: {button}")
                return False
            
            self._log_automation_event("mouse_click", {"button": button})
            return True
            
        except ImportError:
            logger.warning("pyautogui not available - mouse control disabled")
            return False
        except Exception as e:
            logger.error(f"Mouse click failed: {e}")
            return False
    
    def mouse_scroll(self, clicks: int, direction: str = 'vertical') -> bool:
        """Scroll mouse wheel."""
        if self.halt_event.is_set():
            return False
        
        try:
            import pyautogui
            
            if direction == 'vertical':
                pyautogui.scroll(clicks)
            elif direction == 'horizontal':
                pyautogui.hscroll(clicks)
            else:
                logger.warning(f"Unknown scroll direction: {direction}")
                return False
            
            self._log_automation_event("mouse_scroll", {
                "clicks": clicks,
                "direction": direction
            })
            return True
            
        except ImportError:
            logger.warning("pyautogui not available - mouse control disabled")
            return False
        except Exception as e:
            logger.error(f"Mouse scroll failed: {e}")
            return False
    
    # ===== Keyboard Control =====
    
    def keyboard_type(self, text: str, interval: float = 0.02) -> bool:
        """Type text on keyboard."""
        if self.halt_event.is_set():
            return False
        
        try:
            import pyautogui
            
            pyautogui.typewrite(text, interval=interval)
            self._log_automation_event("keyboard_type", {
                "text": text[:50] + "..." if len(text) > 50 else text,
                "length": len(text)
            })
            return True
            
        except ImportError:
            logger.warning("pyautogui not available - keyboard control disabled")
            return False
        except Exception as e:
            logger.error(f"Keyboard type failed: {e}")
            return False
    
    def keyboard_press(self, key: str) -> bool:
        """Press a keyboard key."""
        if self.halt_event.is_set():
            return False
        
        try:
            import pyautogui
            
            pyautogui.press(key)
            self._log_automation_event("keyboard_press", {"key": key})
            return True
            
        except ImportError:
            logger.warning("pyautogui not available - keyboard control disabled")
            return False
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return False
    
    def keyboard_hotkey(self, keys: List[str]) -> bool:
        """Press a keyboard hotkey combination."""
        if self.halt_event.is_set():
            return False
        
        try:
            import pyautogui
            
            pyautogui.hotkey(*keys)
            self._log_automation_event("keyboard_hotkey", {"keys": keys})
            return True
            
        except ImportError:
            logger.warning("pyautogui not available - keyboard control disabled")
            return False
        except Exception as e:
            logger.error(f"Hotkey failed: {e}")
            return False
    
    # ===== Macro Recording & Playback =====
    
    def start_macro_recording(self) -> bool:
        """Start recording a macro."""
        if self.halt_event.is_set():
            return False
        
        if self.macro_recording:
            logger.warning("Macro recording already in progress")
            return False
        
        self.macro_recording = True
        self.recorded_macro = []
        
        self._log_automation_event("macro_start", {})
        logger.info("Started macro recording")
        return True
    
    def stop_macro_recording(self) -> bool:
        """Stop recording a macro."""
        if not self.macro_recording:
            logger.warning("No macro recording in progress")
            return False
        
        self.macro_recording = False
        
        self._log_automation_event("macro_stop", {
            "actions": len(self.recorded_macro)
        })
        logger.info(f"Stopped macro recording - {len(self.recorded_macro)} actions recorded")
        return True
    
    def save_macro(self, name: str) -> bool:
        """Save recorded macro to file."""
        if not self.recorded_macro:
            logger.warning("No macro to save")
            return False
        
        try:
            macro_dir = Path("src/automation/macros")
            macro_dir.mkdir(parents=True, exist_ok=True)
            
            macro_file = macro_dir / f"{name}.json"
            
            with open(macro_file, 'w') as f:
                json.dump({
                    "name": name,
                    "actions": self.recorded_macro,
                    "timestamp": datetime.now().isoformat(),
                    "action_count": len(self.recorded_macro)
                }, f, indent=2)
            
            self._log_automation_event("macro_save", {"name": name})
            logger.info(f"Saved macro: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save macro: {e}")
            return False
    
    def load_macro(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """Load macro from file."""
        try:
            macro_file = Path(f"src/automation/macros/{name}.json")
            
            if not macro_file.exists():
                logger.warning(f"Macro not found: {name}")
                return None
            
            with open(macro_file, 'r') as f:
                macro_data = json.load(f)
            
            self._log_automation_event("macro_load", {"name": name})
            logger.info(f"Loaded macro: {name} ({len(macro_data['actions'])} actions)")
            return macro_data['actions']
            
        except Exception as e:
            logger.error(f"Failed to load macro: {e}")
            return None
    
    def play_macro(self, name: str, speed: float = 1.0) -> bool:
        """Play a recorded macro."""
        if self.halt_event.is_set():
            return False
        
        actions = self.load_macro(name)
        if not actions:
            return False
        
        def _play():
            try:
                for action in actions:
                    if self.halt_event.is_set():
                        break
                    
                    action_type = action.get('type')
                    params = action.get('params', {})
                    
                    # Apply speed factor
                    if 'duration' in params:
                        params['duration'] = params['duration'] / speed
                    if 'interval' in params:
                        params['interval'] = params['interval'] / speed
                    
                    # Execute action
                    if action_type == 'mouse_move':
                        self.mouse_move(params['x'], params['y'], params.get('duration', 0.5))
                    elif action_type == 'mouse_click':
                        self.mouse_click(params.get('button', 'left'))
                    elif action_type == 'keyboard_type':
                        self.keyboard_type(params['text'], params.get('interval', 0.02))
                    elif action_type == 'keyboard_press':
                        self.keyboard_press(params['key'])
                    elif action_type == 'delay':
                        time.sleep(params.get('seconds', 0.1))
                    
                    # Small delay between actions
                    time.sleep(0.05)
                
                self._log_automation_event("macro_play", {
                    "name": name,
                    "actions": len(actions),
                    "speed": speed
                })
                
            except Exception as e:
                logger.error(f"Macro playback error: {e}")
                self._log_automation_event("macro_error", {
                    "name": name,
                    "error": str(e)
                })
        
        thread = threading.Thread(target=_play, daemon=True)
        with self.lock:
            self.active_commands.append(thread)
        thread.start()
        
        return True
    
    def _record_action(self, action_type: str, params: Dict[str, Any]):
        """Record an action during macro recording."""
        if self.macro_recording:
            action = {
                "type": action_type,
                "params": params,
                "timestamp": datetime.now().isoformat()
            }
            self.recorded_macro.append(action)
    
    # ===== File Management =====
    
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in a directory."""
        if self.halt_event.is_set():
            return []
        
        try:
            path = Path(directory)
            if not path.exists():
                return []
            
            files = [str(f) for f in path.glob(pattern)]
            
            self._log_automation_event("file_list", {
                "directory": directory,
                "pattern": pattern,
                "count": len(files)
            })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Read file content."""
        if self.halt_event.is_set():
            return None
        
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            content = path.read_text(encoding='utf-8')
            
            self._log_automation_event("file_read", {
                "file": file_path,
                "size": len(content)
            })
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return None
    
    def write_file(self, file_path: str, content: str, overwrite: bool = False) -> bool:
        """Write content to file."""
        if self.halt_event.is_set():
            return False
        
        try:
            path = Path(file_path)
            
            # Check if file exists and overwrite is False
            if path.exists() and not overwrite:
                logger.warning(f"File already exists and overwrite=False: {file_path}")
                return False
            
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            
            self._log_automation_event("file_write", {
                "file": file_path,
                "size": len(content),
                "overwrite": overwrite
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        if self.halt_event.is_set():
            return False
        
        # Security check for destructive operation
        if self._is_destructive_command(f"delete {file_path}") and not self._request_permission(f"delete {file_path}"):
            return False
        
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            path.unlink()
            
            self._log_automation_event("file_delete", {"file": file_path})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    def copy_file(self, source: str, destination: str) -> bool:
        """Copy a file."""
        if self.halt_event.is_set():
            return False
        
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if not source_path.exists():
                return False
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use shutil for cross-platform file copy
            import shutil
            shutil.copy2(source_path, dest_path)
            
            self._log_automation_event("file_copy", {
                "source": source,
                "destination": destination
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return False
    
    # ===== System Commands =====
    
    def run_shell_command(self, command: str, timeout: int = 30) -> Optional[str]:
        """Run a shell command with timeout and security checks."""
        if self.halt_event.is_set():
            return None
        
        # Security check for destructive commands
        if self._is_destructive_command(command) and not self._request_permission(command):
            return None
        
        try:
            logger.info(f"Running shell command: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr}")
            
            self._log_automation_event("shell_command", {
                "command": command,
                "success": result.returncode == 0,
                "return_code": result.returncode
            })
            
            return output
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            self._log_automation_event("command_timeout", {"command": command})
            return None
            
        except Exception as e:
            logger.error(f"Command failed: {e}")
            self._log_automation_event("command_error", {
                "command": command,
                "error": str(e)
            })
            return None
    
    def open_application(self, path: str) -> bool:
        """Open an application."""
        if self.halt_event.is_set():
            return False
        
        try:
            # Security check
            if self._is_destructive_command(path) and not self._request_permission(path):
                return False
            
            # Use subprocess to open application
            subprocess.Popen([path], shell=True)
            
            self._log_automation_event("app_open", {"path": path})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to open application: {e}")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            import psutil
            import platform
            
            info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "cpu_cores": psutil.cpu_count(logical=True),
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_total": psutil.virtual_memory().total,
                "memory_used": psutil.virtual_memory().used,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": {}
            }
            
            # Get disk usage
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    info["disk_usage"][partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    }
                except:
                    pass
            
            self._log_automation_event("system_info", info)
            
            return info
            
        except ImportError:
            logger.warning("psutil not available - limited system info")
            return {
                "os": platform.system(),
                "os_version": platform.version(),
                "warning": "psutil not installed - install for full system info"
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}
    
    # ===== Security & Control =====
    
    def halt_all(self):
        """IMMEDIATE HALT - Stop all active automation actions."""
        logger.warning("ARCHER HALT activated - stopping all automation")
        
        with self.lock:
            self.halt_event.set()
            
            # Stop any running threads
            for thread in self.active_commands[:]:
                if thread.is_alive():
                    # Note: Can't forcefully stop threads in Python
                    pass
                self.active_commands.remove(thread)
        
        # Reset halt event for future use
        self.halt_event.clear()
        
        self._log_automation_event("halt", {"status": "success"})
        logger.info("All automation actions halted")
    
    def is_halted(self) -> bool:
        """Check if halt is active."""
        return self.halt_event.is_set()
    
    def set_security_enabled(self, enabled: bool):
        """Enable or disable security checks."""
        self.security_enabled = enabled
        self._log_automation_event("security_change", {"enabled": enabled})
        logger.info(f"Security checks {'enabled' if enabled else 'disabled'}")
    
    def add_destructive_command(self, command: str):
        """Add a command to the destructive commands list."""
        if command not in self.destructive_commands:
            self.destructive_commands.append(command)
            self._log_automation_event("security_add", {"command": command})
    
    def remove_destructive_command(self, command: str):
        """Remove a command from the destructive commands list."""
        if command in self.destructive_commands:
            self.destructive_commands.remove(command)
            self._log_automation_event("security_remove", {"command": command})
    
    # ===== Trigger System =====
    
    def create_trigger(self, trigger_name: str, condition: Dict[str, Any], action: Dict[str, Any]) -> bool:
        """Create a system-level trigger."""
        try:
            trigger_dir = Path("src/automation/triggers")
            trigger_dir.mkdir(parents=True, exist_ok=True)
            
            trigger_file = trigger_dir / f"{trigger_name}.json"
            
            trigger_data = {
                "name": trigger_name,
                "condition": condition,
                "action": action,
                "enabled": True,
                "created_at": datetime.now().isoformat(),
                "last_triggered": None,
                "trigger_count": 0
            }
            
            with open(trigger_file, 'w') as f:
                json.dump(trigger_data, f, indent=2)
            
            self._log_automation_event("trigger_create", {"name": trigger_name})
            return True
            
        except Exception as e:
            logger.error(f"Failed to create trigger: {e}")
            return False
    
    def check_triggers(self) -> List[str]:
        """Check all triggers and execute if conditions are met."""
        triggered = []
        
        try:
            trigger_dir = Path("src/automation/triggers")
            if not trigger_dir.exists():
                return triggered
            
            for trigger_file in trigger_dir.glob("*.json"):
                with open(trigger_file, 'r') as f:
                    trigger_data = json.load(f)
                
                if not trigger_data.get("enabled", False):
                    continue
                
                # Check condition
                condition_met = self._check_trigger_condition(trigger_data["condition"])
                
                if condition_met:
                    # Execute action
                    self._execute_trigger_action(trigger_data["action"])
                    
                    # Update trigger data
                    trigger_data["last_triggered"] = datetime.now().isoformat()
                    trigger_data["trigger_count"] = trigger_data.get("trigger_count", 0) + 1
                    
                    with open(trigger_file, 'w') as f:
                        json.dump(trigger_data, f, indent=2)
                    
                    triggered.append(trigger_data["name"])
                    self._log_automation_event("trigger_execute", {"name": trigger_data["name"]})
            
            return triggered
            
        except Exception as e:
            logger.error(f"Trigger check error: {e}")
            return triggered
    
    def _check_trigger_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if a trigger condition is met."""
        try:
            condition_type = condition.get("type")
            
            if condition_type == "time":
                # Check time-based condition
                current_time = datetime.now()
                target_time = condition.get("time")
                if target_time:
                    # Simple time comparison (HH:MM format)
                    current_time_str = current_time.strftime("%H:%M")
                    return current_time_str == target_time
            
            elif condition_type == "file_exists":
                # Check if file exists
                file_path = condition.get("path")
                if file_path:
                    return Path(file_path).exists()
            
            elif condition_type == "system_load":
                # Check system load
                try:
                    import psutil
                    threshold = condition.get("threshold", 80)
                    current_load = psutil.cpu_percent(interval=1)
                    return current_load > threshold
                except:
                    return False
            
            elif condition_type == "memory_usage":
                # Check memory usage
                try:
                    import psutil
                    threshold = condition.get("threshold", 80)
                    current_usage = psutil.virtual_memory().percent
                    return current_usage > threshold
                except:
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check trigger condition: {e}")
            return False
    
    def _execute_trigger_action(self, action: Dict[str, Any]):
        """Execute a trigger action."""
        try:
            action_type = action.get("type")
            
            if action_type == "run_command":
                command = action.get("command")
                if command:
                    self.run_shell_command(command)
            
            elif action_type == "open_application":
                path = action.get("path")
                if path:
                    self.open_application(path)
            
            elif action_type == "log_message":
                message = action.get("message")
                if message:
                    logger.info(f"Trigger message: {message}")
                    self._log_automation_event("trigger_message", {"message": message})
            
            elif action_type == "play_macro":
                macro_name = action.get("macro_name")
                if macro_name:
                    self.play_macro(macro_name)
            
        except Exception as e:
            logger.error(f"Failed to execute trigger action: {e}")


# Global instance for easy access
automation_controller = None


def get_automation_controller() -> AutomationController:
    """Get the global automation controller instance."""
    global automation_controller
    if automation_controller is None:
        automation_controller = AutomationController()
    return automation_controller


def start_automation_system():
    """Start the automation system."""
    global automation_controller
    if automation_controller is None:
        automation_controller = AutomationController()
    return automation_controller


def stop_automation_system():
    """Stop the automation system."""
    global automation_controller
    if automation_controller:
        automation_controller.halt_all()
        automation_controller = None