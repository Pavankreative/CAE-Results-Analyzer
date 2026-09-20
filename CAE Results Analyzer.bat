@echo off
REM Launches CAE Results Analyzer as a desktop app.
REM %~dp0 is the folder this .bat file itself is sitting in, so double-clicking
REM it works no matter where the project folder is on this computer.
cd /d "%~dp0"
python desktop\desktop_app.py
if errorlevel 1 (
  echo.
  echo The application closed with an error. See the messages above.
  pause
)
