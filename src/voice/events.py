import logging
from enum import Enum, auto
from collections import defaultdict
from threading import RLock

class VoicePipelineEvent(Enum):
    """Defines events in the voice pipeline."""
    WAKE_WORD_DETECTED = auto()
    HALT_COMMAND_DETECTED = auto()
    AUTH_SUCCESS = auto()
    AUTH_FAILURE = auto()
    SESSION_STARTED = auto()
    SESSION_ENDED = auto()
    AUDIO_CHUNK_PROCESSED = auto() # For passing audio data

class EventBus:
    """A simple thread-safe pub/sub event bus."""
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event_type: VoicePipelineEvent, callback):
        """Subscribe a callback to an event type."""
        with self._lock:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logging.debug(f"Subscribed {callback.__name__} to {event_type.name}")

    def unsubscribe(self, event_type: VoicePipelineEvent, callback):
        """Unsubscribe a callback from an event type."""
        with self._lock:
            try:
                self._subscribers[event_type].remove(callback)
                logging.debug(f"Unsubscribed {callback.__name__} from {event_type.name}")
            except ValueError:
                logging.warning(f"Attempted to unsubscribe a non-existent callback {callback.__name__} from {event_type.name}")

    def publish(self, event_type: VoicePipelineEvent, *args, **kwargs):
        """Publish an event to all subscribers."""
        with self._lock:
            if event_type not in self._subscribers:
                return
            
            # Avoid logging audio chunks for cleaner logs
            if event_type is not VoicePipelineEvent.AUDIO_CHUNK_PROCESSED:
                 logging.info(f"Publishing event: {event_type.name}")

            for callback in self._subscribers[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Error in callback for event {event_type.name}: {e}", exc_info=True)

# Global instance
event_bus = EventBus()