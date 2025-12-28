"""
3D Orb Animation for ARCHER GUI
Uses PyVista for interactive 3D visualization
"""

import numpy as np
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer
import pyvista as pv
from pyvistaqt import QtInteractor

class OrbAnimation(QWidget):
    """
    3D Orb Animation Widget
    
    Features:
    - Animated 3D sphere representing ARCHER state
    - Color-coded states: Idle, Listening, Thinking, Speaking
    - Pulsing animation effects
    - Real-time state updates
    """
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create PyVista plotter
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor)
        
        # Orb parameters
        self.radius = 1.0
        self.resolution = 50
        self.current_state = "idle"
        self.state_colors = {
            "idle": "#808080",      # Gray
            "listening": "#3498db",  # Blue
            "thinking": "#f39c12",   # Orange
            "speaking": "#2ecc71",   # Green
            "error": "#e74c3c"       # Red
        }
        
        # Animation parameters
        self.pulse_amplitude = 0.1
        self.pulse_speed = 0.05
        self.pulse_direction = 1
        self.pulse_offset = 0
        
        # Create orb
        self.orb = pv.Sphere(radius=self.radius, theta_resolution=self.resolution, phi_resolution=self.resolution)
        
        # Add orb to plotter
        self.actor = self.plotter.add_mesh(
            self.orb, 
            color=self.state_colors[self.current_state],
            specular=0.5,
            specular_power=30,
            smooth_shading=True
        )
        
        # Camera setup
        self.plotter.camera_position = 'xy'
        self.plotter.set_background('white')
        self.plotter.disable()  # Disable interactive controls for animation
        
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(50)  # ~20 FPS
        
        # Initial render
        self._update_orb_appearance()
    
    def _update_animation(self):
        """Update animation frame"""
        # Pulsing effect
        self.pulse_offset += self.pulse_speed * self.pulse_direction
        
        if self.pulse_offset > self.pulse_amplitude:
            self.pulse_offset = self.pulse_amplitude
            self.pulse_direction = -1
        elif self.pulse_offset < -self.pulse_amplitude:
            self.pulse_offset = -self.pulse_amplitude
            self.pulse_direction = 1
        
        # Update orb size
        current_radius = self.radius + self.pulse_offset
        self.orb.radius = current_radius
        
        # Update mesh
        self.actor.SetScale(current_radius, current_radius, current_radius)
        
        # Refresh plotter
        self.plotter.update()
    
    def _update_orb_appearance(self):
        """Update orb appearance based on current state"""
        color = self.state_colors.get(self.current_state, "#808080")
        self.actor.SetColor(color)
        
        # State-specific animation parameters
        if self.current_state == "idle":
            self.pulse_amplitude = 0.05
            self.pulse_speed = 0.03
        elif self.current_state == "listening":
            self.pulse_amplitude = 0.15
            self.pulse_speed = 0.08
        elif self.current_state == "thinking":
            self.pulse_amplitude = 0.10
            self.pulse_speed = 0.10
        elif self.current_state == "speaking":
            self.pulse_amplitude = 0.12
            self.pulse_speed = 0.06
        elif self.current_state == "error":
            self.pulse_amplitude = 0.20
            self.pulse_speed = 0.15
    
    def set_state(self, state):
        """
        Set orb state
        
        Args:
            state (str): One of 'idle', 'listening', 'thinking', 'speaking', 'error'
        """
        if state in self.state_colors:
            self.current_state = state
            self._update_orb_appearance()
    
    def get_state(self):
        """Get current orb state"""
        return self.current_state
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'animation_timer') and self.animation_timer.isActive():
            self.animation_timer.stop()
        super().close()

class OrbAnimationWidget:
    """
    Wrapper class for easier integration with main GUI
    """
    
    def __init__(self):
        self.widget = OrbAnimation()
    
    def get_widget(self):
        """Get the QWidget for integration"""
        return self.widget
    
    def set_state(self, state):
        """Set orb state"""
        self.widget.set_state(state)
    
    def get_state(self):
        """Get current state"""
        return self.widget.get_state()

# Test the orb animation
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create and show orb
    orb = OrbAnimation()
    orb.show()
    
    # Test state changes
    def test_states():
        import time
        states = ["idle", "listening", "thinking", "speaking", "error"]
        for state in states:
            print(f"Setting state to: {state}")
            orb.set_state(state)
            time.sleep(2)
    
    # Start state testing in background
    import threading
    threading.Thread(target=test_states, daemon=True).start()
    
    sys.exit(app.exec())