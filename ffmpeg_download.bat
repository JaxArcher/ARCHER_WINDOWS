@echo off
echo ===============================================
echo   ARCHER F5-TTS - FFmpeg Download Guide
echo ===============================================
echo.
echo REQUIRED: FFmpeg full-shared build (with DLLs)
echo.
echo DOWNLOAD LOCATION:
echo https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full-shared.7z
echo.
echo DIRECT LINK: ffmpeg-release-full-shared.7z (Version 7)
echo.
echo INSTALLATION:
echo 1. Download the file above
echo 2. Extract to: C:\Tools\ffmpeg\ (replace existing)
echo 3. Run: launch_archer_ffmpeg_path.bat
echo.
echo This will fix the TorchCodec FFmpeg DLL loading issue!
echo.
pause