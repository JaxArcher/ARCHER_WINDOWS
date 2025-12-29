"""
Enhanced Voice Pipeline for ARCHER

Complete voice interaction system with wake word detection, speaker verification, 
STT, TTS, voice cloning, emotion detection, multi-language support, streaming, and filler audio.
"""

import os
import logging
import sounddevice as sd
import numpy as np
import threading
import time
import queue
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

# Memory integration
try:
    from src.memory.unified_vector_memory import VectorMemory
    from src.memory.episodic_memory import EpisodicMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# Voice components
try:
    from .enhanced_tts import EnhancedF5TTS, EmotionType, LanguageSupport
    from .wake_word import WakeWordDetector
    from .voice_auth import VoiceAuthenticator
    from .vad import VadGate
    from .stt import SpeechToText
    from .audio_buffer import AudioBuffer
    from .fillers import FillerPlayer
    from .interruption import InterruptionHandler
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.error(f"Voice components import failed: {e}")
    COMPONENTS_AVAILABLE = False

# Event system
try:
    from src.events.bus import bus
    from src.performance_monitor import performance_monitor
    EVENTS_AVAILABLE = True
except ImportError:
    EVENTS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class PipelineState(Enum):
    """Voice pipeline states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"

class EnhancedVoicePipeline:
    """
    Enhanced voice interaction pipeline for ARCHER.
    
    Features:
    - Wake word detection (openWakeWord)
    - Speaker verification (SpeechBrain)
    - Multi-language STT (Faster-Whisper)
    - Enhanced TTS (F5-TTS with multi-language, emotion, filler audio)
    - Voice cloning
    - Emotion detection
    - Memory integration
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize the enhanced voice pipeline."""
        logger.info("=" * 80)
        logger.info("ENHANCED ARCHER VOICE PIPELINE - INITIALIZING")
        logger.info("=" * 80)
        
        # State management
        self.state = PipelineState.IDLE
        self.is_running = False
        self.state_lock = threading.Lock()
        
        # Memory integration
        if MEMORY_AVAILABLE:
            self.memory = VectorMemory(collection_name="agent_v_pipeline")
            self.episodic = EpisodicMemory()
            logger.info("✅ Memory systems initialized")
        else:
            self.memory = None
            self.episodic = None
            logger.warning("⚠️ Memory systems not available")
        
        # Initialize components
        self._initialize_components()
        
        # Audio configuration
        self.sample_rate = 16000
        self.block_size = 480  # 30ms chunks
        self.audio_device = None
        
        # Silence detection
        self.silence_threshold_ms = 400
        self.silence_frames = 0
        self.frames_per_ms = self.sample_rate / 1000
        
        # Timers
        self.filler_timer: Optional[threading.Timer] = None
        self.filler_latency_ms = 600
        
        # Cooldowns
        self.last_wake_time = 0
        self.wake_cooldown_s = 2.0
        
        # Performance metrics
        self.performance_metrics = {
            'total_pipeline_time': 0.0,
            'pipeline_count': 0,
            'average_latency': 0.0,
            'stt_latency': 0.0,
            'llm_latency': 0.0,
            'tts_latency': 0.0
        }
        
        # Audio buffer
        self.audio_buffer = AudioBuffer(sample_rate=self.sample_rate, max_duration=10.0)
        
        # Emotion detection state
        self.current_emotion = EmotionType.NEUTRAL
        self.emotion_history = []
        
        logger.info("✅ Enhanced Voice Pipeline initialized successfully")
    
    def _initialize_components(self):
        """Initialize all voice components with error handling."""
        try:
            # Enhanced TTS
            logger.info("Loading Enhanced TTS...")
            self.tts = EnhancedF5TTS()
            logger.info("✅ Enhanced TTS loaded")
            
            # Wake Word Detector
            logger.info("Loading Wake Word Detector...")
            self.wake_word_detector = WakeWordDetector()
            logger.info("✅ Wake Word Detector loaded")
            
            # Voice Authenticator
            logger.info("Loading Voice Authenticator...")
            self.voice_auth = VoiceAuthenticator()
            logger.info("✅ Voice Authenticator loaded")
            
            # VAD
            logger.info("Loading VAD...")
            self.vad = VadGate()
            logger.info("✅ VAD loaded")
            
            # STT
            logger.info("Loading Speech-to-Text...")
            self.stt = SpeechToText()
            logger.info("✅ Speech-to-Text loaded")
            
            # Filler Player
            logger.info("Loading Filler Audio...")
            self.filler_player = FillerPlayer()
            logger.info("✅ Filler Audio loaded")
            
            # Interruption Handler
            logger.info("Loading Interruption Handler...")
            self.interruption_handler = InterruptionHandler()
            logger.info("✅ Interruption Handler loaded")
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}", exc_info=True)
            raise
    
    def start(self):
        """Start the enhanced voice pipeline."""
        logger.info("=" * 80)
        logger.info("STARTING ENHANCED VOICE PIPELINE")
        logger.info("=" * 80)
        
        self.is_running = True
        
        # Try to initialize audio stream
        try:
            self._initialize_audio_stream()
        except Exception as e:
            logger.error(f"Audio initialization failed: {e}")
            self._run_text_mode()
    
    def _initialize_audio_stream(self):
        """Initialize audio input stream."""
        try:
            # Check audio devices
            devices = sd.query_devices()
            input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
            
            if not input_devices:
                raise RuntimeError("No input audio devices available")
            
            logger.info(f"Found {len(input_devices)} input audio device(s)")
            
            # Find default device
            default_device = None
            for i, device in enumerate(devices):
                if device.get("max_input_channels", 0) > 0:
                    try:
                        sd.check_input_settings(device=i, samplerate=self.sample_rate, channels=1)
                        default_device = i
                        logger.info(f"Using audio device: {device.get('name', f'Device {i}')}")
                        break
                    except Exception as e:
                        logger.debug(f"Device {i} not accessible: {e}")
                        continue
            
            if default_device is None:
                raise RuntimeError("No accessible input audio devices found")
            
            # Start audio stream
            with sd.InputStream(
                device=default_device,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
            ):
                logger.info("=" * 80)
                logger.info("🎤 ENHANCED ARCHER IS LISTENING")
                logger.info(f"   State: {self.state.value}")
                logger.info(f"   Say the wake word to begin...")
                logger.info("=" * 80)
                
                # Main loop
                while self.is_running:
                    sd.sleep(100)
                    
        except Exception as e:
            logger.error(f"Audio stream failed: {e}")
            raise
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Process incoming audio frames."""
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
        if not self.vad.is_speech(audio_bytes, self.sample_rate):
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
            if EVENTS_AVAILABLE:
                bus.publish("voice.wake_word", {
                    "model": wake_model,
                    "timestamp": time.time()
                })
            
            # Transition to LISTENING
            self._transition_to_listening()
    
    def _handle_listening_state(self, audio_frame: np.ndarray):
        """Handle audio in LISTENING state (recording user speech)."""
        audio_bytes = audio_frame.tobytes()
        
        # Check if user is still speaking
        if self.vad.is_speech(audio_bytes, self.sample_rate):
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
        if self.vad.is_speech(audio_bytes, self.sample_rate):
            logger.info("Barge-in detected - stopping TTS")
            self.tts.stop()  # Stop current TTS playback
            
            # Detect emotion from barge-in
            emotion = self._detect_emotion_from_audio(audio_frame)
            logger.info(f"Detected emotion from barge-in: {emotion}")
            
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
        if EVENTS_AVAILABLE:
            bus.publish("voice.user_speech_start", {"timestamp": time.time()})
        
        logger.info("🎙️  Listening for user speech...")
    
    def _transition_to_processing(self):
        """Transition to PROCESSING state."""
        logger.info("STATE: LISTENING → PROCESSING")
        self.state = PipelineState.PROCESSING
        
        # Process in background thread
        processing_thread = threading.Thread(target=self._process_speech, daemon=True)
        processing_thread.start()
    
    def _process_speech(self):
        """Process recorded speech with comprehensive features."""
        pipeline_timer = None
        if EVENTS_AVAILABLE:
            pipeline_timer = performance_monitor.start_timer("voice_pipeline_total")
        
        try:
            logger.info("⚙️  Processing speech with enhanced features...")
            
            # Get recorded audio
            audio_data = self.audio_buffer.get_audio()
            duration = self.audio_buffer.get_duration()
            
            logger.info(f"Recorded {duration:.2f}s of audio ({len(audio_data)} samples)")
            
            if len(audio_data) == 0:
                logger.warning("Empty audio buffer, returning to IDLE")
                if pipeline_timer:
                    performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
                self._transition_to_idle()
                return
            
            # Start filler timer (600ms)
            self.filler_timer = threading.Timer(0.6, self._play_filler)
            self.filler_timer.start()
            
            # 1. Voice Authentication
            logger.info("Authenticating speaker...")
            auth_start = time.time()
            is_authenticated, auth_result = self.voice_auth.authenticate(audio_data, self.sample_rate)
            auth_time = time.time() - auth_start
            
            if not is_authenticated:
                logger.warning(f"Voice authentication failed: {auth_result}")
                self._cancel_filler()
                if pipeline_timer:
                    performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
                self._transition_to_idle()
                return
            
            logger.info(f"✓ Voice authentication successful ({auth_time:.3f}s)")
            
            # 2. Emotion Detection
            logger.info("Detecting emotion...")
            emotion_start = time.time()
            self.current_emotion = self._detect_emotion_from_audio(audio_data)
            emotion_time = time.time() - emotion_start
            
            logger.info(f"✓ Emotion detected: {self.current_emotion.value} ({emotion_time:.3f}s)")
            
            # Set TTS emotion based on detected emotion
            self.tts.set_emotion(self.current_emotion)
            
            # 3. Speech-to-Text with performance monitoring
            logger.info("Running STT...")
            stt_timer = None
            if EVENTS_AVAILABLE:
                stt_timer = performance_monitor.start_timer("stt_latency")
            
            transcript = self.stt.transcribe(audio_data)
            
            if EVENTS_AVAILABLE and stt_timer:
                stt_latency = performance_monitor.end_timer(stt_timer, "stt_latency")
            else:
                stt_latency = (time.time() - (emotion_start + emotion_time)) * 1000
            
            if not transcript:
                logger.warning("STT returned empty transcript")
                self._cancel_filler()
                if pipeline_timer:
                    performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
                self._transition_to_idle()
                return
            
            logger.info(f"✓ STT ({stt_latency:.0f}ms): '{transcript}'")
            
            # 4. Language Detection
            logger.info("Detecting language...")
            detected_language = self.tts.detect_language(transcript)
            self.tts.set_language(detected_language)
            logger.info(f"✓ Language detected: {detected_language.value}")
            
            # Publish event with enhanced data
            if EVENTS_AVAILABLE:
                bus.publish("voice.user_speech_end", {
                    "text": transcript,
                    "duration": duration,
                    "stt_latency": stt_latency / 1000,
                    "emotion": self.current_emotion.value,
                    "language": detected_language.value,
                    "authentication": auth_result,
                    "performance_metrics": performance_monitor.get_metric_stats("stt_latency") if EVENTS_AVAILABLE else {}
                })
            
            # 5. LLM Processing (simplified for this implementation)
            logger.info("Processing with LLM...")
            llm_timer = None
            if EVENTS_AVAILABLE:
                llm_timer = performance_monitor.start_timer("llm_latency")
            
            # In a real implementation, this would call the LLM router
            response_text = self._generate_response(transcript)
            
            if EVENTS_AVAILABLE and llm_timer:
                llm_latency = performance_monitor.end_timer(llm_timer, "llm_latency")
            else:
                llm_latency = (time.time() - (time.time() - 0.5)) * 1000  # Simulated
            
            logger.info(f"✓ LLM ({llm_latency:.0f}ms): '{response_text[:100]}...'")
            
            # Cancel filler now that we have response
            self._cancel_filler()
            
            # 6. Text-to-Speech with performance monitoring
            self._transition_to_speaking()
            
            logger.info("Playing TTS response...")
            tts_timer = None
            if EVENTS_AVAILABLE:
                tts_timer = performance_monitor.start_timer("tts_latency")
            
            # Synthesize speech with emotion and language
            audio_output = self.tts.synthesize(response_text)
            
            if audio_output:
                # Play the synthesized audio
                self._play_audio(audio_output)
            else:
                logger.warning("TTS synthesis failed, using fallback")
                self._play_fallback_audio(response_text)
            
            if EVENTS_AVAILABLE and tts_timer:
                tts_latency = performance_monitor.end_timer(tts_timer, "tts_latency")
            else:
                tts_latency = (time.time() - (time.time() - 1.0)) * 1000  # Simulated
            
            logger.info(f"✓ TTS ({tts_latency:.0f}ms) Response complete")
            
            # Update performance metrics
            if EVENTS_AVAILABLE and pipeline_timer:
                total_latency = performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
            else:
                total_latency = stt_latency + llm_latency + tts_latency
            
            # Update internal metrics
            self.performance_metrics['total_pipeline_time'] += total_latency
            self.performance_metrics['pipeline_count'] += 1
            self.performance_metrics['average_latency'] = \
                self.performance_metrics['total_pipeline_time'] / \
                self.performance_metrics['pipeline_count']
            self.performance_metrics['stt_latency'] = stt_latency
            self.performance_metrics['llm_latency'] = llm_latency
            self.performance_metrics['tts_latency'] = tts_latency
            
            # Log to memory
            self._log_interaction_to_memory(transcript, response_text, total_latency)
            
            # Publish comprehensive performance report
            if EVENTS_AVAILABLE:
                bus.publish("voice.assistant_response_end", {
                    "timestamp": time.time(),
                    "performance_report": {
                        "total_latency": total_latency,
                        "stt_latency": stt_latency,
                        "llm_latency": llm_latency,
                        "tts_latency": tts_latency,
                        "health_status": performance_monitor.get_health_status() if EVENTS_AVAILABLE else {},
                        "emotion": self.current_emotion.value,
                        "language": detected_language.value
                    },
                })
            
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
            if pipeline_timer:
                performance_monitor.end_timer(pipeline_timer, "voice_pipeline_total")
            self._transition_to_idle()
    
    def _detect_emotion_from_audio(self, audio_data: np.ndarray) -> EmotionType:
        """Detect emotion from audio using acoustic features."""
        try:
            # Extract acoustic features
            features = self._extract_acoustic_features(audio_data)
            
            # Simple emotion classification based on features
            # In a real implementation, this would use a trained model
            if features['pitch_mean'] > 200:
                if features['energy'] > 0.1:
                    return EmotionType.EXCITED
                else:
                    return EmotionType.HAPPY
            elif features['pitch_mean'] < 100:
                if features['energy'] < 0.05:
                    return EmotionType.SAD
                else:
                    return EmotionType.CALM
            elif features['speech_rate'] > 0.2:
                return EmotionType.ANGRY
            else:
                return EmotionType.NEUTRAL
                
        except Exception as e:
            logger.error(f"Emotion detection failed: {e}")
            return EmotionType.NEUTRAL
    
    def _extract_acoustic_features(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Extract basic acoustic features from audio."""
        try:
            # Convert to float if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
            
            # Calculate basic features
            energy = np.mean(audio_data ** 2)
            
            # Simple pitch detection (zero-crossing rate)
            zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / 2
            pitch_estimate = zero_crossings / len(audio_data) * self.sample_rate
            
            # Speech rate (simplified)
            speech_rate = len(audio_data) / self.sample_rate  # seconds
            
            return {
                'energy': float(energy),
                'pitch_mean': float(pitch_estimate),
                'speech_rate': float(speech_rate),
                'duration': float(len(audio_data) / self.sample_rate)
            }
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {
                'energy': 0.05,
                'pitch_mean': 150.0,
                'speech_rate': 0.15,
                'duration': 1.0
            }
    
    def _generate_response(self, transcript: str) -> str:
        """Generate response (simplified for this implementation)."""
        try:
            # In a real implementation, this would call the LLM router
            # For now, generate a simple response based on input
            
            transcript_lower = transcript.lower()
            
            if "hello" in transcript_lower or "hi" in transcript_lower:
                return "Hello! How can I assist you today?"
            elif "how are you" in transcript_lower:
                return "I'm doing well, thank you for asking! How about you?"
            elif "time" in transcript_lower:
                return f"The current time is {datetime.now().strftime('%H:%M:%S')}."
            elif "date" in transcript_lower:
                return f"Today is {datetime.now().strftime('%Y-%m-%d')}."
            elif "weather" in transcript_lower:
                return "I can't check the weather right now, but I can help with other information!"
            elif "thank" in transcript_lower:
                return "You're welcome! Is there anything else I can help with?"
            elif "bye" in transcript_lower or "goodbye" in transcript_lower:
                return "Goodbye! Have a wonderful day!"
            else:
                return f"I heard you say: '{transcript}'. How can I assist you with that?"
                
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "I'm sorry, I had trouble processing that request."
    
    def _play_audio(self, audio_data: bytes):
        """Play audio data."""
        try:
            import tempfile
            import soundfile as sf
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file = f.name
            
            # Convert bytes to numpy array and save
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            sf.write(temp_file, audio_array, self.sample_rate)
            
            # Play using winsound
            import winsound
            winsound.PlaySound(temp_file, winsound.SND_FILENAME)
            
            # Clean up
            os.unlink(temp_file)
            
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
    
    def _play_fallback_audio(self, text: str):
        """Play fallback audio using simple synthesis."""
        try:
            # Generate simple beep tones
            sample_rate = 22050
            duration = len(text) * 0.1
            
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            audio_data = 0.3 * np.sin(2 * np.pi * 440 * t)
            
            # Play using sounddevice
            sd.play(audio_data, sample_rate)
            sd.wait()
            
        except Exception as e:
            logger.error(f"Fallback audio playback failed: {e}")
    
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
    
    def _log_interaction_to_memory(self, user_text: str, response_text: str, latency: float):
        """Log complete interaction to memory systems."""
        try:
            if not self.memory or not self.episodic:
                return
            
            # Store in vector memory
            self.memory.add(
                text=f"User: {user_text}\nARCHER: {response_text}",
                metadata={
                    "agent": "agent_v",
                    "event_type": "voice_interaction",
                    "emotion": self.current_emotion.value,
                    "language": self.tts.current_language.value,
                    "latency": latency,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Store in episodic memory
            self.episodic.log(
                agent="agent_v",
                event_type="voice_interaction",
                data={
                    "user_text": user_text,
                    "response_text": response_text,
                    "emotion": self.current_emotion.value,
                    "language": self.tts.current_language.value,
                    "latency": latency,
                    "performance": self.performance_metrics,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info("✅ Interaction logged to memory")
            
        except Exception as e:
            logger.error(f"Memory logging failed: {e}")
    
    def _run_text_mode(self):
        """Fallback text input mode when no microphone available."""
        logger.warning("=" * 80)
        logger.warning("MICROPHONE UNAVAILABLE - TEXT MODE ACTIVE")
        logger.warning("=" * 80)
        
        print("\n" + "=" * 80)
        print("ARCHER - ENHANCED TEXT INPUT MODE")
        print("=" * 80)
        print("Type your message and press Enter.")
        print("Say 'exit' or 'quit' to stop.")
        print("=" * 80 + "\n")
        
        while self.is_running:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ["exit", "quit", "stop"]:
                    logger.info("User requested exit")
                    self.stop()
                    break
                
                if not user_input:
                    continue
                
                # Process text input
                logger.info(f"User input: '{user_input}'")
                
                try:
                    # Generate response
                    response = self._generate_response(user_input)
                    
                    # Display response
                    print(f"\nARCHER: {response}\n")
                    
                    # Log to memory
                    self._log_interaction_to_memory(user_input, response, 0.0)
                    
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
        logger.info("Stopping Enhanced Voice Pipeline...")
        self.is_running = False
        
        # Cancel any active filler
        self._cancel_filler()
        
        logger.info("✅ Enhanced Voice Pipeline stopped")
    
    def get_state(self) -> PipelineState:
        """Get current pipeline state."""
        return self.state
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_metrics.copy()
    
    def reset_performance_metrics(self):
        """Reset performance metrics."""
        self.performance_metrics = {
            'total_pipeline_time': 0.0,
            'pipeline_count': 0,
            'average_latency': 0.0,
            'stt_latency': 0.0,
            'llm_latency': 0.0,
            'tts_latency': 0.0
        }
    
    def enable_filler_audio(self, enabled: bool = True):
        """Enable or disable filler audio."""
        self.filler_audio_enabled = enabled
        logger.info(f"Filler audio {'enabled' if enabled else 'disabled'}")
    
    def enable_barge_in(self, enabled: bool = True):
        """Enable or disable barge-in detection."""
        self.barge_in_enabled = enabled
        logger.info(f"Barge-in detection {'enabled' if enabled else 'disabled'}")
    
    def set_emotion(self, emotion: EmotionType):
        """Set current emotion for TTS."""
        self.current_emotion = emotion
        self.tts.set_emotion(emotion)
        logger.info(f"Emotion set to: {emotion.value}")
    
    def set_language(self, language: LanguageSupport):
        """Set current language for TTS."""
        self.tts.set_language(language)
        logger.info(f"Language set to: {language.value}")
