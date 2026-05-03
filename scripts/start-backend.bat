@echo off
echo ========================================
echo Anki Card Generator - Backend Server
echo ========================================
echo.

REM 切换到项目根目录
cd /d "%~dp0\.."

REM Check if venv exists
if not exist .venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

echo [2/4] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python check failed
    pause
    exit /b 1
)
echo.

echo [3/4] Installing backend dependencies...
cd backend
if not exist requirements.txt (
    echo ERROR: requirements.txt not found
    deactivate
    cd ..
    pause
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    deactivate
    cd ..
    pause
    exit /b 1
)
echo Dependencies installed
cd ..
echo.

echo [4/4] Starting FastAPI server...
echo.
echo ========================================
echo Backend will start at:
echo   API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
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
deactivate
