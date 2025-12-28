# Simple F5-TTS Configuration
# Disables voice cloning to avoid "Are you listening to me?" issue

[f5_tts]
# Use basic model instead of voice cloning
use_basic_model = true

# Reference settings (minimal)
ref_audio = ""
ref_text = ""

# Audio settings
device = "cuda" if os.environ.get('CUDA_AVAILABLE', '').lower() == 'true' else "cpu"
sample_rate = 24000
