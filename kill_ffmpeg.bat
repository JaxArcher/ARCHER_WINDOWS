@echo off
echo ===============================================
echo   ARCHER - Kill FFmpeg Process
echo ===============================================
echo.
echo DETECTED: ffmpeg.exe is running (PID 10124)
echo.
echo CLOSING FFmpeg process...
taskkill /F /IM ffmpeg.exe
echo.
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: FFmpeg process closed
    echo.
    echo You can now replace FFmpeg files!
    echo.
    echo Next steps:
    echo 1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full-shared.7z
    echo 2. Extract to: C:\Tools\ffmpeg\ (replace existing)
    echo 3. Launch: launch_archer_ffmpeg_path.bat
    echo 4. Test TTS!
) else (
    echo ERROR: Could not close FFmpeg process
    echo.
    echo Try these alternatives:
    echo 1. Task Manager: Ctrl+Shift+Esc, find ffmpeg.exe, End Task
    echo 2. Restart computer to clear all processes
    echo 3. Check if any video/audio apps are using FFmpeg
)
echo.
pause