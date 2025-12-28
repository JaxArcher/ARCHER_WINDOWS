from collections import defaultdict
from typing import Callable, Any, DefaultDict, List
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.subscribers: DefaultDict[str, List[Callable]] = defaultdict(list)
            logger.info("EventBus singleton instance created.")
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe a callback function to a specific event type."""
        self.subscribers[event_type].append(callback)
        logger.info(f"Callback {callback.__name__} subscribed to event '{event_type}'")

    def publish(self, event_type: str, *args, **kwargs: Any):
        """Publish an event, calling all subscribed callbacks."""
        if event_type in self.subscribers:
            logger.info(f"Publishing event '{event_type}' with args: {args}, kwargs: {kwargs}")
            for callback in self.subscribers[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error executing callback for event '{event_type}': {e}", exc_info=True)

# Global instance for easy import and use across the application
bus = EventBus()