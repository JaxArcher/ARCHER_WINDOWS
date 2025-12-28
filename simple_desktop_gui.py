#!/usr/bin/env python3
"""
ARCHER Desktop GUI - Simple Version
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class SimpleARCHERGUI(QMainWindow):
    """Simple ARCHER Desktop GUI"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARCHER AI Assistant - Desktop")
        self.setGeometry(100, 100, 800, 600)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Title
        title = QLabel("ARCHER AI Assistant")
        title.setFont(QFont("Arial", 16))
        title.setStyleSheet("color: #2c3e50; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Input
        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Arial", 11))
        self.input_field.setPlaceholderText("Enter your command...")
        layout.addWidget(self.input_field)
        
        # Button
        self.send_btn = QPushButton("Send to ARCHER")
        self.send_btn.setFont(QFont("Arial", 10))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.send_btn.clicked.connect(self.on_send)
        layout.addWidget(self.send_btn)
        
        # Response area
        self.response_area = QTextEdit()
        self.response_area.setFont(QFont("Arial", 10))
        self.response_area.setReadOnly(True)
        layout.addWidget(self.response_area)
        
        # Status
        self.status_label = QLabel("ARCHER Ready")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setStyleSheet("color: #27ae60;")
        layout.addWidget(self.status_label)
        
        # Welcome message
        self.response_area.append("Welcome to ARCHER AI Assistant Desktop!")
        self.response_area.append("This is the native Windows desktop interface.")
        self.response_area.append("Enter commands above and click Send.")
        
        # Connect return key
        self.input_field.returnPressed.connect(self.on_send)
        
    def on_send(self):
        """Handle send button"""
        text = self.input_field.text().strip()
        if not text:
            return
            
        self.response_area.append(f"You: {text}")
        self.input_field.clear()
        
        # Simple response
        self.status_label.setText("Processing...")
        self.response_area.append(f"ARCHER: Processing '{text}'...")
        
        # Reset after delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.status_label.setText("ARCHER Ready"))

def main():
    app = QApplication(sys.argv)
    window = SimpleARCHERGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()