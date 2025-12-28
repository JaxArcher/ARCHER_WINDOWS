"""
ARCHER Voice Pipeline - End-to-End Conversational Loop.

Implements the complete state machine for voice interaction:
IDLE → LISTENING → PROCESSING → SPEAKING → IDLE

Integrates: Wake Word, VAD, STT, LLM, TTS, Fillers
"""

import os
import logging
import sounddevice as sd
import numpy as np
import threading
import time
from enum import Enum
from dotenv import load_dotenv

from .wake_word import WakeWordDetector
from .voice_auth import VoiceAuthenticator
from .vad import VadGate
from .stt import SpeechToText
from .audio_buffer import AudioBuffer
from .fillers import FillerPlayer
from .tts import TTSManager as TTSEngine
from src.llm.router import LLMRouter
from src.events.bus import bus
from src.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """Voice pipeline states."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class VoicePipeline:
    """
    End-to-end voice interaction pipeline for ARCHER.

    Manages state transitions and coordinates all voice components.
    """

    def __init__(self):
        """Initialize the voice pipeline with all components."""
        load_dotenv()
        self.config = os.environ

        logger.info("=" * 60)
        logger.info("ARCHER VOICE PIPELINE - INITIALIZING")
        logger.info("=" * 60)

        # State management
        self.state = PipelineState.IDLE
        self.is_running = False
        self.state_lock = threading.Lock()

        # Initialize components with detailed error handling
        try:
            logger.info("Loading Wake Word Detector...")
            self.wake_word_detector = WakeWordDetector(self.config)
            logger.info("✅ Wake Word Detector loaded")

            logger.info("Loading VAD...")
            self.vad = VadGate()
            logger.info("✅ VAD loaded")

            logger.info("Loading Voice Auth...")
            # TEMPORARY: Disable SpeechBrain voice auth to bypass TensorFlow issues
            # This allows testing core ARCHER functionality
            logger.warning("Voice Auth disabled temporarily to bypass TensorFlow/Protobuf issues")
            class DummyAuthenticator:
                def authenticate(self, audio_data, sample_rate=16000):
                    return True, "Authentication bypassed - TensorFlow compatibility mode"
                def verify_voice(self, audio_data):
                    return True, "Verification bypassed - TensorFlow compatibility mode"
            self.auth = DummyAuthenticator()
            logger.info("✅ Using dummy authenticator (TensorFlow compatibility mode)")

            logger.info("Loading Speech-to-Text...")
            self.stt = SpeechToText()
            logger.info("✅ Speech-to-Text loaded")

            logger.info("Loading LLM Router...")
            self.llm = LLMRouter()
            logger.info("✅ LLM Router loaded")

            logger.info("Loading TTS Engine...")
            self.tts = TTSEngine()
            logger.info("✅ TTS Engine loaded")

            logger.info("Loading Filler Audio...")
            self.filler_player = FillerPlayer()
            logger.info("✅ Filler Audio loaded")

        except Exception as e:
            logger.error(
                f"Failed to initialize pipeline components: {e}", exc_info=True
            )
            logger.error(f"Component initialization failed at: {e.__traceback__.tb_frame.f_code.co_name if hasattr(e, '__traceback__') else 'unknown'}")
            raise

        # Audio buffer for speech recording
        self.audio_buffer = AudioBuffer(sample_rate=16000, max_duration=10.0)

        # Silence detection
        self.silence_threshold_ms = int(self.config.get("TRAILING_SILENCE_MS", 400))
        self.silence_frames = 0
        self.frames_per_ms = 16  # 16000 Hz / 1000 ms = 16 frames per ms

        # Filler timer
        self.filler_timer: threading.Timer = None
        self.filler_latency_ms = 600

        # Cooldown to prevent wake word spam
        self.last_wake_time = 0
        self.wake_cooldown_s = 2.0

        logger.info("✓ Voice Pipeline initialized successfully")

    def start(self):
        """Start the voice pipeline."""
        logger.info("=" * 60)
        logger.info("STARTING VOICE PIPELINE")
        logger.info("=" * 60)

        self.is_running = True

        sample_rate = 16000
        block_size = 480  # 30ms chunks

        # Try to get audio device
        device_id = os.getenv("AUDIO_DEVICE_INDEX")
        if device_id and device_id.strip():
            try:
                device_id = int(device_id)
            except ValueError:
                device_id = None

        try:
            # Check if audio devices are available with better error handling
            try:
                devices = sd.query_devices()
                input_devices = [
                    d for d in devices if d.get("max_input_channels", 0) > 0
                ]
                if len(input_devices) == 0:
                    raise RuntimeError("No input audio devices available")

                logger.info(f"Found {len(input_devices)} input audio device(s)")

                # Try to find a working default device
                default_device = None
                for i, device in enumerate(devices):
                    if device.get("max_input_channels", 0) > 0:
                        try:
                            # Test if device is accessible
                            sd.check_input_settings(
                                device=i, samplerate=16000, channels=1
                            )
                            default_device = i
                            logger.info(
                                f"Using audio device: {device.get('name', f'Device {i}')}"
                            )
                            break
                        except Exception as e:
                            logger.debug(f"Device {i} not accessible: {e}")
                            continue

                if default_device is None:
                    raise RuntimeError("No accessible input audio devices found")

                device_id = device_id or default_device

            except Exception as e:
                logger.warning(f"Audio device detection failed: {e}")
                logger.info("Running in TEXT-ONLY mode (no audio input/output)")
                # TEXT-ONLY MODE: Just keep the pipeline running for testing
                while self.is_running:
                    time.sleep(1)
                return

            # HARDWARE MODE: Real audio input
            logger.info(f"Opening audio stream (device: {device_id or 'default'})")

            with sd.InputStream(
                device=device_id,
                samplerate=sample_rate,
                blocksize=block_size,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
            ):
                logger.info("=" * 60)
                logger.info("🎤 ARCHER IS LISTENING")
                logger.info(f"   State: {self.state.value}")
                logger.info(f"   Say the wake word to begin...")
                logger.info("=" * 60)

                # Main loop
                while self.is_running:
                    sd.sleep(100)

        except Exception as e:
            # FALLBACK: Text mode (no microphone)
            logger.warning(f"Audio hardware failed: {e}")
            self._run_text_mode()

    def _audio_callback(self, indata, frames, time_info, status):
        """Process incoming audio frames (called by sounddevice)."""
        if status:
            logger.warning(f"Audio status: {status}")

        audio_frame = indata.flatten()

        # Process based on current state
        with self.state_lock:
            if self.state == PipelineState.IDLE:
                self._handle_idle_state(audio_frame)

            elif self.state == PipelineState.LISTENING:
                self._handle_listening_state(audio_frame)

            elif self.state == PipelineState.SPEAKING:
                self._handle_speaking_state(audio_frame)

            # PROCESSING state doesn't process audio input

    def _handle_idle_state(self, audio_frame: np.ndarray):
        """Handle audio in IDLE state (waiting for wake word)."""

        # Check for speech first (VAD gate)
        audio_bytes = audio_frame.tobytes()
        if not self.vad.is_speech(audio_bytes, 16000):
            return

        # Check cooldown
        if time.time() - self.last_wake_time < self.wake_cooldown_s:
            return

        # Check for wake word
        wake_model = self.wake_word_detector.process_frame(audio_frame)
        if wake_model:
            self.last_wake_time = time.time()
            logger.info(f"🎯 WAKE WORD DETECTED: {wake_model}")

            # Publish event
            bus.publish(
                "voice.wake_word", {"model": wake_model, "timestamp": time.time()}
            )

            # Transition to LISTENING
            self._transition_to_listening()

    def _handle_listening_state(self, audio_frame: np.ndarray):
        """Handle audio in LISTENING state (recording user speech)."""

        audio_bytes = audio_frame.tobytes()

        # Check if user is still speaking
        if self.vad.is_speech(audio_bytes, 16000):
            # Append frame to buffer
            self.audio_buffer.append(audio_frame)
            self.silence_frames = 0

        else:
            # Silence detected
            self.silence_frames += 1

            # Check if silence threshold reached
            silence_ms = self.silence_frames / self.frames_per_ms
            if silence_ms >= self.silence_threshold_ms:
                logger.info(f"Silence detected ({silence_ms:.0f}ms), ending speech")
                self._transition_to_processing()

            else:
                # Still within threshold, keep appending (trailing silence)
                self.audio_buffer.append(audio_frame)

    def _handle_speaking_state(self, audio_frame: np.ndarray):
        """Handle audio in SPEAKING state (check for barge-in)."""
        audio_bytes = audio_frame.tobytes()

        # Check if user is speaking (barge-in)
        if self.vad.is_speech(audio_bytes, 16000):
            logger.info("Barge-in detected - stopping TTS")
            self.tts.stop()  # Stop current TTS playback
            # Transition back to LISTENING to capture new speech
            self._transition_to_listening()

    def _transition_to_listening(self):
        """Transition to LISTENING state."""
        logger.info("STATE: IDLE → LISTENING")
        self.state = PipelineState.LISTENING

        # Reset audio buffer
        self.audio_buffer.clear()
        self.silence_frames = 0

        # Publish event
        bus.publish("voice.user_speech_start", {"timestamp": time.time()})

        logger.info("🎙️  Listening for user speech...")

    def _transition_to_processing(self):
        """Transition to PROCESSING state."""
        logger.info("STATE: LISTENING → PROCESSING")
        self.state = PipelineState.PROCESSING

        # Process in background thread to avoid blocking audio callback
        processing_thread = threading.Thread(target=self._process_speech, daemon=True)
        processing_thread.start()

    def _process_speech(self):
        """Process recorded speech (STT → LLM → TTS) with comprehensive latency monitoring."""
        pipeline_timer = performance_monitor.start_timer("voice_pipeline_total")

        try:
            logger.info("⚙️  Processing speech...")

            # Get recorded audio
            audio_data = self.audio_buffer.get_audio()
            duration = self.audio_buffer.get_duration()

            logger.info(
                f"Recorded {duration:.2f}s of audio ({len(audio_data)} samples)"
            )

            if len(audio_data) == 0:
                logger.warning("Empty audio buffer, returning to IDLE")
                performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
                self._transition_to_idle()
                return

            # Start filler timer (600ms)
            self.filler_timer = threading.Timer(0.6, self._play_filler)
            self.filler_timer.start()

            # 1. Speech-to-Text with performance monitoring
            logger.info("Running STT...")
            stt_timer = performance_monitor.start_timer("stt_latency")
            transcript = self.stt.transcribe(audio_data)
            stt_latency = performance_monitor.end_timer(stt_timer, "stt_latency")

            if not transcript:
                logger.warning("STT returned empty transcript")
                self._cancel_filler()
                performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
                self._transition_to_idle()
                return

            logger.info(f"✓ STT ({stt_latency:.0f}ms): '{transcript}'")

            # Publish event with enhanced latency data
            bus.publish(
                "voice.user_speech_end",
                {
                    "text": transcript,
                    "duration": duration,
                    "stt_latency": stt_latency
                    / 1000,  # Convert back to seconds for compatibility
                    "performance_metrics": performance_monitor.get_metric_stats(
                        "stt_latency"
                    ),
                },
            )

            # 2. LLM Processing with performance monitoring
            logger.info("Querying LLM...")
            llm_timer = performance_monitor.start_timer("llm_latency")

            response_text = self.llm.get_response(
                user_text=transcript, role="assistant", temperature=0.7
            )

            llm_latency = performance_monitor.end_timer(llm_timer, "llm_latency")

            logger.info(f"✓ LLM ({llm_latency:.0f}ms): '{response_text[:100]}...'")

            # Cancel filler now that we have response
            self._cancel_filler()

            # Publish event with enhanced latency data
            bus.publish(
                "voice.assistant_response_start",
                {
                    "text": response_text,
                    "llm_latency": llm_latency
                    / 1000,  # Convert back to seconds for compatibility
                    "performance_metrics": performance_monitor.get_metric_stats(
                        "llm_latency"
                    ),
                },
            )

            # 3. Text-to-Speech with performance monitoring
            self._transition_to_speaking()

            logger.info("Playing TTS response...")
            tts_timer = performance_monitor.start_timer("tts_latency")
            self.tts.speak(response_text)
            tts_latency = performance_monitor.end_timer(tts_timer, "tts_latency")

            logger.info(f"✓ TTS ({tts_latency:.0f}ms) Response complete")

            # Record total pipeline latency
            total_latency = performance_monitor.end_timer(
                pipeline_timer, "voice_pipeline_total"
            )

            # Publish comprehensive performance report
            bus.publish(
                "voice.assistant_response_end",
                {
                    "timestamp": time.time(),
                    "performance_report": {
                        "total_latency": total_latency,
                        "stt_latency": stt_latency,
                        "llm_latency": llm_latency,
                        "tts_latency": tts_latency,
                        "health_status": performance_monitor.get_health_status(),
                    },
                },
            )

            # Log performance summary
            logger.info(
                f"PERFORMANCE: Total pipeline = {total_latency:.0f}ms "
                f"(STT: {stt_latency:.0f}ms, LLM: {llm_latency:.0f}ms, TTS: {tts_latency:.0f}ms)"
            )

            # Return to IDLE
            self._transition_to_idle()

        except Exception as e:
            logger.error(f"Speech processing failed: {e}", exc_info=True)
            self._cancel_filler()
            performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
            self._transition_to_idle()

    def _transition_to_speaking(self):
        """Transition to SPEAKING state."""
        logger.info("STATE: PROCESSING → SPEAKING")
        self.state = PipelineState.SPEAKING

    def _transition_to_idle(self):
        """Transition back to IDLE state."""
        logger.info("STATE: → IDLE")
        with self.state_lock:
            self.state = PipelineState.IDLE
            self.audio_buffer.clear()
            self.silence_frames = 0

        logger.info("🎤 Ready for wake word...")

    def _play_filler(self):
        """Play filler audio if LLM is taking too long."""
        logger.info("⏱️  Playing filler audio (LLM latency >600ms)")
        try:
            self.filler_player.play_random()
        except Exception as e:
            logger.error(f"Filler playback failed: {e}")

    def _cancel_filler(self):
        """Cancel the filler timer if it hasn't fired yet."""
        if self.filler_timer:
            self.filler_timer.cancel()
            self.filler_timer = None

    def _run_text_mode(self):
        """Fallback text input mode when no microphone available."""
        logger.warning("=" * 60)
        logger.warning("MICROPHONE UNAVAILABLE - TEXT MODE ACTIVE")
        logger.warning("=" * 60)

        print("\n" + "=" * 60)
        print("ARCHER - TEXT INPUT MODE")
        print("=" * 60)
        print("Type your message and press Enter.")
        print("Say 'exit' or 'quit' to stop.")
        print("=" * 60 + "\n")

        while self.is_running:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ["exit", "quit", "stop"]:
                    logger.info("User requested exit")
                    self.stop()
                    break

                if not user_input:
                    continue

                # Process text input as if it were transcribed speech
                logger.info(f"User input: '{user_input}'")

                try:
                    # Get LLM response
                    response = self.llm.get_response(user_input, role="assistant")

                    # Display response
                    print(f"\nARCHER: {response}\n")

                except Exception as e:
                    logger.error(f"Processing failed: {e}", exc_info=True)
                    print(f"\nARCHER: Sorry, I encountered an error processing that.\n")

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.stop()
                break

            except Exception as e:
                logger.error(f"Text mode error: {e}", exc_info=True)

    def stop(self):
        """Stop the voice pipeline."""
        logger.info("Stopping Voice Pipeline...")
        self.is_running = False

        # Cancel any active filler
        self._cancel_filler()

        logger.info("✓ Voice Pipeline stopped")
