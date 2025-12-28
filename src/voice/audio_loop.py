import queue
import threading
import logging
import sounddevice as sd
import numpy as np

class AudioLoop:
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.stream = None
        self.logger = logging.getLogger("AudioLoop")

    def start(self):
        self.running = True
        # Basic audio config
        samplerate = 16000
        blocksize = 1280 # 80ms
        
        try:
            self.stream = sd.InputStream(
                samplerate=samplerate,
                blocksize=blocksize,
                channels=1,
                dtype='int16',
                callback=self._stream_callback
            )
            self.stream.start()
            self.logger.info("Audio stream started")
        except Exception as e:
            self.logger.error(f"Failed to start audio stream: {e}")
            self.running = False

    def _stream_callback(self, indata, frames, time, status):
        if status:
            self.logger.warning(f"Audio status: {status}")
        if self.running:
            self.callback(indata)

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
