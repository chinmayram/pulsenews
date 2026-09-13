@echo off
title PulseNews - Multi-Source News Aggregator
echo ===================================================
echo   PulseNews Multi-Source Aggregator & Dashboard
echo ===================================================
echo Checking Python environment...
python --version
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH! Please install Python 3.10+.
    pause
    exit /b 1
)

echo Installing / checking dependencies...
pip install -r requirements.txt

echo.
echo Starting PulseNews Server...
echo Press Ctrl+C to stop the server anytime.
echo.

python main.py
pause
