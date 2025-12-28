@echo off
echo ===============================================
echo   ARCHER - Manual FFmpeg Process Kill
echo ===============================================
echo.
echo DETECTED: ffmpeg.exe is running (PID 10124)
echo.
echo MANUAL STEPS TO CLOSE FFMPEG:
echo.
echo STEP 1: Open Task Manager
echo 1. Press: Ctrl + Shift + Esc
echo 2. Go to: Processes tab
echo 3. Find: ffmpeg.exe
echo 4. Right-click: End Task
echo.
echo STEP 2: Alternative - Command Prompt
echo 1. Open CMD as Administrator
echo 2. Type: taskkill /F /IM ffmpeg.exe
echo 3. Press Enter
echo.
echo STEP 3: Verify Closed
echo Run: tasklist | findstr ffmpeg
echo Should show: (no results)
echo.
echo AFTER CLOSING:
echo 1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full-shared.7z
echo 2. Extract to: C:\Tools\ffmpeg\ (replace existing)
echo 3. Launch: launch_archer_ffmpeg_path.bat
echo 4. Test: Type "Hello F5-TTS" + click Text to Speech
echo.
pause