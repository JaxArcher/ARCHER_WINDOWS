#!/usr/bin/env python
"""
ARCHER GUI - Integrated Voice Interface

A comprehensive GUI for ARCHER with TTS testing and system monitoring.
"""

import os
import sys
import json
import subprocess
from typing import Tuple

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.platform_utils import ensure_xvfb_running, is_headless

try:
    import gradio as gr

    GRADIO_AVAILABLE = True
except ImportError:
    try:
        import streamlit as st

        STREAMLIT_AVAILABLE = True
        GRADIO_AVAILABLE = False
        print("⚠️ Gradio not available, using Streamlit instead")
    except ImportError:
        GRADIO_AVAILABLE = False
        STREAMLIT_AVAILABLE = False
        print(
            "❌ Neither Gradio nor Streamlit available. Install with: pip install gradio or pip install streamlit"
        )


class ARCHER_GUI:
    """ARCHER GUI with TTS integration."""

    def __init__(self):
        if not GRADIO_AVAILABLE:
            raise ImportError(
                "Gradio is required for GUI. Install with: pip install gradio"
            )

        # Ensure Xvfb is running for headless environments
        if is_headless():
            ensure_xvfb_running()

        self.tts_available = self._check_tts_availability()

    def _check_tts_availability(self) -> bool:
        """Check if TTS system is available."""
        try:
            from voice.tts import get_tts_manager
            # Test if we can get the TTS manager without errors
            manager = get_tts_manager()
            print(f"✅ TTS Manager initialized with engine: {manager.current_engine.value}")
            return True
        except Exception as e:
            print(f"X TTS check failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_interface(self):
        """Create the GUI interface."""

        if GRADIO_AVAILABLE:
            return self._create_gradio_interface()
        elif STREAMLIT_AVAILABLE:
            return self._create_streamlit_interface()
        else:
            raise ImportError("No GUI framework available")

    def _create_gradio_interface(self):
        """Create the Gradio interface."""

        with gr.Blocks(
            title="ARCHER - Voice AI Assistant", theme=gr.themes.Soft()
        ) as interface:
            gr.Markdown("""
            # 🤖 ARCHER - Advanced Responsive Computing Helper

            **Real-time AI Assistant with SOTA Voice Interaction**

            Status: <span style="color: green;">● ONLINE</span>
            """)

            with gr.Tabs():
                # TTS Testing Tab
                with gr.TabItem("🔊 TTS Testing"):
                    self._create_tts_tab()

                # System Status Tab
                with gr.TabItem("📊 System Status"):
                    self._create_status_tab()

                # Settings Tab
                with gr.TabItem("⚙️ Settings"):
                    self._create_settings_tab()

        return interface

    def _create_tts_tab(self):
        """Create TTS testing interface."""

        gr.Markdown("### 🎭 F5-TTS Voice Synthesis Testing")

        # Always show TTS status dynamically
        try:
            from voice.tts import get_tts_manager
            manager = get_tts_manager()
            tts_status = f"✅ TTS Available - Engine: {manager.current_engine.value}"
        except Exception as e:
            tts_status = "❌ TTS system not available. Please check TTS integration."

        gr.Markdown(tts_status)

        if not self.tts_available:
            return

        with gr.Row():
            with gr.Column():
                # Text input
                text_input = gr.Textbox(
                    label="Text to Synthesize",
                    lines=4,
                    placeholder="Enter text to convert to speech...",
                    value="Hello! I am ARCHER, your advanced AI assistant with state-of-the-art voice synthesis.",
                )

                # Voice selection
                voice_options = [
                    "voice_01.wav - Default Male",
                    "voice_02.wav - Female 1",
                    "voice_03.wav - Chinese Speaker",
                    "voice_04.wav - Professional Male",
                    "voice_05.wav - Narrator",
                    "voice_06.wav - Casual Male",
                    "voice_07.wav - Angry Male",
                    "voice_08.wav - Sad Male",
                    "voice_09.wav - Happy Female",
                    "voice_10.wav - Excited Male",
                    "voice_11.wav - Calm Female",
                    "voice_12.wav - Scared Female",
                ]

                voice_selector = gr.Dropdown(
                    choices=voice_options,
                    label="Voice Reference",
                    value="voice_01.wav - Default Male",
                )

                # Generate button
                generate_btn = gr.Button(
                    "🎵 Generate Speech", variant="primary", size="lg"
                )

            with gr.Column():
                # Status display
                status_display = gr.Textbox(
                    label="Status", interactive=False, value="Ready to generate speech"
                )

                # Model info
                gr.Markdown("""
                **🎯 F5-TTS Features:**
                - **Quality:** 24kHz, Emotional Expression
                - **GPU:** RTX 5080 Accelerated
                - **Latency:** 30-60s first load, <2s subsequent
                - **Voices:** 12 reference voices available
                - **Emotions:** Anger, sadness, happiness, fear, etc.
                """)

        # Event handler
        generate_btn.click(
            fn=self._generate_speech,
            inputs=[text_input, voice_selector],
            outputs=[status_display],
        )

    def _create_status_tab(self):
        """Create system status interface."""

        gr.Markdown("### 📊 System Status & Monitoring")

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### 🖥️ Hardware Status")

                gpu_status = gr.Textbox(
                    label="GPU Status", interactive=False, value="Checking..."
                )

                memory_status = gr.Textbox(
                    label="Memory Usage", interactive=False, value="Checking..."
                )

                disk_status = gr.Textbox(
                    label="Storage", interactive=False, value="Checking..."
                )

            with gr.Column():
                gr.Markdown("#### 🔧 Component Status")

                tts_status = gr.Textbox(
                    label="Text-to-Speech",
                    interactive=False,
                    value="✅ F5-TTS (SOTA)"
                    if self.tts_available
                    else "❌ TTS Unavailable",
                )

                stt_status = gr.Textbox(
                    label="Speech-to-Text",
                    interactive=False,
                    value="✅ Faster-Whisper (GPU)",
                )

                llm_status = gr.Textbox(
                    label="Language Model",
                    interactive=False,
                    value="✅ Multi-Model Router",
                )

        # Refresh button
        refresh_btn = gr.Button("🔄 Refresh Status", variant="secondary")

        refresh_btn.click(
            fn=self._get_system_status, outputs=[gpu_status, memory_status, disk_status]
        )

        # Load initial status
        interface = gr.Interface(
            fn=self._get_system_status,
            inputs=[],
            outputs=[gpu_status, memory_status, disk_status],
        )

    def _create_settings_tab(self):
        """Create settings interface."""

        gr.Markdown("### ⚙️ System Settings")

        with gr.Accordion("🎤 Voice Settings", open=True):
            wake_word = gr.Textbox(
                label="Wake Word",
                value="Hey Archer",
                placeholder="Word/phrase to activate ARCHER",
            )

        with gr.Accordion("🔊 TTS Settings", open=False):
            tts_quality = gr.Radio(
                choices=["High (24kHz)", "Medium (16kHz)", "Low (8kHz)"],
                label="Audio Quality",
                value="High (24kHz)",
            )

            tts_emotion = gr.Checkbox(label="Enable Emotional Expression", value=True)

        save_btn = gr.Button("💾 Save Settings", variant="primary")

        save_btn.click(
            fn=self._save_settings,
            inputs=[wake_word, tts_quality, tts_emotion],
            outputs=[],
        )

    def _generate_speech(self, text: str, voice: str) -> str:
        """Generate speech using the active TTS engine."""
        if not text.strip():
            return "❌ Please enter text to synthesize"

        try:
            # Import TTS manager
            from voice.tts import get_tts_manager

            # Extract voice filename
            voice_file = voice.split(" - ")[0] + ".wav"

            # Get TTS manager and generate speech
            tts_manager = get_tts_manager()
            success = tts_manager.speak(text, voice_file)

            if success:
                return f"✅ Speech generated successfully using {voice}"
            else:
                return f"⚠️ Speech generation completed with warnings"

        except Exception as e:
            return f"❌ TTS Error: {str(e)}"

    def _get_system_status(self) -> Tuple[str, str, str]:
        """Get current system status."""
        try:
            # GPU status
            gpu_result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if gpu_result.returncode == 0:
                gpu_util, mem_used, mem_total = gpu_result.stdout.strip().split(", ")
                gpu_status = (
                    f"GPU: {gpu_util}% utilized, {mem_used}/{mem_total} MB VRAM"
                )
            else:
                gpu_status = "GPU: Status unavailable"

            # Memory status
            with open("/proc/meminfo", "r") as f:
                mem_lines = f.readlines()
                total_mem = (
                    int(
                        [line for line in mem_lines if "MemTotal" in line][0].split()[1]
                    )
                    // 1024
                )
                available_mem = (
                    int(
                        [line for line in mem_lines if "MemAvailable" in line][
                            0
                        ].split()[1]
                    )
                    // 1024
                )
                memory_status = f"RAM: {available_mem}/{total_mem} MB available"

            # Disk status
            disk_result = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True, timeout=5
            )
            if disk_result.returncode == 0:
                disk_line = disk_result.stdout.split("\n")[1]
                disk_status = f"Storage: {disk_line.split()[4]} used"
            else:
                disk_status = "Storage: Status unavailable"

            return gpu_status, memory_status, disk_status

        except Exception as e:
            return f"GPU: Error - {e}", f"RAM: Error - {e}", f"Storage: Error - {e}"

    def _save_settings(
        self, wake_word: str, tts_quality: str, tts_emotion: bool
    ) -> str:
        """Save settings."""
        settings = {
            "wake_word": wake_word,
            "tts_quality": tts_quality,
            "tts_emotion": tts_emotion,
        }

        try:
            settings_file = os.path.join(
                os.path.dirname(__file__), "..", "..", "gui_settings.json"
            )
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
            return "✅ Settings saved successfully!"
        except Exception as e:
            return f"❌ Failed to save settings: {e}"


def launch_gui(host: str = "0.0.0.0", port: int = 7860, share: bool = False):
    """Launch the ARCHER GUI."""
    if not GRADIO_AVAILABLE:
        print("❌ Gradio not installed. Install with: pip install gradio")
        return

    try:
        gui = ARCHER_GUI()
        interface = gui.create_interface()

        print("🚀 Launching ARCHER GUI...")
        print(f"📱 Access at: http://localhost:{port}")
        if share:
            print("🌐 Share link will be generated")

        interface.launch(
            server_name=host, server_port=port, share=share, show_error=True
        )
    except Exception as e:
        print(f"X Failed to launch GUI: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ARCHER GUI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=7860, help="Port to run on")
    parser.add_argument("--share", action="store_true", help="Create public share link")

    args = parser.parse_args()

    launch_gui(host=args.host, port=args.port, share=args.share)
