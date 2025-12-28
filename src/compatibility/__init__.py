"""
ARCHER Compatibility Module.

This package contains compatibility fixes and shims for various
library version mismatches and platform-specific issues.
"""

# Import compatibility fixes
from .torchaudio_fix import apply_torchaudio_compatibility_fix

# Apply all compatibility fixes automatically
apply_torchaudio_compatibility_fix()

__all__ = ['apply_torchaudio_compatibility_fix']