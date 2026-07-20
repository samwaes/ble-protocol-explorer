@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found.
  echo Run the existing setup script first or create .venv and install requirements.txt.
  pause
  exit /b 1
)

echo.
echo Medisana BS430 Protocol Explorer
echo =================================
echo Close the VitaDock app and nRF Connect before starting.
echo Complete a normal weighing when the scanner is ready.
echo No write command is sent unless you explicitly type SEND and confirm YES.
echo.

".venv\Scripts\python.exe" tools\medisana_protocol_explorer.py

echo.
echo Session ended. Captures are stored under captures\private.
pause
