@echo off
echo ===============================================
echo   ARCHER - Alternative FFmpeg Fix
echo ===============================================
echo.
echo SINCE YOU CAN'T RENAME THE FOLDER:
echo.
echo SOLUTION 1: Copy Shared DLLs to Existing Folder
echo 1. Copy all files from C:\Tools\ffmpeg-full\bin\*.dll
echo 2. Paste them into C:\Tools\ffmpeg\bin\
echo 3. Overwrite when prompted
echo.
echo SOLUTION 2: Add New Folder to PATH
echo 1. Set PATH=C:\Tools\ffmpeg-full\bin;%PATH%
echo 2. Use launch_archer_ffmpeg_path.bat
echo.
echo SOLUTION 3: Use New Folder Directly
echo 1. Edit launch_archer_ffmpeg_path.bat
echo 2. Change: set FFMPEG_BIN=C:\Tools\ffmpeg-full\bin
echo.
echo Try SOLUTION 1 first - copy the DLL files!
echo.
pause