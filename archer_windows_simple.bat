@echo off
echo 🚀 Starting ARCHER Windows Edition...
cd /d "D:\ARCHER_WINDOWS"

:: Try to find and use Python
if exist "D:\ARCHER_WINDOWS\venv_f5tss\Scripts\python.exe" (
    echo 🤖 Using F5-TTS virtual environment...
    "D:\ARCHER_WINDOWS\venv_f5tss\Scripts\python.exe" archer_gui.py
) else (
    echo 🐍 No virtual Python found, trying system Python...
    python archer_gui.py
)

if errorlevel 1 (
    echo ❌ GUI startup failed
    pause
) else (
    echo ✅ ARCHER GUI running!
    echo 🌐 Access at: http://localhost:7860
)