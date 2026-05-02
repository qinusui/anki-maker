@echo off
echo ========================================
echo Anki Card Generator - 一键启动
echo ========================================
echo.

REM 检查 Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo 错误: 未检测到 Node.js
    echo 请先安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/2] 检查前端依赖...
cd frontend
if not exist node_modules (
    echo 前端依赖未安装，正在安装...
    call npm install
    if errorlevel 1 (
        echo 错误: 前端依赖安装失败
        pause
        exit /b 1
    )
)
echo 前端依赖就绪

echo.
echo [2/2] 启动服务...
echo    后端: http://localhost:8000
echo    前端: http://localhost:5173
echo    API 文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止所有服务
echo ----------------------------------------

REM 使用 PowerShell 启动两个进程
powershell -Command "& { Start-Process python -ArgumentList 'main.py' -WorkingDirectory 'backend' -NoNewWindow; Start-Process npm -ArgumentList 'run','dev' -WorkingDirectory 'frontend' -NoNewWindow }"

REM 保持窗口打开
pause
