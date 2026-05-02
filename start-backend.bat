@echo off
echo ========================================
echo Anki Card Generator - Backend Server
echo ========================================
echo.

REM Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python: https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Checking Python environment...
python --version
if errorlevel 1 (
    echo ERROR: Python version check failed
    pause
    exit /b 1
)
echo.

echo [2/3] Installing backend dependencies...
cd backend
if not exist requirements.txt (
    echo ERROR: requirements.txt not found
    cd ..
    pause
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    cd ..
    pause
    exit /b 1
)
echo Dependencies installed
echo.

echo [3/3] Starting FastAPI server...
echo.
echo ========================================
echo Backend will start at:
echo   API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py

REM If backend exits with error
if errorlevel 1 (
    echo.
    echo ========================================
    echo Backend server exited with error
    echo ========================================
    pause
)

cd ..
