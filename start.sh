#!/bin/bash

echo "========================================"
echo "Anki Card Generator - 一键启动"
echo "========================================"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未检测到 Node.js"
    echo "请先安装 Node.js: https://nodejs.org/"
    exit 1
fi

echo "✅ 检测到 Node.js"

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo "错误: 未检测到 npm"
    exit 1
fi

echo "✅ 检测到 npm"

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo ""
    echo "📦 前端依赖未安装，正在安装..."
    cd frontend
    npm install
    if [ $? -ne 0 ]; then
        echo "错误: 前端依赖安装失败"
        exit 1
    fi
    cd ..
    echo "✅ 前端依赖安装完成"
fi

echo ""
echo "🚀 启动服务..."
echo "   后端: http://localhost:8000"
echo "   前端: http://localhost:5173"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "----------------------------------------"

# 启动后端
cd backend
python main.py &
BACKEND_PID=$!

# 启动前端
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# 等待信号
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM

wait
