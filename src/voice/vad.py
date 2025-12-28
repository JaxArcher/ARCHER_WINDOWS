import logging

try:
    import webrtcvad

    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    logging.warning("webrtcvad not available - VAD functionality limited")


class VadGate:
    def __init__(self, aggressiveness=3):
        if WEBRTCVAD_AVAILABLE:
            self.vad = webrtcvad.Vad(aggressiveness)
        else:
            self.vad = None
            logging.warning(
                "VAD initialized without webrtcvad - speech detection disabled"
            )
        self.logger = logging.getLogger("VAD")

    def is_speech(self, frame_bytes, sample_rate):
        if self.vad is None:
            # Fallback: assume speech if webrtcvad not available
            return True

        try:
            return self.vad.is_speech(frame_bytes, sample_rate)
        except Exception as e:
            self.logger.debug(f"VAD processing error: {e}")
            return False
