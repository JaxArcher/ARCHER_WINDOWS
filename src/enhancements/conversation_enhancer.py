"""
Conversation Enhancer

Implements natural conversation improvements including:
- Endpoint detection
- Noise suppression
- Backchanneling
- Language detection
- Emotion analysis
"""

import logging
import numpy as np
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

# Import external libraries
import noisereduce as nr
from langdetect import detect, DetectorFactory
from textblob import TextBlob
import assemblyai as aai

logger = logging.getLogger(__name__)


class ConversationEnhancer:
    """Enhances natural conversation quality."""
    
    def __init__(self):
        # Initialize language detection
        DetectorFactory.seed = 0
        
        # Initialize AssemblyAI for transcription
        self.aai_api_key = None
        self.transcription_config = {
            "language_detection": True,
            "speaker_labels": True,
            "sentiment_analysis": True
        }
        
        logger.info("ConversationEnhancer initialized")
    
    def set_assemblyai_api_key(self, api_key: str):
        """Set AssemblyAI API key for transcription services."""
        self.aai_api_key = api_key
        if api_key:
            aai.settings.api_key = api_key
            logger.info("AssemblyAI API key set")
    
    def detect_language(self, text: str) -> str:
        """Detect the language of text."""
        try:
            if not text or not text.strip():
                return "unknown"
            return detect(text)
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "unknown"
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text."""
        try:
            blob = TextBlob(text)
            return {
                "polarity": blob.sentiment.polarity,  # -1 to 1
                "subjectivity": blob.sentiment.subjectivity  # 0 to 1
            }
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return {"polarity": 0.0, "subjectivity": 0.5}
    
    def detect_endpoint(self, audio_data: np.ndarray, sample_rate: int = 16000,
                       threshold: float = 0.01, min_silence_duration: float = 0.5) -> bool:
        """Detect conversation endpoint (when speaker has finished)."""
        try:
            # Simple energy-based endpoint detection
            energy = np.mean(np.abs(audio_data))
            
            # Check if energy is below threshold
            if energy < threshold:
                # Check duration of silence (simplified)
                return True
            
            return False
        except Exception as e:
            logger.warning(f"Endpoint detection failed: {e}")
            return False
    
    def suppress_noise(self, audio_data: np.ndarray, sample_rate: int = 16000,
                      stationary: bool = True, prop_decrease: float = 0.8) -> np.ndarray:
        """Apply noise suppression to audio data."""
        try:
            if len(audio_data) == 0:
                return audio_data
            
            # Apply noise reduction
            reduced_noise = nr.reduce_noise(
                y=audio_data,
                sr=sample_rate,
                stationary=stationary,
                prop_decrease=prop_decrease
            )
            
            return reduced_noise
        except Exception as e:
            logger.warning(f"Noise suppression failed: {e}")
            return audio_data
    
    def generate_backchannel_response(self, context: str, emotion: str = "neutral") -> str:
        """Generate appropriate backchannel responses."""
        try:
            # Simple backchannel responses based on context and emotion
            backchannels = {
                "neutral": ["I see", "Understood", "Got it", "Right", "Okay"],
                "positive": ["That's great", "Wonderful", "Excellent", "Nice", "Good"],
                "negative": ["I understand", "That's tough", "I see", "Hmm", "Okay"],
                "question": ["Good question", "Let me think", "Interesting", "Hmm", "Let me see"]
            }
            
            # Detect if it's a question
            if context.strip().endswith('?'):
                emotion = "question"
            
            # Get appropriate responses
            responses = backchannels.get(emotion.lower(), backchannels["neutral"])
            
            # Simple context-aware selection
            if "problem" in context.lower() or "issue" in context.lower():
                return responses[0] if responses else "I see"
            else:
                return np.random.choice(responses) if responses else "I see"
                
        except Exception as e:
            logger.warning(f"Backchannel generation failed: {e}")
            return "I see"
    
    def transcribe_audio(self, audio_file: str, language: str = None) -> Dict[str, Any]:
        """Transcribe audio using AssemblyAI."""
        try:
            if not self.aai_api_key:
                raise ValueError("AssemblyAI API key not set")
            
            # Configure transcription
            config = aai.TranscriptionConfig(
                language_detection=True,
                speaker_labels=True,
                sentiment_analysis=True
            )
            
            if language:
                config.language_code = language
            
            # Transcribe the file
            transcoder = aai.Transcriber()
            transcript = transcoder.transcribe(audio_file, config)
            
            return {
                "text": transcript.text,
                "language": transcript.language_code,
                "speakers": transcript.utterances,
                "sentiment": transcript.sentiment_analysis,
                "confidence": transcript.confidence
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "error": str(e),
                "text": "",
                "language": "unknown",
                "speakers": [],
                "sentiment": None,
                "confidence": 0.0
            }
    
    def enhance_conversation_quality(self, audio_data: np.ndarray, 
                                    text: str = None) -> Dict[str, Any]:
        """Apply multiple enhancements to improve conversation quality."""
        result = {
            "noise_suppression_applied": False,
            "language_detected": "unknown",
            "sentiment": {"polarity": 0.0, "subjectivity": 0.5},
            "endpoint_detected": False,
            "backchannel_response": "",
            "enhanced_audio": audio_data,
            "enhanced_text": text or ""
        }
        
        try:
            # Apply noise suppression
            if len(audio_data) > 0:
                enhanced_audio = self.suppress_noise(audio_data)
                result["enhanced_audio"] = enhanced_audio
                result["noise_suppression_applied"] = True
            
            # Detect language if text is provided
            if text:
                result["language_detected"] = self.detect_language(text)
                result["sentiment"] = self.analyze_sentiment(text)
                result["enhanced_text"] = text
            
            # Detect endpoint
            if len(audio_data) > 0:
                result["endpoint_detected"] = self.detect_endpoint(audio_data)
            
            # Generate backchannel response
            if text:
                result["backchannel_response"] = self.generate_backchannel_response(text)
            
            return result
            
        except Exception as e:
            logger.error(f"Conversation enhancement failed: {e}")
            return result
    
    def real_time_enhancement(self, audio_chunk: np.ndarray, 
                             sample_rate: int = 16000) -> Dict[str, Any]:
        """Real-time conversation enhancement for streaming audio."""
        try:
            # Apply noise suppression
            enhanced_audio = self.suppress_noise(audio_chunk)
            
            # Detect endpoint
            endpoint_detected = self.detect_endpoint(enhanced_audio)
            
            return {
                "enhanced_audio": enhanced_audio,
                "endpoint_detected": endpoint_detected,
                "audio_energy": float(np.mean(np.abs(enhanced_audio))),
                "chunk_duration": len(enhanced_audio) / sample_rate
            }
            
        except Exception as e:
            logger.error(f"Real-time enhancement failed: {e}")
            return {
                "enhanced_audio": audio_chunk,
                "endpoint_detected": False,
                "audio_energy": 0.0,
                "chunk_duration": 0.0
            }
    
    def shutdown(self):
        """Clean up resources."""
        logger.info("ConversationEnhancer shutdown complete")


# Example usage and testing
if __name__ == "__main__":
    import logging
    import numpy as np
    logging.basicConfig(level=logging.INFO)
    
    # Create conversation enhancer
    enhancer = ConversationEnhancer()
    
    # Example: Test language detection
    text = "ARCHER is an advanced AI assistant for Windows systems."
    language = enhancer.detect_language(text)
    sentiment = enhancer.analyze_sentiment(text)
    print(f"Text: {text}")
    print(f"Language: {language}")
    print(f"Sentiment: {sentiment}")
    
    # Example: Test backchannel responses
    backchannel = enhancer.generate_backchannel_response(text)
    print(f"Backchannel response: {backchannel}")
    
    # Example: Test noise suppression (with dummy audio)
    dummy_audio = np.random.randn(16000) * 0.1  # Low amplitude audio
    enhanced_audio = enhancer.suppress_noise(dummy_audio)
    endpoint = enhancer.detect_endpoint(dummy_audio)
    print(f"Audio enhanced: {len(enhanced_audio)} samples")
    print(f"Endpoint detected: {endpoint}")
    
    # Example: Test conversation enhancement
    enhancement_result = enhancer.enhance_conversation_quality(dummy_audio, text)
    print(f"\nEnhancement result:")
    print(f"  Noise suppression: {enhancement_result['noise_suppression_applied']}")
    print(f"  Language: {enhancement_result['language_detected']}")
    print(f"  Sentiment: {enhancement_result['sentiment']}")
    print(f"  Backchannel: {enhancement_result['backchannel_response']}")
    
    # Shutdown
    enhancer.shutdown()