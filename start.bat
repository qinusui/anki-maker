@echo off
echo ========================================
echo Anki Card Generator - Start All
echo ========================================
echo.

REM Check if venv exists
if not exist .venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

echo [2/5] Checking Python...
python --version

REM Check Node.js
echo [3/5] Checking Node.js...
where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js not found
    echo Please install Node.js: https://nodejs.org/
    deactivate
    pause
    exit /b 1
)
node --version

REM Check frontend dependencies
echo.
echo [4/5] Checking frontend dependencies...
cd frontend
if not exist node_modules (
    echo Frontend dependencies not installed, installing now...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies
        cd ..
        deactivate
        pause
        exit /b 1
    )
)
echo Frontend dependencies ready
cd ..

echo.
echo [5/5] Starting services...
echo.
echo ========================================
echo Services starting...
echo   Backend API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend UI: http://localhost:5173
echo ========================================
echo.
echo TIP: If browser does not open automatically, visit http://localhost:5173
echo.
echo Press Ctrl+C to stop all services
echo ----------------------------------------
echo.

REM Start backend in new window with activated venv
start "Anki Backend" cmd /k "call .venv\Scripts\activate.bat && cd backend && python main.py"

REM Wait a bit for backend to start
timeout /t 2 /nobreak >nul

REM Start frontend
cd frontend
start "Anki Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo Two services started in separate windows
echo Backend window: "Anki Backend"
echo Frontend window: "Anki Frontend"
echo ========================================
echo.
echo To stop services, close the above two windows
echo.

deactivate
pause
