import cv2
import threading
import logging
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)

class CameraManager:
    _instance = None
    _lock = threading.Lock()
    _capture: Optional[cv2.VideoCapture] = None
    _camera_index: int = 0
    _camera_url: Optional[str] = None
    _is_network_camera: bool = False

    def __new__(cls, camera_index: Union[int, str] = 0):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CameraManager, cls).__new__(cls)
                    # Handle both local camera index and network camera URL
                    if isinstance(camera_index, str):
                        cls._camera_url = camera_index
                        cls._is_network_camera = True
                        cls._camera_index = 0
                    else:
                        cls._camera_index = camera_index
                        cls._is_network_camera = False
        return cls._instance

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self) -> bool:
        """Acquires and initializes the camera resource."""
        with self._lock:
            if self._capture is None:
                if self._is_network_camera:
                    # Network camera
                    self._capture = cv2.VideoCapture(self._camera_url)
                    if not self._capture.isOpened():
                        logger.error(f"Failed to open network camera: {self._camera_url}")
                        self._capture = None
                        return False
                    logger.info(f"Network camera acquired successfully: {self._camera_url}")
                else:
                    # Local camera
                    self._capture = cv2.VideoCapture(self._camera_index)
                    if not self._capture.isOpened():
                        logger.error(f"Failed to open camera at index {self._camera_index}.")
                        self._capture = None
                        return False
                    logger.info(f"Camera {self._camera_index} acquired successfully.")
                return True
            logger.warning("Camera already acquired. Ignoring request.")
            return True

    def release(self):
        """Releases the camera resource."""
        with self._lock:
            if self._capture is not None:
                self._capture.release()
                self._capture = None
                logger.info(f"Camera {self._camera_index} released.")

    def get_frame(self) -> Tuple[bool, Optional[cv2.typing.MatLike]]:
        """Reads a single frame from the acquired camera."""
        with self._lock:
            if self._capture and self._capture.isOpened():
                return self._capture.read()
            else:
                logger.warning("Attempted to get frame, but camera is not acquired.")
                return False, None