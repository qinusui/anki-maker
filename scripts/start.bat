@echo off
echo ========================================
echo Anki Card Generator - Start All
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
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js not found
    echo Please install Node.js: https://nodejs.org/
    deactivate
    pause
    exit /b 1
)

REM Run start-all.py (handles everything else)
python scripts\start-all.py

deactivate
exit
