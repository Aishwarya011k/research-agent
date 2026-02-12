#!/bin/bash

# Research Agent Web Interface Startup Script (Linux/macOS)
# This script starts the Flask web server for the Research Agent

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                      RESEARCH AGENT WEB INTERFACE                      ║"
echo "║                          Starting server...                            ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.9+ and try again"
    exit 1
fi

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Flask and required dependencies..."
    pip install -r requirements.txt
fi

# Start the Flask server
echo "Starting Flask server on http://localhost:5000"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python3 app.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to start server"
    exit 1
fi
