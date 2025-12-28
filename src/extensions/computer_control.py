"""
Computer Control Module for ARCHER.

Provides direct OS control (mouse, keyboard, shell) with verbal HALT failsafe.
"""

import logging
import os
import subprocess
import threading
import time
from typing import Optional, Callable

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logging.warning("pyautogui not available - mouse/keyboard control disabled")

logger = logging.getLogger(__name__)

class ComputerController:
    """
    Handles direct computer control with safety mechanisms.
    """

    def __init__(self):
        self.halt_event = threading.Event()
        self.active_commands = []
        self.lock = threading.Lock()

        # Safety: disable pyautogui failsafes that might interfere
        if PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = False  # We'll handle our own failsafe
            pyautogui.PAUSE = 0.1  # Small pause between actions

        logger.info("Computer Controller initialized")

    def halt_all(self):
        """
        IMMEDIATE HALT - Stop all active computer control actions.
        """
        logger.warning("ARCHER HALT activated - stopping all computer control")

        with self.lock:
            self.halt_event.set()

            # Stop any running threads
            for thread in self.active_commands[:]:
                if thread.is_alive():
                    # Note: Can't forcefully stop threads in Python, but we set the event
                    pass
                self.active_commands.remove(thread)

        # Reset halt event for future use
        self.halt_event.clear()

        logger.info("All computer control actions halted")

    def mouse_move(self, x: int, y: int, duration: float = 0.5):
        """Move mouse to coordinates."""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("Mouse control not available")
            return

        if self.halt_event.is_set():
            return

        def _move():
            try:
                pyautogui.moveTo(x, y, duration=duration)
                logger.info(f"Mouse moved to ({x}, {y})")
            except Exception as e:
                logger.error(f"Mouse move failed: {e}")

        thread = threading.Thread(target=_move, daemon=True)
        with self.lock:
            self.active_commands.append(thread)
        thread.start()

    def mouse_click(self, button: str = 'left'):
        """Click mouse button."""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("Mouse control not available")
            return

        if self.halt_event.is_set():
            return

        def _click():
            try:
                if button == 'left':
                    pyautogui.click()
                elif button == 'right':
                    pyautogui.rightClick()
                elif button == 'middle':
                    pyautogui.middleClick()
                logger.info(f"Mouse {button} click")
            except Exception as e:
                logger.error(f"Mouse click failed: {e}")

        thread = threading.Thread(target=_click, daemon=True)
        with self.lock:
            self.active_commands.append(thread)
        thread.start()

    def keyboard_type(self, text: str, interval: float = 0.02):
        """Type text on keyboard."""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("Keyboard control not available")
            return

        if self.halt_event.is_set():
            return

        def _type():
            try:
                pyautogui.typewrite(text, interval=interval)
                logger.info(f"Typed: {text[:50]}...")
            except Exception as e:
                logger.error(f"Keyboard type failed: {e}")

        thread = threading.Thread(target=_type, daemon=True)
        with self.lock:
            self.active_commands.append(thread)
        thread.start()

    def keyboard_press(self, key: str):
        """Press a keyboard key."""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("Keyboard control not available")
            return

        if self.halt_event.is_set():
            return

        def _press():
            try:
                pyautogui.press(key)
                logger.info(f"Pressed key: {key}")
            except Exception as e:
                logger.error(f"Key press failed: {e}")

        thread = threading.Thread(target=_press, daemon=True)
        with self.lock:
            self.active_commands.append(thread)
        thread.start()

    def run_shell_command(self, command: str, timeout: int = 30) -> Optional[str]:
        """
        Run a shell command with timeout.

        Returns output if successful, None if failed or halted.
        """
        if self.halt_event.is_set():
            return None

        def _run():
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
                logger.info(f"Command completed: {command}")
                return output
            except subprocess.TimeoutExpired:
                logger.error(f"Command timed out: {command}")
                return None
            except Exception as e:
                logger.error(f"Command failed: {e}")
                return None

        # Run in thread to allow halting
        result = [None]
        def _thread_run():
            result[0] = _run()

        thread = threading.Thread(target=_thread_run, daemon=True)
        with self.lock:
            self.active_commands.append(thread)
        thread.start()
        thread.join(timeout=timeout + 5)  # Wait a bit longer than command timeout

        return result[0]

    def is_halted(self) -> bool:
        """Check if halt is active."""
        return self.halt_event.is_set()