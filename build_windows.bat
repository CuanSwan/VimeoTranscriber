@echo off
REM Builds a standalone Windows executable (dist\VimeoTranscriber.exe).
REM Run this on a Windows machine with Python 3.10+ installed.

python -m venv build_venv
call build_venv\Scripts\activate.bat

pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller --onefile --console --name VimeoTranscriber run.py

echo.
echo Build complete. VimeoTranscriber.exe is in the dist folder.
echo Remember to copy ffmpeg.exe next to it (see README.md) before
echo handing it to non-technical users.
pause
