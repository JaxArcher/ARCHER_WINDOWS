"""
Network Camera Support for ARCHER

Supports RTSP, HTTP, and IP camera streams for remote camera access.
Solves compatibility issues with local webcam drivers.
"""

import cv2
import threading
import logging
import time
import urllib.parse
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class NetworkCamera:
    """
    Network camera support for ARCHER with multiple protocol support.
    
    Supported protocols:
    - RTSP: rtsp://username:password@ip:port/stream
    - HTTP: http://username:password@ip:port/video
    - MJPEG: http://ip:port/video.mjpeg
    - ONVIF: via RTSP
    """
    
    def __init__(self, camera_url: str, **kwargs):
        """
        Initialize network camera connection.
        
        Args:
            camera_url: Full URL including authentication
            kwargs: Additional OpenCV parameters
        """
        self.camera_url = camera_url
        self.kwargs = kwargs
        self.cap = None
        self.lock = threading.Lock()
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0
        
        # Parse URL for authentication
        self.parsed_url = self._parse_camera_url(camera_url)
        
        logger.info(f"Initializing network camera: {self._redact_url(camera_url)}")
        
    def _parse_camera_url(self, url: str) -> Dict[str, Any]:
        """Parse camera URL for protocol, host, auth, etc."""
        parsed = urllib.parse.urlparse(url)
        
        result = {
            'protocol': parsed.scheme,
            'hostname': parsed.hostname,
            'port': parsed.port,
            'path': parsed.path,
            'username': None,
            'password': None
        }
        
        # Extract authentication
        if parsed.username:
            result['username'] = parsed.username
        if parsed.password:
            result['password'] = '*****'  # Redact for logging
        
        return result
        
    def _redact_url(self, url: str) -> str:
        """Redact sensitive information from URL for logging."""
        parsed = urllib.parse.urlparse(url)
        if parsed.username:
            # Reconstruct with redacted password
            netloc = parsed.netloc.split('@')[0] if '@' in parsed.netloc else parsed.netloc
            username = netloc.split(':')[0]
            return f"{parsed.scheme}://{username}:*****@{parsed.hostname}:{parsed.port}{parsed.path}"
        return url

    def connect(self) -> bool:
        """Establish connection to network camera."""
        with self.lock:
            if self.cap and self.cap.isOpened():
                logger.warning("Camera already connected")
                return True
                
            try:
                # Add buffer size for better stability
                self.kwargs['buffer_size'] = self.kwargs.get('buffer_size', 4096)
                
                logger.info(f"Connecting to {self._redact_url(self.camera_url)}")
                self.cap = cv2.VideoCapture(self.camera_url, **self.kwargs)
                
                if not self.cap.isOpened():
                    logger.error(f"Failed to connect to network camera: {self._redact_url(self.camera_url)}")
                    self.cap = None
                    return False
                    
                # Set optimal parameters for network streaming
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Test connection
                success, _ = self.cap.read()
                if not success:
                    logger.error("Camera connection established but no frames received")
                    self.cap.release()
                    self.cap = None
                    return False
                    
                self.is_connected = True
                self.reconnect_attempts = 0
                logger.info(f"Successfully connected to network camera: {self._redact_url(self.camera_url)}")
                
                # Log camera properties
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logger.info(f"Camera properties - FPS: {fps:.1f}, Resolution: {width}x{height}")
                
                return True
                
            except Exception as e:
                logger.error(f"Exception connecting to network camera: {e}")
                self.cap = None
                self.is_connected = False
                return False

    def disconnect(self):
        """Disconnect from network camera."""
        with self.lock:
            if self.cap:
                try:
                    self.cap.release()
                    logger.info("Network camera disconnected")
                except Exception as e:
                    logger.error(f"Error disconnecting camera: {e}")
                finally:
                    self.cap = None
                    self.is_connected = False

    def get_frame(self) -> Tuple[bool, Optional[cv2.typing.MatLike]]:
        """Get a frame from the network camera with automatic reconnection."""
        if not self.is_connected:
            if not self.connect():
                return False, None
                
        with self.lock:
            if not self.cap or not self.cap.isOpened():
                logger.warning("Camera not available")
                return False, None
                
            try:
                success, frame = self.cap.read()
                
                if not success:
                    logger.warning("Failed to read frame, attempting reconnection...")
                    self.disconnect()
                    if self.reconnect_attempts < self.max_reconnect_attempts:
                        self.reconnect_attempts += 1
                        time.sleep(self.reconnect_delay)
                        if self.connect():
                            # Try again after reconnect
                            return self.cap.read()
                    return False, None
                    
                # Reset reconnect counter on successful frame
                self.reconnect_attempts = 0
                return True, frame
                
            except Exception as e:
                logger.error(f"Exception reading frame: {e}")
                self.disconnect()
                return False, None

    def is_available(self) -> bool:
        """Check if camera is available."""
        return self.is_connected and self.cap is not None and self.cap.isOpened()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class NetworkCameraManager:
    """
    Manager for multiple network cameras with fallback support.
    """
    
    def __init__(self):
        self.cameras = {}
        self.current_camera = None
        self.lock = threading.Lock()
        
    def add_camera(self, camera_id: str, camera_url: str, **kwargs) -> bool:
        """Add a network camera to the manager."""
        with self.lock:
            if camera_id in self.cameras:
                logger.warning(f"Camera {camera_id} already exists")
                return False
                
            camera = NetworkCamera(camera_url, **kwargs)
            if camera.connect():
                self.cameras[camera_id] = camera
                logger.info(f"Added network camera {camera_id}")
                return True
            else:
                logger.error(f"Failed to add network camera {camera_id}")
                return False

    def set_active_camera(self, camera_id: str) -> bool:
        """Set the active camera."""
        with self.lock:
            if camera_id in self.cameras:
                self.current_camera = camera_id
                logger.info(f"Set active camera to {camera_id}")
                return True
            logger.error(f"Camera {camera_id} not found")
            return False

    def get_frame(self) -> Tuple[bool, Optional[cv2.typing.MatLike]]:
        """Get frame from active camera."""
        with self.lock:
            if not self.current_camera or self.current_camera not in self.cameras:
                logger.error("No active camera set")
                return False, None
                
            return self.cameras[self.current_camera].get_frame()

    def disconnect_all(self):
        """Disconnect all cameras."""
        with self.lock:
            for camera_id, camera in self.cameras.items():
                camera.disconnect()
            self.cameras.clear()
            self.current_camera = None
            logger.info("All network cameras disconnected")


# Common camera URL formats for reference
CAMERA_URL_EXAMPLES = {
    'rtsp_basic': 'rtsp://username:password@192.168.1.100:554/stream1',
    'rtsp_onvif': 'rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0',
    'http_mjpeg': 'http://192.168.1.102:8080/video.mjpeg',
    'http_h264': 'http://username:password@192.168.1.103:8080/video',
    'axis_camera': 'http://root:password@192.168.1.104/axis-cgi/mjpg/video.cgi',
    'dahua': 'rtsp://admin:password@192.168.1.105:554/cam/realmonitor?channel=1&subtype=0',
    'hikvision': 'rtsp://admin:password@192.168.1.106:554/Streaming/Channels/101'
}