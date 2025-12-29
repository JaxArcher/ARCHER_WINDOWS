@echo off
echo 🚀 Installing ARCHER Automation Dependencies...
cd /d "D:\ARCHER_WINDOWS"

echo 📦 Installing core automation libraries...
venv_windows\Scripts\pip.exe install pyautogui psutil keyboard paramiko pynput

if errorlevel 1 (
    echo ❌ Core libraries installation failed
    pause
    exit /b 1
)

echo 📦 Installing remote access libraries...
venv_windows\Scripts\pip.exe install fastapi uvicorn python-multipart

if errorlevel 1 (
    echo ❌ Remote access libraries installation failed
    pause
    exit /b 1
)

echo 📦 Installing Windows-specific libraries...
venv_windows\Scripts\pip.exe install pywin32 pyscreeze

if errorlevel 1 (
    echo ❌ Windows libraries installation failed
    pause
    exit /b 1
)

echo 📦 Installing security libraries...
venv_windows\Scripts\pip.exe install cryptography bcrypt

if errorlevel 1 (
    echo ❌ Security libraries installation failed
    pause
    exit /b 1
)

echo 📦 Installing file management libraries...
venv_windows\Scripts\pip.exe install watchdog pywinrm

if errorlevel 1 (
    echo ❌ File management libraries installation failed
    pause
    exit /b 1
)

echo 📦 Installing testing libraries...
venv_windows\Scripts\pip.exe install pytest pytest-cov

if errorlevel 1 (
    echo ❌ Testing libraries installation failed
    pause
    exit /b 1
)

echo ✅ All automation dependencies installed successfully!
echo 🎉 ARCHER Automation system is ready for development!
pause