"""
ARCHER TTS System - Windows Setup Script
Completes the Windows native setup with F5-TTS.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🚀 Setting up Windows Native ARCHER with F5-TTS...")
    
    # Set working directory
    os.chdir("D:/ARCHER_WINDOWS")
    
    # Step 1: Ensure proper virtual environment
    venv_path = Path("venv_f5tts")
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        result = subprocess.run([
            sys.executable, "-m", "venv", "venv_f5tts", "--system-site-packages"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Virtual environment created successfully")
        else:
            print(f"❌ Virtual environment creation failed: {result.stderr}")
            return 1
    
    # Step 2: Install F5-TTS in Windows venv
    print("📦 Installing F5-TTS in Windows environment...")
    activate_script = venv_path / "Scripts" / "activate.bat"
    
    pip_install = [
        f'"{venv_path / "Scripts" / "python.exe"}"',
        "-m", "pip", "install", "f5-tts", "librosa", "soundfile"
    ]
    
    result = subprocess.run(pip_install, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ F5-TTS installed in Windows environment")
    else:
        print(f"❌ F5-TTS installation failed: {result.stderr}")
        return 1
    
    # Step 3: Copy F5-TTS assets
    print("📋 Setting up F5-TTS assets...")
    assets_path = Path("assets")
    venv_assets = venv_path / "assets"
    venv_assets.mkdir(exist_ok=True)
    
    # Copy reference audio files if they exist in original
    original_assets = Path("/mnt/d/ARCHER_SWARM/venv_f5tts/lib/python3.12/site-packages/f5_tts/infer/examples")
    if original_assets.exists():
        print("📋 Copying F5-TTS reference audio files...")
        shutil.copytree(original_assets, venv_assets, dirs_exist_ok=True)
        print("✅ F5-TTS reference files copied")
    else:
        print("⚠️ Original F5-TTS assets not found, using defaults")
    
    # Step 4: Create Windows launcher
    launcher_content = """@echo off
echo 🚀 Starting ARCHER Windows Edition...
call "D:\\ARCHER_WINDOWS\\venv_f5tts\\Scripts\\activate.bat"
set PYTHONPATH=D:\\ARCHER_WINDOWS\\src;D:\\ARCHER_WINDOWS\\venv_f5tts\\lib\\site-packages
echo 🎯 F5-TTS Windows Native Ready!
python archer_gui.py
if errorlevel 1 (
    echo ❌ GUI startup failed
    pause
)
"""
    
    launcher_path = Path("archer_windows.bat")
    launcher_path.write_text(launcher_content)
    
    print("✅ Windows setup complete!")
    print("📁 Run: D:\\ARCHER_WINDOWS\\archer_windows.bat")
    print("🌐 Access: http://localhost:7860")
    print("🎉 ARCHER Windows Edition with F5-TTS is ready!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())