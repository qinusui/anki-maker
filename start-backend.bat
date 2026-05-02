@echo off
echo ========================================
echo Anki Card Generator - Backend Server
echo ========================================
echo.

REM 检查 Python 是否安装
where python >nul 2>nul
if errorlevel 1 (
    echo 错误: 未检测到 Python
    echo 请先安装 Python: https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误: Python 版本检查失败
    pause
    exit /b 1
)
echo.

echo [2/3] 安装后端依赖...
cd backend
if not exist requirements.txt (
    echo 错误: 找不到 requirements.txt 文件
    cd ..
    pause
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 依赖安装失败
    cd ..
    pause
    exit /b 1
)
echo 依赖安装完成
echo.

echo [3/3] 启动 FastAPI 服务器...
echo.
echo ========================================
echo 后端将启动在:
echo   API: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo ========================================
echo.
echo 按 Ctrl+C 停止服务器
echo.

python main.py

REM 如果后端退出，显示错误信息
if errorlevel 1 (
    echo.
    echo ========================================
    echo 后端服务异常退出
    echo ========================================
    pause
)

cd ..
