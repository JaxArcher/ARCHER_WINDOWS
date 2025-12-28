import os
import openwakeword
import numpy as np
import logging


class WakeWordDetector:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("WakeWord")
        self.model_paths = config.get("WAKE_WORD_MODEL_PATHS", "").split(",")
        self.threshold = float(config.get("WAKE_WORD_THRESHOLD", 0.5))
        self.oww = None

        self._load_models()

    def _load_models(self):
        self.logger.info("Loading wake word models...")
        paths = [p.strip() for p in self.model_paths if p.strip()]

        if not paths:
            self.logger.error("No wake word model paths provided in config")
            self.oww = None
            return

        # Check if model files exist
        missing_files = [p for p in paths if not os.path.exists(p)]
        if missing_files:
            self.logger.error(f"Wake word model files not found: {missing_files}")
            self.oww = None
            return

        try:
            # Try different initialization methods
            try:
                # FIX: Pass paths as the first positional argument
                self.oww = openwakeword.Model(
                    wakeword_models=paths, inference_framework="onnx"
                )
                self.logger.info(f"Successfully loaded models: {paths}")

            except TypeError as e:
                # Fallback for older versions that don't take kwargs
                self.logger.warning(
                    f"Standard init failed ({e}), trying positional only..."
                )
                self.oww = openwakeword.Model(paths)
                self.logger.info(f"Successfully loaded models with fallback: {paths}")

        except ImportError as e:
            self.logger.error(f"openWakeWord not installed: {e}")
            self.oww = None
        except Exception as e:
            self.logger.error(f"Failed to initialize openWakeWord: {e}")
            self.oww = None
            # Don't raise, just log so system can continue in text mode

    def process_frame(self, audio_frame):
        if self.oww is None:
            return None

        # openwakeword expects int16 numpy array
        prediction = self.oww.predict(audio_frame)

        for model_name, score in prediction.items():
            if score > self.threshold:
                self.logger.info(
                    f"Wake word detected: {model_name} (Score: {score:.2f})"
                )
                return model_name

        return None
