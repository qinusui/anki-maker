@echo off
echo ========================================
echo Anki Card Generator - 一键启动
echo ========================================
echo.

REM 检查 Python
where python >nul 2>nul
if errorlevel 1 (
    echo 错误: 未检测到 Python
    echo 请先安装 Python: https://www.python.org/
    pause
    exit /b 1
)
echo [1/4] 检测到 Python
python --version

REM 检查 Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo.
    echo 错误: 未检测到 Node.js
    echo 请先安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
)
echo [2/4] 检测到 Node.js
node --version

REM 检查前端依赖
echo.
echo [3/4] 检查前端依赖...
cd frontend
if not exist node_modules (
    echo 前端依赖未安装，正在安装...
    call npm install
    if errorlevel 1 (
        echo 错误: 前端依赖安装失败
        cd ..
        pause
        exit /b 1
    )
)
echo 前端依赖就绪
cd ..

echo.
echo [4/4] 启动服务...
echo.
echo ========================================
echo 服务启动中...
echo   后端 API: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo   前端界面: http://localhost:5173
echo ========================================
echo.
echo 提示: 如果浏览器没有自动打开，请手动访问 http://localhost:5173
echo.
echo 按 Ctrl+C 停止所有服务
echo ----------------------------------------
echo.

REM 启动后端（在新窗口中）
start "Anki Backend" cmd /k "cd backend && python main.py"

REM 等待一下让后端先启动
timeout /t 2 /nobreak >nul

REM 启动前端
cd frontend
start "Anki Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo 两个服务已在独立窗口中启动
echo 后端窗口: "Anki Backend"
echo 前端窗口: "Anki Frontend"
echo ========================================
echo.
echo 如果需要停止服务，请关闭上述两个窗口
echo.

REM 等待用户按键
pause
