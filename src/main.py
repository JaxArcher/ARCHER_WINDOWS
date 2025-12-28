"""
ARCHER Main Entry Point

Starts the voice pipeline and coordinates all system components.
"""

import logging
import sys
import os
import threading
import time
import re
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Apply torchaudio compatibility fix before any imports
try:
    import torchaudio

    # Add the missing attribute for compatibility
    def dummy_list_audio_backends():
        """Dummy implementation for compatibility with older SpeechBrain versions"""
        return []

    # Monkey patch torchaudio to add the missing function
    torchaudio.list_audio_backends = dummy_list_audio_backends
    logging.info("Applied torchaudio compatibility fix")
except ImportError:
    logging.warning("torchaudio not available, compatibility fix not applied")

# Initialize response handler early
import src.response_handler

from src.voice.voice_pipeline import VoicePipeline
from src.vision.observer import Observer
from src.memory.semantic_memory import SemanticMemory
from src.llm.router import LLMRouter
from src.agents import TherapistAgent, TrainerAgent, ProfileLearner
from src.agents.stock_expert import StockExpertAgent
from src.agents.rnd_agent import RNDAgent
from src.agents.assistant import AssistantAgent
from src.events.bus import bus


class PIIRedactionFilter(logging.Filter):
    """Filter to redact personally identifiable information from log messages."""

    def __init__(self):
        super().__init__()
        # Patterns for sensitive data
        self.patterns = {
            # Email addresses
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            # Phone numbers (various formats)
            "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
            # Social Security Numbers
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            # API keys (long alphanumeric strings, often with prefixes)
            "api_key": re.compile(
                r"\b(?:sk-|pk_|api_key|apikey|token|secret)[a-zA-Z0-9_-]{20,}\b",
                re.IGNORECASE,
            ),
            # IP addresses (IPv4)
            "ipv4": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
            # IPv6 (simplified)
            "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
            # User paths (Unix/Linux)
            "user_path_unix": re.compile(r"/home/[^/\s]+(?:/[^/\s]*)*"),
            # User paths (Windows)
            "user_path_win": re.compile(
                r"C:\\Users\\[^\\]+(?:\\[^\\]*)*", re.IGNORECASE
            ),
        }

    def filter(self, record):
        """Redact PII from the log message."""
        if hasattr(record, "msg"):
            record.msg = self._redact(record.msg)
        if hasattr(record, "getMessage"):
            # For cases where message is already formatted
            try:
                formatted = record.getMessage()
                record.msg = self._redact(formatted)
            except:
                pass
        return True

    def _redact(self, message):
        """Apply redaction patterns to the message."""
        if not isinstance(message, str):
            return message

        redacted = message
        for pattern_type, pattern in self.patterns.items():
            redacted = pattern.sub(f"[REDACTED_{pattern_type.upper()}]", redacted)

        return redacted


def setup_logging():
    """Configures the root logger with PII redaction."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create handlers
    file_handler = logging.FileHandler(log_dir / "archer.log")
    stream_handler = logging.StreamHandler()

    # Add PII redaction filter to both handlers
    pii_filter = PIIRedactionFilter()
    file_handler.addFilter(pii_filter)
    stream_handler.addFilter(pii_filter)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        handlers=[file_handler, stream_handler],
    )


def main():
    """Main entry point for ARCHER that can be called programmatically."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("ARCHER: Advanced Responsive Computing Helper & Executive Resource")
    logger.info("=" * 70)

    # Start health check server in background
    try:
        from src.health_check import app

        health_thread = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=5001, debug=False),
            daemon=True,
            name="HealthCheckServer",
        )
        health_thread.start()
        logger.info("Health check server started on port 5001")
    except Exception as e:
        logger.warning(f"Failed to start health check server: {e}")

    try:
        # Initialize core systems
        logger.info("Initializing ARCHER systems...")

        # Memory
        memory = SemanticMemory()
        logger.info("✓ Semantic memory loaded")

        # LLM Router
        llm = LLMRouter()
        logger.info("✓ LLM router initialized")

        # Agents
        profile_learner = ProfileLearner(memory)
        therapist = TherapistAgent(llm, memory)
        trainer = TrainerAgent(llm, memory)
        stock_expert = StockExpertAgent(llm, memory)
        rnd_agent = RNDAgent(llm, memory)
        assistant = AssistantAgent(llm, memory)
        logger.info("✓ Agents initialized")

        # Subscribe agents to events
        bus.subscribe(
            "vision.emotion.detected",
            lambda e: therapist.process_vision_event("vision.emotion.detected", e),
        )
        bus.subscribe(
            "vision.posture.bad",
            lambda e: therapist.process_vision_event("vision.posture.bad", e),
        )
        bus.subscribe(
            "vision.posture.bad",
            lambda e: trainer.process_vision_event("vision.posture.bad", e),
        )
        bus.subscribe(
            "vision.user.arrived",
            lambda e: trainer.process_vision_event("vision.user.arrived", e),
        )
        logger.info("✓ Event subscriptions configured")

        # Vision Observer (optional - only if camera available)
        vision_enabled = os.getenv("ENABLE_VISION", "false").lower() == "true"
        observer = None
        if vision_enabled:
            try:
                observer = Observer(frame_rate=1)
                observer.start()
                # Set observer in response handler for command processing
                import src.response_handler

                if src.response_handler.response_handler_instance:
                    src.response_handler.response_handler_instance.observer = observer
                logger.info("✓ Vision Observer started")
            except Exception as e:
                logger.warning(f"Vision Observer failed to start: {e}")
                logger.info("Continuing without vision...")
        else:
            logger.info("Vision Observer disabled (set ENABLE_VISION=true to enable)")

        # Launch VoicePipeline in background thread
        pipeline_thread = threading.Thread(
            target=lambda: VoicePipeline().start(),
            daemon=True,
            name="VoicePipelineThread",
        )
        pipeline_thread.start()
        logger.info("VoicePipeline started in background thread")

        # Launch GUI if enabled
        gui_enabled = os.getenv("ENABLE_GUI", "true").lower() == "true"
        if gui_enabled:
            try:
                logger.info("Launching GUI interface...")
                from PyQt6.QtWidgets import QApplication
                from src.ui.archer_gui import ARCHERGUI

                # Set offscreen platform if no display available
                if not os.environ.get("DISPLAY"):
                    os.environ["QT_QPA_PLATFORM"] = "offscreen"
                    logger.info("No display detected, using offscreen rendering")

                # Set Qt plugin path for Windows
                if os.name == "nt":
                    qt_plugin_path = os.path.join(
                        os.path.dirname(PyQt6.__file__), "Qt6", "plugins"
                    )
                    if os.path.exists(qt_plugin_path):
                        os.environ["QT_PLUGIN_PATH"] = qt_plugin_path

                # Create Qt application
                app = QApplication(sys.argv)

                # Set font fallback for missing fonts
                from PyQt6.QtGui import QFont

                app.setFont(QFont("Arial", 10))  # Use system font as fallback

                # Create and show main window
                main_window = ARCHERGUI()
                print("GUI created successfully")
                main_window.show()
                print("GUI shown")

                logger.info("GUI launched successfully")
                logger.info("ARCHER is now running with full voice and GUI interface")

                # Start Qt event loop (this will block)
                sys.exit(app.exec())

            except ImportError:
                logger.warning("PyQt6 not available, running in voice-only mode")
                # Keep running in voice-only mode
                logger.info("ARCHER running in voice-only mode. Press Ctrl+C to exit.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Shutting down...")
            except Exception as e:
                logger.warning(f"GUI launch failed: {e}")
                logger.info("Continuing in voice-only mode...")
                # Keep running in voice-only mode
                logger.info("ARCHER running in voice-only mode. Press Ctrl+C to exit.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Shutting down...")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
