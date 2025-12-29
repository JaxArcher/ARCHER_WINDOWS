"""
Call Transcription and Summarization Service

Handles real-time and batch transcription of calls/conversations
with speaker diarization and summarization capabilities.
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
import time

# Import external libraries
import assemblyai as aai
from langdetect import detect
from textblob import TextBlob

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """A segment of speech from a specific speaker."""
    speaker: str
    text: str
    start_time: float
    end_time: float
    confidence: float


@dataclass
class CallTranscript:
    """Complete transcript of a call."""
    transcript_id: str
    audio_file: str
    duration: float
    language: str
    speakers: List[str]
    segments: List[SpeakerSegment]
    summary: Optional[str] = None
    sentiment: Optional[Dict[str, Any]] = None
    timestamp: str = ""


class CallTranscriptionService:
    """Handles call transcription and summarization."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        if api_key:
            aai.settings.api_key = api_key
        
        self.transcripts_dir = Path("data/transcripts")
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("CallTranscriptionService initialized")
    
    def set_api_key(self, api_key: str):
        """Set AssemblyAI API key."""
        self.api_key = api_key
        aai.settings.api_key = api_key
        logger.info("AssemblyAI API key set")
    
    def transcribe_call(self, audio_file: str, 
                       language: str = None) -> CallTranscript:
        """Transcribe a call recording."""
        try:
            if not self.api_key:
                raise ValueError("AssemblyAI API key not set")
            
            # Configure transcription
            config = aai.TranscriptionConfig(
                speaker_labels=True,
                language_detection=True,
                sentiment_analysis=True
            )
            
            if language:
                config.language_code = language
            
            # Start transcription
            transcoder = aai.Transcriber()
            transcript = transcoder.transcribe(audio_file, config)
            
            # Process the transcript
            return self._process_transcript(transcript, audio_file)
            
        except Exception as e:
            logger.error(f"Call transcription failed: {e}")
            raise
    
    def _process_transcript(self, transcript, audio_file: str) -> CallTranscript:
        """Process AssemblyAI transcript into our format."""
        try:
            # Extract speaker segments
            segments = []
            speakers = set()
            
            for utterance in transcript.utterances:
                segment = SpeakerSegment(
                    speaker=utterance.speaker,
                    text=utterance.text,
                    start_time=utterance.start,
                    end_time=utterance.end,
                    confidence=utterance.confidence
                )
                segments.append(segment)
                speakers.add(utterance.speaker)
            
            # Generate transcript ID
            transcript_id = f"call_{int(time.time())}"
            
            # Create call transcript
            call_transcript = CallTranscript(
                transcript_id=transcript_id,
                audio_file=audio_file,
                duration=transcript.duration,
                language=transcript.language_code,
                speakers=list(speakers),
                segments=segments,
                summary=self._generate_summary(transcript.text),
                sentiment=self._analyze_sentiment(transcript.text),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # Save transcript
            self._save_transcript(call_transcript)
            
            return call_transcript
            
        except Exception as e:
            logger.error(f"Failed to process transcript: {e}")
            raise
    
    def _generate_summary(self, text: str) -> str:
        """Generate a summary of the call."""
        try:
            if not text or len(text.strip()) == 0:
                return "No content to summarize"
            
            # Simple summary: first few sentences
            sentences = text.split('.')[:3]
            summary = '. '.join(sentences) + '...'
            
            # Add sentiment info
            sentiment = self._analyze_sentiment(text)
            polarity_desc = "positive" if sentiment['polarity'] > 0.1 else "negative" if sentiment['polarity'] < -0.1 else "neutral"
            
            summary += f"\n\nSentiment: {polarity_desc} (polarity: {sentiment['polarity']:.2f})"
            
            return summary
            
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return "Summary generation failed"
    
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of the call."""
        try:
            blob = TextBlob(text)
            return {
                "polarity": blob.sentiment.polarity,
                "subjectivity": blob.sentiment.subjectivity
            }
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return {"polarity": 0.0, "subjectivity": 0.5}
    
    def _save_transcript(self, transcript: CallTranscript):
        """Save transcript to file."""
        try:
            transcript_data = {
                "transcript_id": transcript.transcript_id,
                "audio_file": transcript.audio_file,
                "duration": transcript.duration,
                "language": transcript.language,
                "speakers": transcript.speakers,
                "segments": [{
                    "speaker": seg.speaker,
                    "text": seg.text,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "confidence": seg.confidence
                } for seg in transcript.segments],
                "summary": transcript.summary,
                "sentiment": transcript.sentiment,
                "timestamp": transcript.timestamp
            }
            
            transcript_file = self.transcripts_dir / f"{transcript.transcript_id}.json"
            with open(transcript_file, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved transcript: {transcript_file}")
            
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
    
    def load_transcript(self, transcript_id: str) -> Optional[CallTranscript]:
        """Load a saved transcript."""
        try:
            transcript_file = self.transcripts_dir / f"{transcript_id}.json"
            
            if not transcript_file.exists():
                return None
            
            with open(transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct CallTranscript object
            segments = [
                SpeakerSegment(
                    speaker=seg["speaker"],
                    text=seg["text"],
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    confidence=seg["confidence"]
                ) for seg in data["segments"]
            ]
            
            return CallTranscript(
                transcript_id=data["transcript_id"],
                audio_file=data["audio_file"],
                duration=data["duration"],
                language=data["language"],
                speakers=data["speakers"],
                segments=segments,
                summary=data["summary"],
                sentiment=data["sentiment"],
                timestamp=data["timestamp"]
            )
            
        except Exception as e:
            logger.error(f"Failed to load transcript: {e}")
            return None
    
    def list_transcripts(self) -> List[Dict[str, Any]]:
        """List all saved transcripts."""
        try:
            transcripts = []
            
            for transcript_file in self.transcripts_dir.glob("*.json"):
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                transcripts.append({
                    "transcript_id": data["transcript_id"],
                    "audio_file": data["audio_file"],
                    "duration": data["duration"],
                    "language": data["language"],
                    "speakers": data["speakers"],
                    "timestamp": data["timestamp"],
                    "summary": data["summary"][:100] + "..." if data["summary"] else ""
                })
            
            # Sort by timestamp (newest first)
            transcripts.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return transcripts
            
        except Exception as e:
            logger.error(f"Failed to list transcripts: {e}")
            return []
    
    def search_transcripts(self, query: str) -> List[Dict[str, Any]]:
        """Search transcripts for specific content."""
        try:
            if not query or not query.strip():
                return []
            
            results = []
            
            for transcript_file in self.transcripts_dir.glob("*.json"):
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Search in summary and segments
                transcript_text = (data["summary" ] or "") + " ".join(
                    seg["text"] for seg in data["segments"]
                )
                
                if query.lower() in transcript_text.lower():
                    results.append({
                        "transcript_id": data["transcript_id"],
                        "audio_file": data["audio_file"],
                        "duration": data["duration"],
                        "language": data["language"],
                        "timestamp": data["timestamp"],
                        "match_context": transcript_text[:200] + "..."
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Transcript search failed: {e}")
            return []
    
    def delete_transcript(self, transcript_id: str) -> bool:
        """Delete a transcript."""
        try:
            transcript_file = self.transcripts_dir / f"{transcript_id}.json"
            
            if transcript_file.exists():
                transcript_file.unlink()
                logger.info(f"Deleted transcript: {transcript_id}")
                return True
            else:
                logger.warning(f"Transcript not found: {transcript_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to delete transcript: {e}")
            return False
    
    def get_transcript_stats(self) -> Dict[str, Any]:
        """Get statistics about transcripts."""
        try:
            total_transcripts = 0
            total_duration = 0.0
            languages = set()
            speakers_count = 0
            
            for transcript_file in self.transcripts_dir.glob("*.json"):
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                total_transcripts += 1
                total_duration += data["duration"]
                languages.add(data["language"])
                speakers_count += len(data["speakers"])
            
            return {
                "total_transcripts": total_transcripts,
                "total_duration_hours": total_duration / 3600,
                "languages": list(languages),
                "average_speakers_per_call": speakers_count / total_transcripts if total_transcripts > 0 else 0,
                "transcripts_dir": str(self.transcripts_dir)
            }
            
        except Exception as e:
            logger.error(f"Failed to get transcript stats: {e}")
            return {"error": str(e)}
    
    def shutdown(self):
        """Clean up resources."""
        logger.info("CallTranscriptionService shutdown complete")


# Example usage and testing
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Note: This example won't work without a valid AssemblyAI API key
    # and an actual audio file
    
    # Create transcription service
    # service = CallTranscriptionService("your_assemblyai_api_key")
    
    # For testing without API key, we'll just test the local methods
    service = CallTranscriptionService()
    
    # Test summary generation
    sample_text = """
    This is a sample call transcription. The customer called about 
    a technical issue with their software. The support agent helped 
    them resolve the problem quickly.
    """
    
    summary = service._generate_summary(sample_text)
    sentiment = service._analyze_sentiment(sample_text)
    
    print(f"Sample text: {sample_text}")
    print(f"\nGenerated summary: {summary}")
    print(f"Sentiment analysis: {sentiment}")
    
    # Test transcript management (without actual transcription)
    print(f"\nTranscripts directory: {service.transcripts_dir}")
    print(f"Current transcripts: {service.list_transcripts()}")
    
    # Test stats
    stats = service.get_transcript_stats()
    print(f"Transcript stats: {stats}")
    
    # Shutdown
    service.shutdown()
    
    print("\nNote: Full transcription functionality requires a valid AssemblyAI API key")