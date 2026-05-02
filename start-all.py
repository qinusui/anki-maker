"""
一键启动后端和前端服务
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def check_command(cmd):
    """检查命令是否可用"""
    try:
        subprocess.run([cmd, '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def main():
    print("=" * 50)
    print("Anki 卡片生成器 - 一键启动")
    print("=" * 50)

    # 检查 Node.js
    if not check_command('node'):
        print("\n❌ 错误: 未检测到 Node.js")
        print("请先安装 Node.js: https://nodejs.org/")
        sys.exit(1)

    print("\n✅ 检测到 Node.js")

    # 检查 npm
    if not check_command('npm'):
        print("\n❌ 错误: 未检测到 npm")
        sys.exit(1)

    print("✅ 检测到 npm")

    # 检查前端依赖
    frontend_dir = Path(__file__).parent / 'frontend'
    if not (frontend_dir / 'node_modules').exists():
        print("\n📦 前端依赖未安装，正在安装...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        print("✅ 前端依赖安装完成")

    print("\n🚀 启动服务...")
    print("   后端: http://localhost:8000")
    print("   前端: http://localhost:5173")
    print("   API 文档: http://localhost:8000/docs")
    print("\n按 Ctrl+C 停止所有服务")
    print("-" * 50)

    try:
        # 启动后端
        backend_dir = Path(__file__).parent / 'backend'
        backend_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # 启动前端
        frontend_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # 等待进程
        processes = [backend_process, frontend_process]
        while True:
            # 检查进程状态
            for p in processes:
                if p.poll() is not None:
                    print(f"\n⚠️  进程意外退出，退出码: {p.returncode}")
                    for proc in processes:
                        if proc.poll() is None:
                            proc.terminate()
                    sys.exit(1)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  正在停止服务...")
        backend_process.terminate()
        frontend_process.terminate()

        # 等待进程结束
        backend_process.wait(timeout=5)
        frontend_process.wait(timeout=5)

        print("✅ 所有服务已停止")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
