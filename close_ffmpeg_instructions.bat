@echo off
echo ===============================================
echo   ARCHER - Close FFmpeg Process
echo ===============================================
echo.
echo CURRENT STATUS: ffmpeg.exe is running (PID 10124)
echo.
echo TO CLOSE FFMPEG, RUN THIS COMMAND AS ADMINISTRATOR:
echo.
echo taskkill /F /IM ffmpeg.exe
echo.
echo ALTERNATIVE: Use Task Manager
echo 1. Ctrl+Shift+Esc
echo 2. Find ffmpeg.exe
echo 3. End Task
echo.
echo AFTER CLOSING:
echo 1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full-shared.7z
echo 2. Extract to: C:\Tools\ffmpeg\ (replace existing)
echo 3. Launch: launch_archer_ffmpeg_path.bat
echo 4. Test TTS!
echo.
pause