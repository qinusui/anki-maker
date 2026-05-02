"""
一键启动后端和前端服务 — 关闭浏览器页面后自动停止所有服务
"""

import subprocess
import sys
import os
import json
import time
import webbrowser
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
        print("\n错误: 未检测到 Node.js")
        print("请先安装 Node.js: https://nodejs.org/")
        sys.exit(1)

    print("\n检测到 Node.js")

    # 检查 npm
    if not check_command('npm'):
        print("\n错误: 未检测到 npm")
        sys.exit(1)

    print("检测到 npm")

    # 检查前端依赖
    root_dir = Path(__file__).parent
    frontend_dir = root_dir / 'frontend'
    if not (frontend_dir / 'node_modules').exists():
        print("\n前端依赖未安装，正在安装...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        print("前端依赖安装完成")

    print("\n启动服务...")
    print("   后端: http://localhost:8000")
    print("   前端: http://localhost:5173")
    print("   API 文档: http://localhost:8000/docs")
    print("\n关闭浏览器页面后，服务将在 30 秒内自动停止")
    print("按 Ctrl+C 可手动停止所有服务")
    print("-" * 50)

    processes = []
    try:
        # 启动后端
        backend_dir = root_dir / 'backend'
        backend_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        processes.append(backend_process)

        # 启动前端
        frontend_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        processes.append(frontend_process)

        # 写入 PID 文件供后端关闭服务使用
        pid_file = backend_dir / 'pids.json'
        pid_data = {
            'backend_pid': backend_process.pid,
            'frontend_pid': frontend_process.pid,
            'orchestrator_pid': os.getpid()
        }
        pid_file.write_text(json.dumps(pid_data))

        # 等待后端启动后自动打开浏览器
        time.sleep(3)
        webbrowser.open('http://localhost:5173')

        # 监控进程状态
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(f"\n进程意外退出，退出码: {p.returncode}")
                    for proc in processes:
                        if proc.poll() is None:
                            proc.terminate()
                    pid_file.unlink(missing_ok=True)
                    sys.exit(1)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n正在停止服务...")
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

        # 清理 PID 文件
        pid_file = backend_dir / 'pids.json'
        pid_file.unlink(missing_ok=True)

        print("所有服务已停止")


if __name__ == "__main__":
    main()
