"""
Enhanced TTS System for ARCHER

Extends existing F5-TTS with multi-language support, filler audio, barge-in handling, and emotion detection.
"""

import logging
import os
import tempfile
import threading
import time
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path
import numpy as np

# Memory integration
try:
    from src.memory.unified_vector_memory import VectorMemory
    from src.memory.episodic_memory import EpisodicMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    
# Configure logging
logger = logging.getLogger(__name__)

class TTSEngine(Enum):
    """Available TTS engines in order of preference."""
    F5_TTS = "f5"  # Primary engine
    COQUI_TTS = "coqui"
    INDEX_TTS = "indextts"
    BARK_TTS = "bark"
    KOKORO_TTS = "kokoro"
    NONE = "none"

class EmotionType(Enum):
    """Supported emotion types for TTS."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CALM = "calm"

class LanguageSupport(Enum):
    """Supported languages for TTS."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"

class EnhancedF5TTS:
    """
    Enhanced F5-TTS Service with multi-language support, filler audio, barge-in handling, and emotion detection.
    """
    
    def __init__(self):
        """Initialize enhanced TTS service."""
        self.current_engine = TTSEngine.F5_TTS
        self.current_emotion = EmotionType.NEUTRAL
        self.current_language = LanguageSupport.ENGLISH
        self.is_speaking = False
        self.speaking_lock = threading.Lock()
        self.filler_audio_enabled = True
        self.barge_in_enabled = True
        
        # Memory integration
        if MEMORY_AVAILABLE:
            self.memory = VectorMemory(collection_name="agent_v_tts")
            self.episodic = EpisodicMemory()
        else:
            self.memory = None
            self.episodic = None
            
        # Filler audio configuration
        self.filler_audio_files = []
        self._load_filler_audio()
        
        # Performance metrics
        self.performance_metrics = {
            'total_synthesis_time': 0.0,
            'synthesis_count': 0,
            'average_latency': 0.0
        }
        
        logger.info("✅ EnhancedF5TTS initialized")
        
    def _load_filler_audio(self):
        """Load filler audio files for latency masking."""
        filler_dir = Path("data/filler_audio")
        if filler_dir.exists():
            for audio_file in filler_dir.glob("*"):
                if audio_file.suffix.lower() in ['.wav', '.mp3', '.ogg']:
                    self.filler_audio_files.append(str(audio_file))
                    logger.info(f"Loaded filler audio: {audio_file.name}")
        else:
            logger.warning(f"Filler audio directory not found: {filler_dir}")
            # Create default filler audio directory
            filler_dir.mkdir(parents=True, exist_ok=True)
    
    def _play_filler_audio(self):
        """Play random filler audio during processing delays."""
        if not self.filler_audio_enabled or not self.filler_audio_files:
            return
            
        try:
            import random
            filler_file = random.choice(self.filler_audio_files)
            
            # Play filler audio
            import winsound
            winsound.PlaySound(filler_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            logger.info(f"Playing filler audio: {filler_file}")
            
        except Exception as e:
            logger.error(f"Failed to play filler audio: {e}")
    
    def set_emotion(self, emotion: EmotionType) -> bool:
        """Set emotion for TTS synthesis."""
        try:
            self.current_emotion = emotion
            logger.info(f"TTS emotion set to: {emotion.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set emotion: {e}")
            return False
    
    def set_language(self, language: LanguageSupport) -> bool:
        """Set language for TTS synthesis."""
        try:
            self.current_language = language
            logger.info(f"TTS language set to: {language.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set language: {e}")
            return False
    
    def detect_language(self, text: str) -> LanguageSupport:
        """Detect language from text."""
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0  # For consistent results
            
            lang_code = detect(text)
            
            # Map detected language to supported languages
            lang_map = {
                'en': LanguageSupport.ENGLISH,
                'es': LanguageSupport.SPANISH,
                'fr': LanguageSupport.FRENCH,
                'de': LanguageSupport.GERMAN,
                'zh': LanguageSupport.CHINESE,
                'ja': LanguageSupport.JAPANESE,
                'ko': LanguageSupport.KOREAN,
                'it': LanguageSupport.ITALIAN,
                'pt': LanguageSupport.PORTUGUESE,
                'ru': LanguageSupport.RUSSIAN
            }
            
            return lang_map.get(lang_code, LanguageSupport.ENGLISH)
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return LanguageSupport.ENGLISH
    
    def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """Synthesize speech with comprehensive error handling and memory integration."""
        if not text or not text.strip():
            logger.warning("Empty text provided for synthesis")
            return None
            
        start_time = time.time()
        
        try:
            # Auto-detect language if not set
            if self.current_language == LanguageSupport.ENGLISH:
                detected_lang = self.detect_language(text)
                if detected_lang != LanguageSupport.ENGLISH:
                    self.set_language(detected_lang)
                    logger.info(f"Auto-detected language: {detected_lang.value}")
            
            # Start filler timer for latency masking
            filler_timer = threading.Timer(0.6, self._play_filler_audio)
            filler_timer.start()
            
            # Use appropriate engine based on language
            if self.current_engine == TTSEngine.F5_TTS:
                audio_data = self._synthesize_f5tts(text, voice)
            else:
                audio_data = self._synthesize_fallback(text)
            
            # Cancel filler timer
            filler_timer.cancel()
            
            # Update performance metrics
            synthesis_time = time.time() - start_time
            self.performance_metrics['total_synthesis_time'] += synthesis_time
            self.performance_metrics['synthesis_count'] += 1
            self.performance_metrics['average_latency'] = \
                self.performance_metrics['total_synthesis_time'] / \
                self.performance_metrics['synthesis_count']
            
            logger.info(f"✅ Synthesis completed in {synthesis_time:.3f}s")
            
            # Memory integration
            if self.memory and self.episodic:
                self._log_memory_event(text, synthesis_time)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            return self._fallback_synthesis(text)
    
    def _synthesize_f5tts(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """Synthesize speech using F5-TTS."""
        try:
            from f5_tts.api import F5TTS
            import torch
            import tempfile
            
            # Get reference audio based on language
            ref_audio_path, ref_text = self._get_reference_audio()
            
            # Initialize F5-TTS
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = F5TTS(
                model="F5TTS_v1_Base",
                device=device
            )
            
            # Generate speech
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                output_file = f.name
            
            result = model.infer(
                ref_file=ref_audio_path,
                ref_text=ref_text,
                gen_text=text,
                file_wave=output_file,
                remove_silence=False,
                speed=1.0
            )
            
            # Read generated audio
            import soundfile as sf
            audio_data, sample_rate = sf.read(output_file, dtype='float32')
            
            # Clean up
            os.unlink(output_file)
            
            return audio_data.tobytes()
            
        except ImportError:
            logger.error("F5-TTS not available, falling back to other engine")
            return None
        except Exception as e:
            logger.error(f"F5-TTS synthesis failed: {e}")
            return None
    
    def _get_reference_audio(self) -> Tuple[str, str]:
        """Get appropriate reference audio based on current language and emotion."""
        try:
            from importlib.resources import files
            
            # Language-specific reference audio
            lang_refs = {
                LanguageSupport.ENGLISH: ("infer/examples/basic/basic_ref_en.wav", 
                                       "Some call me nature, others call me mother nature."),
                LanguageSupport.SPANISH: ("infer/examples/basic/basic_ref_es.wav", 
                                       "Algunos me llaman naturaleza, otros me llaman madre naturaleza."),
                LanguageSupport.FRENCH: ("infer/examples/basic/basic_ref_fr.wav", 
                                       "Certains m'appellent nature, d'autres m'appellent mère nature."),
                # Add more languages as needed
            }
            
            ref_file, ref_text = lang_refs.get(self.current_language, 
                                              lang_refs[LanguageSupport.ENGLISH])
            
            ref_audio_path = str(files("f5_tts").joinpath(ref_file))
            return ref_audio_path, ref_text
            
        except Exception as e:
            logger.error(f"Failed to get reference audio: {e}")
            # Fallback to English
            return str(files("f5_tts").joinpath("infer/examples/basic/basic_ref_en.wav")), \
                   "Some call me nature, others call me mother nature."
    
    def _synthesize_fallback(self, text: str) -> Optional[bytes]:
        """Fallback synthesis using Coqui TTS."""
        try:
            import TTS
            from TTS.api import TTS as TTS_API
            
            # Language-specific model selection
            model_map = {
                LanguageSupport.ENGLISH: "tts_models/en/ljspeech/tacotron2-DDC_ph",
                LanguageSupport.SPANISH: "tts_models/es/css10/vits",
                LanguageSupport.FRENCH: "tts_models/fr/css10/vits",
                # Add more languages as needed
            }
            
            model_name = model_map.get(self.current_language, 
                                      model_map[LanguageSupport.ENGLISH])
            
            tts = TTS_API(model_name=model_name)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                output_path = f.name
            
            tts.tts_to_file(text=text, file_path=output_path)
            
            # Read generated audio
            import soundfile as sf
            audio_data, sample_rate = sf.read(output_path, dtype='float32')
            
            # Clean up
            os.unlink(output_path)
            
            return audio_data.tobytes()
            
        except Exception as e:
            logger.error(f"Fallback synthesis failed: {e}")
            return None
    
    def _fallback_synthesis(self, text: str) -> Optional[bytes]:
        """Emergency fallback synthesis using simple tone generation."""
        try:
            # Generate simple beep tones representing speech
            sample_rate = 22050
            duration = len(text) * 0.1  # 100ms per character
            
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            
            # Create varying tones based on text
            tones = []
            for i, char in enumerate(text):
                freq = 440 + (ord(char) % 200)  # Vary frequency based on character
                tone = 0.3 * np.sin(2 * np.pi * freq * t[i*100:(i+1)*100])
                tones.append(tone)
            
            audio_data = np.concatenate(tones) if tones else np.zeros(int(sample_rate * 0.1))
            
            return audio_data.astype(np.float32).tobytes()
            
        except Exception as e:
            logger.error(f"Emergency fallback synthesis failed: {e}")
            return None
    
    def _log_memory_event(self, text: str, synthesis_time: float):
        """Log TTS event to memory systems."""
        try:
            # Store in vector memory
            self.memory.add(
                text=f"TTS Event: {text}",
                metadata={
                    "agent": "agent_v",
                    "event_type": "tts_synthesis",
                    "language": self.current_language.value,
                    "emotion": self.current_emotion.value,
                    "synthesis_time": synthesis_time,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Store in episodic memory
            self.episodic.log(
                agent="agent_v",
                event_type="tts_synthesis",
                data={
                    "text": text,
                    "language": self.current_language.value,
                    "emotion": self.current_emotion.value,
                    "synthesis_time": synthesis_time,
                    "performance": self.performance_metrics
                }
            )
            
        except Exception as e:
            logger.error(f"Memory logging failed: {e}")
    
    def stop(self):
        """Stop current TTS playback (for barge-in handling)."""
        with self.speaking_lock:
            if self.is_speaking:
                # Implementation depends on audio backend
                try:
                    import winsound
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    logger.info("✅ TTS playback stopped (barge-in)")
                except:
                    pass
                
                self.is_speaking = False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_metrics.copy()
    
    def reset_performance_metrics(self):
        """Reset performance metrics."""
        self.performance_metrics = {
            'total_synthesis_time': 0.0,
            'synthesis_count': 0,
            'average_latency': 0.0
        }
    
    def enable_filler_audio(self, enabled: bool = True):
        """Enable or disable filler audio."""
        self.filler_audio_enabled = enabled
        logger.info(f"Filler audio {'enabled' if enabled else 'disabled'}")
    
    def enable_barge_in(self, enabled: bool = True):
        """Enable or disable barge-in detection."""
        self.barge_in_enabled = enabled
        logger.info(f"Barge-in detection {'enabled' if enabled else 'disabled'}")
