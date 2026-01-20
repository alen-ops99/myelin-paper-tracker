#!/bin/bash
# Myelin Paper Research Assistant - Launch Script

cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Load environment variables
if [ -f ~/.env ]; then
    export $(grep -v '^#' ~/.env | xargs)
fi

# Start the server
echo ""
echo "================================================"
echo "  Myelin Paper Research Assistant"
echo "================================================"
echo ""
echo "  Open in browser: http://localhost:5050"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

python3 server.py
