@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo Anki Card Generator - Start All
echo ========================================
echo.

REM Switch to project root directory
cd /d "%~dp0\.."

REM Check if venv exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/5] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

REM Check Python
echo [2/5] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python check failed
    pause
    exit /b 1
)
echo.

REM Check Node.js
echo [3/5] Checking Node.js...
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found
    echo Please install Node.js: https://nodejs.org/
    deactivate
    pause
    exit /b 1
)
node --version
echo.

REM Install backend dependencies
echo [4/5] Installing backend dependencies...
pip install -r requirements.txt -q
pip install -r backend\requirements.txt -q
echo Backend dependencies installed
echo.

REM Install frontend dependencies
echo [5/5] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies
        cd ..
        deactivate
        pause
        exit /b 1
    )
    cd ..
    echo Frontend dependencies installed
) else (
    echo Frontend dependencies already installed
)
echo.

echo ========================================
echo Starting all services...
echo ========================================
echo.

REM Run start-all.py
python scripts\start-all.py

deactivate
exit
