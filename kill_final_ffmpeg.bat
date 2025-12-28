@echo off
echo ===============================================
echo   ARCHER - Kill Final FFmpeg Process
echo ===============================================
echo.
echo STILL DETECTED: ffmpeg.exe running (PID 54164)
echo.
echo RUN THIS IN YOUR ADMIN CMD PROMPT:
echo.
echo taskkill /F /PID 54164
echo.
echo OR (alternative):
echo taskkill /F /IM ffmpeg.exe
echo.
echo AFTER SUCCESS:
echo 1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full-shared.7z
echo 2. Extract to: C:\Tools\ffmpeg\ (replace existing)
echo 3. Verify: ffmpeg -version | find "shared"
echo 4. Launch: launch_archer_ffmpeg_path.bat
echo 5. Test TTS!
echo.
pause