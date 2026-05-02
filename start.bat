@echo off
echo ========================================
echo Anki Card Generator - Start All
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
echo [1/4] Python detected
python --version

REM Check Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Node.js not found
    echo Please install Node.js: https://nodejs.org/
    pause
    exit /b 1
)
echo [2/4] Node.js detected
node --version

REM Check frontend dependencies
echo.
echo [3/4] Checking frontend dependencies...
cd frontend
if not exist node_modules (
    echo Frontend dependencies not installed, installing now...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
)
echo Frontend dependencies ready
cd ..

echo.
echo [4/4] Starting services...
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

REM Start backend in new window
start "Anki Backend" cmd /k "cd backend && python main.py"

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

pause
