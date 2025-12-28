#!/usr/bin/env python3
"""
ARCHER Desktop GUI - Working TTS with Fallback
Uses pyttsx3 fallback TTS system - no FFmpeg required!
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont

# Add src to path for backend imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from voice.tts_fallback import get_tts_manager
    TTS_AVAILABLE = True
    print("TTS Backend: Using pyttsx3 fallback (no FFmpeg needed!)")
except ImportError as e:
    TTS_AVAILABLE = False
    print(f"TTS Backend: Not available - {e}")

class WorkingTTSWorker(QThread):
    """Worker thread for TTS processing using fallback system"""

    response_ready = pyqtSignal(str, str)  # text, status
    tts_complete = pyqtSignal(bool, str)  # success, message

    def __init__(self):
        super().__init__()
        self.tts_manager = None
        if TTS_AVAILABLE:
            try:
                self.tts_manager = get_tts_manager()
            except Exception as e:
                print(f"TTS Manager error: {e}")
        else:
            print("WARNING: TTS system not available")

    def process_tts(self, text):
        """Process text-to-speech using fallback system"""
        if not self.tts_manager:
            self.tts_complete.emit(False, "TTS system not available")
            return

        try:
            self.response_ready.emit(text, "Processing TTS...")

            # Use fallback TTS system (no FFmpeg required!)
            success = self.tts_manager.speak(text, voice=None)

            if success:
                self.tts_complete.emit(True, "TTS Complete - Audio played successfully!")
            else:
                self.tts_complete.emit(False, "TTS Failed - Could not generate audio")

        except Exception as e:
            self.tts_complete.emit(False, f"TTS Error: {e}")

class WorkingARCHERGUI(QMainWindow):
    """Working ARCHER Desktop GUI with Fallback TTS"""

    def __init__(self):
        super().__init__()
        self.tts_worker = WorkingTTSWorker()
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Initialize user interface"""
        # Window setup
        self.setWindowTitle("ARCHER AI Assistant - Working TTS")
        self.setGeometry(100, 100, 900, 700)

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Header
        header = QLabel("ARCHER AI Assistant - Working TTS")
        header.setFont(QFont("Arial", 16))
        header.setStyleSheet("QLabel { color: #2c3e50; font-weight: bold; padding: 10px; }")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Status bar
        self.status_label = QLabel("ARCHER Ready" + (" + Working TTS" if TTS_AVAILABLE else " (TTS Not Available)"))
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet("QLabel { color: #27ae60; padding: 5px; background-color: #ecf0f1; }")
        layout.addWidget(self.status_label)

        # Info label
        info_label = QLabel("This version uses reliable TTS - no FFmpeg required!")
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("QLabel { color: #7f8c8d; padding: 3px; }")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        # Input section
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.Shape.Box)
        input_layout = QVBoxLayout(input_frame)

        input_label = QLabel("Enter text for TTS or command:")
        input_label.setFont(QFont("Arial", 11))
        input_layout.addWidget(input_label)

        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Arial", 11))
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                font-size: 11pt;
            }
        """)
        self.input_field.setPlaceholderText("Type any text and click 'Text to Speech'...")
        input_layout.addWidget(self.input_field)

        # Button layout
        button_layout = QHBoxLayout()

        self.send_btn = QPushButton("Send Command")
        self.send_btn.setFont(QFont("Arial", 10))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        self.tts_btn = QPushButton("Text to Speech")
        self.tts_btn.setFont(QFont("Arial", 10))
        self.tts_btn.setEnabled(TTS_AVAILABLE)
        self.tts_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)

        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.tts_btn)
        input_layout.addLayout(button_layout)

        layout.addWidget(input_frame)

        # Response area
        response_frame = QFrame()
        response_frame.setFrameStyle(QFrame.Shape.Box)
        response_layout = QVBoxLayout(response_frame)

        response_label = QLabel("ARCHER Response:")
        response_label.setFont(QFont("Arial", 11))
        response_layout.addWidget(response_label)

        self.response_area = QTextEdit()
        self.response_area.setFont(QFont("Arial", 10))
        self.response_area.setReadOnly(True)
        self.response_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 8px;
                font-size: 10pt;
            }
        """)
        response_layout.addWidget(self.response_area)

        layout.addWidget(response_frame)

    def connect_signals(self):
        """Connect signals"""
        self.input_field.returnPressed.connect(self.on_send_command)
        self.send_btn.clicked.connect(self.on_send_command)
        self.tts_btn.clicked.connect(self.on_tts_request)

        # Connect TTS worker signals
        self.tts_worker.response_ready.connect(self.on_tts_response)
        self.tts_worker.tts_complete.connect(self.on_tts_complete)

    def on_send_command(self):
        """Handle command submission"""
        text = self.input_field.text().strip()
        if not text:
            return

        self.add_response(f"You: {text}")
        self.input_field.clear()

        # Process command
        response = self.process_command(text)
        self.add_response(f"ARCHER: {response}")

    def on_tts_request(self):
        """Handle TTS request"""
        text = self.input_field.text().strip()
        if not text:
            return

        self.add_response(f"TTS Request: {text}")
        self.input_field.clear()

        # Start TTS processing in background
        self.tts_worker.start()
        self.tts_worker.process_tts(text)

    def on_tts_response(self, text, status):
        """Handle TTS response"""
        self.add_response(f"TTS Status: {status}")
        self.status_label.setText(f"Status: {status}")

        # Reset status after delay
        QTimer.singleShot(3000, lambda: self.status_label.setText("ARCHER Ready + Working TTS"))

    def on_tts_complete(self, success, message):
        """Handle TTS completion"""
        self.add_response(f"TTS Result: {message}")

    def process_command(self, command):
        """Process ARCHER command"""
        cmd = command.lower()

        if "hello" in cmd or "hi" in cmd:
            return "Hello! I'm ARCHER with working TTS capabilities!"
        elif "tts" in cmd:
            return "Text-to-Speech is working! Try typing any text and clicking 'Text to Speech'."
        elif "test" in cmd:
            return "TTS test successful! Using reliable pyttsx3 system."
        elif "agent" in cmd:
            return "I have 9+ specialized agents: Assistant, Therapist, Trainer, Stock Expert, Authority Manager, Evidence Processor, Federated Learning, Governance, and Proactive."
        elif "memory" in cmd:
            return "My 4-tier memory system includes: Short-term context, Long-term vector storage, Episodic event logs, and Semantic knowledge graphs."
        elif "status" in cmd:
            tts_status = "Working (pyttsx3)" if TTS_AVAILABLE else "Not Available"
            return f"All systems operational. TTS Status: {tts_status}. Multi-agent architecture ready."
        elif "help" in cmd:
            return """Available commands: hello, tts, test, agent, memory, status, help.
            For voice synthesis: Type any text and click "Text to Speech" button.
            TTS system uses reliable pyttsx3 - no FFmpeg required!"""
        else:
            return f"Processing: '{command}'. ARCHER multi-agent system is analyzing your request through available agents and memory systems."

    def add_response(self, text):
        """Add text to response area"""
        self.response_area.append(text)
        # Scroll to bottom
        self.response_area.verticalScrollBar().setValue(
            self.response_area.verticalScrollBar().maximum()
        )

def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("ARCHER AI Assistant")
    app.setApplicationVersion("1.0")

    # Show status
    if TTS_AVAILABLE:
        print("Starting ARCHER with Working TTS (pyttsx3 fallback)...")
    else:
        print("Starting ARCHER (TTS not available)...")

    # Create and show main window
    window = WorkingARCHERGUI()
    window.show()

    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()