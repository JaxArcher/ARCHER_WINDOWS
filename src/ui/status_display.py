from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

class StatusDisplay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARCHER AI Assistant")
        self.setGeometry(100, 100, 800, 600)
        
        main_widget = QWidget()
        layout = QVBoxLayout()
        
        self.status_label = QLabel("ARCHER Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.info_label = QLabel("Voice pipeline active\nGUI interface ready")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)
        self.status_label.setText("ARCHER Online")
        
    def update_status(self, message):
        self.status_label.setText(message)
        
    def update_info(self, message):
        self.info_label.setText(message)