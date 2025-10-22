#!/bin/bash

# Simple script to run the local 3D model generation server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Default values
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo ""
echo "=========================================="
echo "Starting 3D Model Generation Server"
echo "=========================================="
echo "Host: $HOST"
echo "Port: $PORT"
echo ""

# Start the server
python3 app.py

