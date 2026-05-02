#!/bin/bash

echo "========================================"
echo "Anki Card Generator - Backend Server"
echo "========================================"
echo ""

echo "[1/2] Installing backend dependencies..."
cd backend
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

echo ""
echo "[2/2] Starting FastAPI server..."
echo "API will be available at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
