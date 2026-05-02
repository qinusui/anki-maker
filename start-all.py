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


def main():
    print("=" * 50)
    print("Anki 卡片生成器 - 一键启动")
    print("=" * 50)

    root_dir = Path(__file__).parent
    backend_dir = root_dir / 'backend'
    frontend_dir = root_dir / 'frontend'

    # 检查前端依赖
    if not (frontend_dir / 'node_modules').exists():
        print("\n前端依赖未安装，正在安装...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        print("前端依赖安装完成")

    print(f"\n后端: http://localhost:8000")
    print(f"前端: http://localhost:5173")
    print("\n关闭浏览器页面后 5 秒自动停止所有服务")
    print("按 Ctrl+C 可手动停止")
    print("-" * 50)

    processes = []
    pid_file = backend_dir / 'pids.json'

    try:
        # 启动后端（输出直接显示在当前终端）
        backend_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd=backend_dir,
        )
        processes.append(backend_process)

        # 启动前端
        frontend_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=frontend_dir,
        )
        processes.append(frontend_process)

        # 写入 PID 文件供后端自动停服使用
        pid_data = {
            'backend_pid': backend_process.pid,
            'frontend_pid': frontend_process.pid,
            'orchestrator_pid': os.getpid()
        }
        pid_file.write_text(json.dumps(pid_data))

        # 等待后端启动后自动打开浏览器
        time.sleep(3)
        webbrowser.open('http://localhost:5173')

        # 等待任意子进程结束
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(f"\n进程退出 (code={p.returncode})，正在停止所有服务...")
                    for proc in processes:
                        if proc.poll() is None:
                            proc.terminate()
                    pid_file.unlink(missing_ok=True)
                    sys.exit(1)
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n正在停止服务...")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        pid_file.unlink(missing_ok=True)
        print("所有服务已停止")


if __name__ == "__main__":
    main()
