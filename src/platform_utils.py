"""
ARCHER Platform Utilities
Unified platform abstraction layer for cross-platform compatibility.

Handles platform detection, audio playback, file paths, and GUI initialization
across Windows, Linux, and WSL environments.
"""

import os
import sys
import platform
import subprocess
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PlatformInfo:
    """Platform information and capabilities."""

    def __init__(self):
        self.system = self._detect_platform()
        self.is_windows = self.system == "windows"
        self.is_linux = self.system == "linux"
        self.is_wsl = self.system == "wsl"
        self.is_headless = self._detect_headless()
        self.has_gui = not self.is_headless
        self.audio_backends = self._detect_audio_backends()

    def _detect_platform(self) -> str:
        """Detect the current platform with WSL support."""
        system = platform.system().lower()

        if system == "windows":
            return "windows"
        elif system == "linux":
            # Check for WSL
            try:
                with open("/proc/version", "r") as f:
                    version = f.read().lower()
                    if "microsoft" in version or "wsl" in version:
                        return "wsl"
            except FileNotFoundError:
                pass

            # Check kernel release for WSL2
            try:
                with open("/proc/sys/kernel/osrelease", "r") as f:
                    if "microsoft" in f.read().lower():
                        return "wsl"
            except FileNotFoundError:
                pass

            return "linux"
        else:
            return "unknown"

    def _detect_headless(self) -> bool:
        """Detect if running in headless environment."""
        # Check DISPLAY variable
        display = os.environ.get("DISPLAY")
        if not display:
            return True

        # Check for X11/Wayland
        try:
            if self.is_linux or self.is_wsl:
                # Try to connect to X server
                result = subprocess.run(
                    ["xdpyinfo", "-display", display], capture_output=True, timeout=5
                )
                return result.returncode != 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def _detect_audio_backends(self) -> list:
        """Detect available audio backends."""
        backends = []

        # Check sounddevice
        try:
            import sounddevice as sd

            backends.append("sounddevice")
        except ImportError:
            pass

        # Check pygame
        try:
            import pygame

            backends.append("pygame")
        except ImportError:
            pass

        # Windows-specific
        if self.is_windows:
            backends.append("powershell")

        # Linux/WSL audio
        if self.is_linux or self.is_wsl:
            backends.extend(["alsa", "pulseaudio"])

        return backends


# Global platform info instance
platform_info = PlatformInfo()


def get_platform() -> str:
    """Get current platform string."""
    return platform_info.system


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform_info.is_windows


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform_info.is_linux


def is_wsl() -> bool:
    """Check if running on WSL."""
    return platform_info.is_wsl


def is_headless() -> bool:
    """Check if running in headless environment."""
    return platform_info.is_headless


def has_gui() -> bool:
    """Check if GUI is available."""
    return platform_info.has_gui


def get_audio_backends() -> list:
    """Get available audio backends."""
    return platform_info.audio_backends


def play_audio_file(file_path: str, backend: Optional[str] = None) -> bool:
    """
    Play audio file using best available backend for current platform.

    Args:
        file_path: Path to audio file
        backend: Specific backend to use (optional)

    Returns:
        bool: Success status
    """
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        return False

    # Select backend
    if backend and backend in platform_info.audio_backends:
        selected_backend = backend
    else:
        # Priority order
        priority = ["sounddevice", "pygame", "powershell", "alsa", "pulseaudio"]
        selected_backend = None
        for b in priority:
            if b in platform_info.audio_backends:
                selected_backend = b
                break

    if not selected_backend:
        logger.error("No audio backend available")
        return False

    try:
        if selected_backend == "sounddevice":
            return _play_sounddevice(file_path)
        elif selected_backend == "pygame":
            return _play_pygame(file_path)
        elif selected_backend == "powershell":
            return _play_powershell(file_path)
        elif selected_backend in ["alsa", "pulseaudio"]:
            return _play_linux_audio(file_path, selected_backend)
        else:
            logger.error(f"Unsupported audio backend: {selected_backend}")
            return False
    except Exception as e:
        logger.error(f"Audio playback failed with {selected_backend}: {e}")
        return False


def _play_sounddevice(file_path: str) -> bool:
    """Play audio using sounddevice."""
    import sounddevice as sd
    import soundfile as sf

    data, samplerate = sf.read(file_path)
    sd.play(data, samplerate)
    sd.wait()
    return True


def _play_pygame(file_path: str) -> bool:
    """Play audio using pygame."""
    import pygame

    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)
    pygame.mixer.quit()
    return True


def _play_powershell(file_path: str) -> bool:
    """Play audio using Windows PowerShell."""
    cmd = [
        "powershell.exe",
        "-c",
        f'(New-Object Media.SoundPlayer "{file_path}").PlaySync();',
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def _play_linux_audio(file_path: str, backend: str) -> bool:
    """Play audio on Linux using aplay or paplay."""
    if backend == "alsa":
        cmd = ["aplay", file_path]
    else:  # pulseaudio
        cmd = ["paplay", file_path]

    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def normalize_path(path: str) -> str:
    """
    Normalize file path for current platform.

    Args:
        path: File path string

    Returns:
        Normalized path string
    """
    if platform_info.is_windows:
        return path.replace("/", "\\")
    else:
        return path.replace("\\", "/")


def ensure_xvfb_running(
    display_num: int = 99, resolution: str = "1920x1080x24"
) -> bool:
    """
    Ensure Xvfb is running for headless GUI operations.

    Args:
        display_num: Display number to use
        resolution: Screen resolution

    Returns:
        bool: Success status
    """
    if not (platform_info.is_linux or platform_info.is_wsl):
        return True  # Not needed on Windows

    if not platform_info.is_headless:
        return True  # GUI already available

    # Check if Xvfb is already running
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"Xvfb.*:{display_num}"], capture_output=True
        )
        if result.returncode == 0:
            logger.info(f"Xvfb already running on :{display_num}")
            return True
    except FileNotFoundError:
        pass

    # Start Xvfb
    try:
        cmd = [
            "Xvfb",
            f":{display_num}",
            "-screen",
            "0",
            resolution,
            "-ac",
            "+extension",
            "GLX",
            "+render",
            "-noreset",
        ]

        logger.info(f"Starting Xvfb: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Wait a moment for startup
        import time

        time.sleep(2)

        # Set DISPLAY
        os.environ["DISPLAY"] = f":{display_num}"

        # Ensure socket permissions
        socket_dir = f"/tmp/.X11-unix"
        if os.path.exists(socket_dir):
            os.chmod(socket_dir, 0o1777)

        logger.info(f"Xvfb started successfully on :{display_num}")
        return True

    except Exception as e:
        logger.error(f"Failed to start Xvfb: {e}")
        return False


def get_gpu_info() -> Dict[str, Any]:
    """
    Get GPU information and memory usage.

    Returns:
        Dict with GPU information
    """
    info = {
        "available": False,
        "count": 0,
        "memory_used": 0,
        "memory_total": 0,
        "utilization": 0,
    }

    try:
        import torch

        if torch.cuda.is_available():
            info["available"] = True
            info["count"] = torch.cuda.device_count()

            if info["count"] > 0:
                # Get memory info for device 0
                info["memory_used"] = (
                    torch.cuda.mem_get_info()[1] - torch.cuda.mem_get_info()[0]
                )
                info["memory_total"] = torch.cuda.mem_get_info()[1]

                # Get utilization (approximate)
                try:
                    props = torch.cuda.get_device_properties(0)
                    info["name"] = props.name
                except:
                    pass

    except ImportError:
        pass

    return info
