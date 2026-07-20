@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found.
  echo Create .venv and install requirements.txt first.
  pause
  exit /b 1
)

echo.
echo Medisana BS430 Reader
echo ======================
echo Close VitaDock and nRF Connect.
echo Temporarily disable Bluetooth on phones that may claim the scale.
echo Wait for Scanning, then complete a normal body-analysis weighing.
echo The reader will send the established BS430 time/request command.
echo Home Assistant is not accessed or changed.
echo.

".venv\Scripts\python.exe" tools\medisana_bs430_reader.py

echo.
echo Session ended. Results are stored under captures\private.
pause
