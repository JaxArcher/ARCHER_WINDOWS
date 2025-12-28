@echo off
echo ===============================================
echo   ARCHER - Rename FFmpeg Folders
echo ===============================================
echo.
echo PROBLEM: You have ffmpeg-full folder, need to replace C:\Tools\ffmpeg
echo.
echo SOLUTION STEPS:
echo.
echo 1. Rename current ffmpeg folder:
echo    rename C:\Tools\ffmpeg C:\Tools\ffmpeg_old
echo.
echo 2. Rename new folder:
echo    rename C:\Tools\ffmpeg-full C:\Tools\ffmpeg
echo.
echo 3. Verify new installation:
echo    C:\Tools\ffmpeg\bin\ffmpeg.exe -version | find "shared"
echo.
echo 4. Test ARCHER:
echo    launch_archer_ffmpeg_path.bat
echo.
echo This will fix the TorchCodec FFmpeg DLL issue!
echo.
pause