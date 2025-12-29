"""
Enhanced ARCHER GUI with 3D Orb Animation and Live Transcription
Includes input field, 4 quadrants, 3D orb, and live transcription display
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, 
    QFrame, QSizePolicy, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from .orb_animation import OrbAnimation
from src.events.bus import bus

class ARCHERGUI(QMainWindow):
    """Main ARCHER GUI with complete interface"""
    
    # Signals for inter-component communication
    user_input_submitted = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setWindowTitle("ARCHER AI Assistant")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Input area
        input_area = self._create_input_area()
        main_layout.addWidget(input_area)
        
        # Quadrant layout
        quadrants = self._create_quadrants()
        main_layout.addWidget(quadrants)
        
        # Status bar
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Initialize 3D orb animation
        self._init_orb_animation()
        
        # Connect signals
        self._connect_signals()
        
        # Initial status
        self.update_status("ARCHER Online - All systems operational")
        self.update_input_placeholder("Type your request here...")
        
        # Set initial orb state
        self.set_orb_state("idle")
    
    def _create_header(self):
        """Create header with title and version"""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 5px;
                padding: 15px;
            }
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("ARCHER AI Assistant")
        version_label = QLabel("v2.0")
        version_label.setStyleSheet("color: #ecf0f1; font-size: 16px;")
        
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(version_label)
        
        header_frame.setLayout(layout)
        return header_frame
    
    def _create_input_area(self):
        """Create input area with text field and button"""
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #2c3e50;
                border-radius: 5px;
                font-size: 16px;
                min-height: 40px;
            }
        """)
        self.input_field.setPlaceholderText("Type your request here...")
        self.input_field.returnPressed.connect(self._on_input_submitted)
        
        # Submit button
        submit_btn = QPushButton("Submit")
        submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        submit_btn.clicked.connect(self._on_input_submitted)
        
        layout.addWidget(self.input_field, 1)
        layout.addWidget(submit_btn)
        
        input_frame.setLayout(layout)
        return input_frame
    
    def _create_quadrants(self):
        """Create 4 quadrant layout"""
        quadrants_frame = QFrame()
        quadrants_frame.setFrameShape(QFrame.Shape.StyledPanel)
        quadrants_frame.setStyleSheet("""
            QFrame {
                background-color: #ecf0f1;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        
        # Main quadrant layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)
        
        # Top quadrants
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        
        # Quadrant 1: Voice Status
        q1_frame = self._create_quadrant("Voice Pipeline", "🎤 Active", "#3498db")
        top_layout.addWidget(q1_frame, 1)
        
        # Quadrant 2: Vision System with Orb Animation
        q2_frame = self._create_orb_quadrant()
        top_layout.addWidget(q2_frame, 1)
        
        # Bottom quadrants
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)
        
        # Quadrant 3: Memory Status
        q3_frame = self._create_quadrant("Memory", "🧠 Operational", "#2ecc71")
        bottom_layout.addWidget(q3_frame, 1)
        
        # Quadrant 4: Response Area with Live Transcription
        q4_frame = self._create_response_quadrant()
        bottom_layout.addWidget(q4_frame, 1)
        
        # Add live transcription display below response area
        transcription_frame = self._create_transcription_display()
        bottom_layout.addWidget(transcription_frame, 1)
        
        # Add layouts to main layout
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)
        
        quadrants_frame.setLayout(main_layout)
        return quadrants_frame
    
    def _create_quadrant(self, title, status, color):
        """Create individual quadrant widget"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 5px;
                border: 2px solid {color};
                padding: 15px;
            }}
            QLabel {{
                font-size: 14px;
            }}
            QLabel#title {{
                font-size: 16px;
                font-weight: bold;
                color: {color};
            }}
            QLabel#status {{
                font-size: 18px;
                font-weight: bold;
                color: {color};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        title_label = QLabel(title)
        title_label.setObjectName("title")
        
        status_label = QLabel(status)
        status_label.setObjectName("status")
        
        layout.addWidget(title_label)
        layout.addWidget(status_label)
        layout.addStretch()
        
        frame.setLayout(layout)
        return frame
    
    def _create_orb_quadrant(self):
        """Create quadrant with 3D orb animation"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 5px;
                border: 2px solid #e74c3c;
                padding: 15px;
            }
            QLabel#title {
                font-size: 16px;
                font-weight: bold;
                color: #e74c3c;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        title_label = QLabel("Vision System & Orb")
        title_label.setObjectName("title")
        layout.addWidget(title_label)
        
        # Add orb animation
        self.orb_animation = OrbAnimation()
        self.orb_animation.setMinimumSize(250, 250)
        self.orb_animation.setMaximumSize(350, 350)
        layout.addWidget(self.orb_animation, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Status label below orb
        self.orb_status_label = QLabel("Orb State: idle")
        self.orb_status_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        layout.addWidget(self.orb_status_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        frame.setLayout(layout)
        return frame
    
    def _init_orb_animation(self):
        """Initialize 3D orb animation - now handled in _create_orb_quadrant"""
        # Orb is now created in _create_orb_quadrant method
        # This method kept for backward compatibility
        pass
    
    def _create_response_quadrant(self):
        """Create response display quadrant"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 5px;
                border: 2px solid #f39c12;
                padding: 15px;
            }
            QLabel#title {
                font-size: 16px;
                font-weight: bold;
                color: #f39c12;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        title_label = QLabel("Response")
        title_label.setObjectName("title")
        
        self.response_area = QTextEdit()
        self.response_area.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 8px;
                font-size: 14px;
                background-color: #f9f9f9;
            }
        """)
        self.response_area.setReadOnly(True)
        self.response_area.setPlaceholderText("ARCHER responses will appear here...")
        
        layout.addWidget(title_label)
        layout.addWidget(self.response_area)
        
        frame.setLayout(layout)
        return frame
    
    def _create_transcription_display(self):
        """Create live transcription display"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 5px;
                border: 2px solid #9b59b6;
                padding: 15px;
                margin-top: 10px;
            }
            QLabel#title {
                font-size: 16px;
                font-weight: bold;
                color: #9b59b6;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        title_label = QLabel("Live Transcription")
        title_label.setObjectName("title")
        
        self.transcription_area = QTextEdit()
        self.transcription_area.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 8px;
                font-size: 14px;
                background-color: #f5f5f5;
                font-family: 'Courier New', monospace;
            }
        """)
        self.transcription_area.setReadOnly(True)
        self.transcription_area.setPlaceholderText("Live transcription will appear here when speaking...")
        
        layout.addWidget(title_label)
        layout.addWidget(self.transcription_area)
        
        frame.setLayout(layout)
        return frame
    
    def _create_status_bar(self):
        """Create status bar at bottom"""
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("ARCHER Online - All systems operational")
        self.status_label.setObjectName("status")
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        
        status_frame.setLayout(layout)
        return status_frame
    def _connect_signals(self):
        """Connect UI signals"""
        # Connect input field
        self.input_field.returnPressed.connect(self._on_input_submitted)
        
        # Subscribe to assistant responses
        bus.subscribe("assistant.response", self.add_response)
        
        # Subscribe to orb state changes
        bus.subscribe("orb.state", self.set_orb_state)
        
        # Subscribe to transcription updates
        bus.subscribe("transcription.update", self.add_transcription)
        bus.subscribe("transcription.clear", self.clear_transcription)
    
    def _on_input_submitted(self):
        """Handle user input submission"""
        user_input = self.input_field.text().strip()
        if user_input:
            # Emit signal for processing
            self.user_input_submitted.emit(user_input)
            
            # Add to response area
            self.response_area.append(f"You: {user_input}")
            self.response_area.append("")
            
            # Clear input
            self.input_field.clear()
            self.update_input_placeholder("Type your next request...")
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_label.setText(message)
    
    def update_input_placeholder(self, placeholder):
        """Update input field placeholder"""
        self.input_field.setPlaceholderText(placeholder)
    
    def add_response(self, response):
        """Add ARCHER response to display"""
        self.response_area.append(f"ARCHER: {response}")
        self.response_area.append("")
        # Auto-scroll to bottom
        self.response_area.verticalScrollBar().setValue(
            self.response_area.verticalScrollBar().maximum()
        )
    
    def set_orb_state(self, state):
        """
        Set the 3D orb state
        
        Args:
            state (str): One of 'idle', 'listening', 'thinking', 'speaking', 'error'
        """
        if hasattr(self, 'orb_animation'):
            self.orb_animation.set_state(state)
            
            # Update status bar to reflect orb state
            state_messages = {
                'idle': 'ARCHER Online - Idle',
                'listening': 'ARCHER Online - Listening...',
                'thinking': 'ARCHER Online - Processing...',
                'speaking': 'ARCHER Online - Speaking',
                'error': 'ARCHER Online - Error State'
            }
            
            if state in state_messages:
                self.update_status(state_messages[state])
            
            # Update orb status label
            if hasattr(self, 'orb_status_label'):
                self.orb_status_label.setText(f"Orb State: {state}")
    
    def get_orb_state(self):
        """Get current orb state"""
        if hasattr(self, 'orb_animation'):
            return self.orb_animation.get_state()
        return "idle"
    
    def add_transcription(self, text):
        """
        Add live transcription text
        
        Args:
            text (str): Transcription text to display
        """
        if hasattr(self, 'transcription_area'):
            self.transcription_area.append(text)
            # Auto-scroll to bottom
            self.transcription_area.verticalScrollBar().setValue(
                self.transcription_area.verticalScrollBar().maximum()
            )
    
    def clear_transcription(self):
        """Clear transcription display"""
        if hasattr(self, 'transcription_area'):
            self.transcription_area.clear()
    
    def update_quadrant_status(self, quadrant, status, color):
        """Update quadrant status"""
        # Implementation would update specific quadrant
        # This is a simplified version
        pass

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = ARCHERGUI()
    window.show()
    sys.exit(app.exec())
