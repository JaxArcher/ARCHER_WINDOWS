@echo off
echo ===============================================
echo   ARCHER F5-TTS - FFmpeg Fix Required
echo ===============================================
echo.
echo CURRENT ISSUE: You have FFmpeg essentials (static build)
echo REQUIRED: FFmpeg full-shared build with DLLs
echo.
echo SOLUTION: Download and install FFmpeg full-shared
echo.
echo Steps:
echo 1. Go to: https://ffmpeg.org/download.html#build-windows
echo 2. Find "Windows builds from gyan.dev"
echo 3. Download: ffmpeg-release-full-shared.7z (for version 7)
echo 4. Extract to: C:\Tools\ffmpeg (replace current)
echo 5. Run this launcher again
echo.
echo Current FFmpeg: essentials (static)
echo Required FFmpeg: full-shared (with DLLs)
echo.
echo Press any key to open FFmpeg download page...
start https://ffmpeg.org/download.html#build-windows
pause >nul