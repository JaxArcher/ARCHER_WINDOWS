@echo off
echo 🚀 Starting ARCHER Windows Edition with F5-TTS...
cd /d "D:\ARCHER_WINDOWS"

:: Check if virtual environment exists, if not, create minimal one
if not exist "venv_windows" (
    echo 📦 Creating virtual environment...
    python -m venv venv_windows
)

:: Activate virtual environment (try Windows first, then Linux)
if exist "venv_windows\Scripts\activate.bat" (
    echo 🔧 Activating F5-TTS Windows environment...
    call "venv_windows\Scripts\activate.bat"
    set PYTHONPATH=D:\ARCHER_WINDOWS\src;D:\ARCHER_WINDOWS\venv_windows\Lib\site-packages
) else if exist "venv_windows\bin\activate" (
    echo 🔧 Activating F5-TTS Linux environment...
    call "venv_windows\bin\activate.bat"
    set PYTHONPATH=D:\ARCHER_WINDOWS\src;D:\ARCHER_WINDOWS\venv_windows\lib\python3.12\site-packages
) else (
    echo 🐍 No virtual Python found, trying system Python...
    set PYTHONPATH=D:\ARCHER_WINDOWS\src
)

echo ✅ Environment ready
echo 🎯 Starting ARCHER GUI with F5-TTS...

:: Start GUI with Windows-friendly paths
python archer_gui.py

if errorlevel 1 (
    echo ❌ GUI startup failed
    pause
) else (
    echo ✅ ARCHER GUI running!
    echo 🌐 Access at: http://localhost:7860
    echo 🎉 F5-TTS Windows Native Edition is ready!
)