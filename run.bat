@echo off
REM Research Agent Web Interface Startup Script (Windows)
REM This script starts the Flask web server for the Research Agent

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                      RESEARCH AGENT WEB INTERFACE                      ║
echo ║                          Starting server...                            ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ and try again
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing Flask and required dependencies...
    pip install -r requirements.txt
)

REM Start the Flask server
echo Starting Flask server on http://localhost:5000
echo.
echo Press CTRL+C to stop the server
echo.

python app.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start server
    pause
)
