"""
Torchaudio compatibility module for ARCHER.

This module provides compatibility fixes for version mismatches between
torchaudio and SpeechBrain libraries.
"""

import torchaudio


def apply_torchaudio_compatibility_fix():
    """
    Apply compatibility fixes for torchaudio version mismatches.
    
    This function adds missing attributes to torchaudio that are expected
    by older versions of SpeechBrain but have been removed in newer
    versions of torchaudio.
    """
    # Check if list_audio_backends is missing (removed in torchaudio 2.0+)
    if not hasattr(torchaudio, 'list_audio_backends'):
        def dummy_list_audio_backends():
            """Enhanced dummy implementation that satisfies SpeechBrain requirements."""
            # Return a list with a valid backend name to prevent SpeechBrain warnings
            return ['soundfile']
        
        torchaudio.list_audio_backends = dummy_list_audio_backends
        return True
    
    return False


# Apply the fix automatically when this module is imported
apply_torchaudio_compatibility_fix()