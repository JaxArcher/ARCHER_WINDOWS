@echo off
echo 🚀 Starting ARCHER Windows Edition with F5-TTS...
cd /d "D:\ARCHER_WINDOWS"

:: Try F5-TTS virtual environment first
if exist "venv_f5tss\Scripts\python.exe" (
    echo 🔧 Activating F5-TTS virtual environment...
    call "venv_f5tss\Scripts\activate.bat"
    set PYTHONPATH=D:\ARCHER_WINDOWS\src;D:\ARCHER_WINDOWS\venv_f5tss\lib\site-packages
    echo 🎯 Starting ARCHER GUI with F5-TTS...
    "D:\ARCHER_WINDOWS\venv_f5tss\Scripts\python.exe" archer_gui.py
    goto :success
) else (
    echo 📦 Creating minimal virtual environment...
    python -m venv venv_f5tss
    call "venv_f5tss\Scripts\activate.bat"
    set PYTHONPATH=D:\ARCHER_WINDOWS\src;D:\ARCHER_WINDOWS\venv_f5tss\lib\site-packages
    echo 🎯 Starting ARCHER GUI with F5-TTS...
    "D:\ARCHER_WINDOWS\venv_f5tss\Scripts\python.exe" archer_gui.py
)

:success
echo ✅ ARCHER GUI running!
echo 🌐 Access at: http://localhost:7860
echo 🎉 F5-TTS Windows Native Edition is ready!

pause