@echo off
echo ===============================================
echo   ARCHER - Run Command to Kill FFmpeg
echo ===============================================
echo.
echo TO KILL FFMPEG PROCESS:
echo.
echo STEP 1: Open Command Prompt as Administrator
echo 1. Click Start button
echo 2. Type: cmd
echo 3. Right-click: Command Prompt
echo 4. Select: Run as administrator
echo.
echo STEP 2: Run the Kill Command
echo Copy-paste this line:
echo taskkill /F /IM ffmpeg.exe
echo Press Enter
echo.
echo STEP 3: Verify Success
echo Should see: SUCCESS: The process "ffmpeg.exe" has been terminated.
echo.
echo STEP 4: Continue with FFmpeg Replacement
echo 1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full-shared.7z
echo 2. Extract to: C:\Tools\ffmpeg\ (replace existing)
echo 3. Launch: launch_archer_ffmpeg_path.bat
echo 4. Test TTS!
echo.
pause