@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo DEFINALYZER virtual environment was not found.
    echo Follow the setup instructions in README.md, then try again.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py dashboard
if errorlevel 1 (
    echo.
    echo The dashboard stopped with an error.
    pause
)
