@echo off
echo ===============================================
echo   ARCHER - Close FFmpeg Process
echo ===============================================
echo.
echo Current running FFmpeg processes:
tasklist | findstr ffmpeg
echo.
echo To close FFmpeg safely:
echo.
echo OPTION 1: Task Manager
echo 1. Press Ctrl+Shift+Esc (Task Manager)
echo 2. Find "ffmpeg.exe" in Processes tab
echo 3. Right-click - End Task
echo.
echo OPTION 2: Command Prompt (Admin)
echo 1. Open Command Prompt as Administrator
echo 2. Run: taskkill /F /IM ffmpeg.exe
echo.
echo After closing FFmpeg, you can replace the files.
echo.
pause