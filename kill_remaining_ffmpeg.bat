@echo off
echo ===============================================
echo   ARCHER - Kill Remaining FFmpeg Process
echo ===============================================
echo.
echo DETECTED: Another ffmpeg.exe is still running (PID 49500)
echo.
echo RUN THIS COMMAND IN YOUR ADMIN CMD PROMPT:
echo.
echo taskkill /F /PID 49500
echo.
echo ALTERNATIVE (if above fails):
echo taskkill /F /IM ffmpeg.exe
echo.
echo AFTER SUCCESS:
echo 1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full-shared.7z
echo 2. Extract to: C:\Tools\ffmpeg\ (replace existing)
echo 3. Launch: launch_archer_ffmpeg_path.bat
echo 4. Test TTS!
echo.
echo You already killed one FFmpeg process - just one more to go!
pause