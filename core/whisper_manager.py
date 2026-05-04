"""
Whisper 动态管理模块
打包时不包含 whisper 和 torch，用户首次使用时自动下载安装
"""
import importlib
import subprocess
import sys
from typing import Optional, Any


def is_whisper_installed() -> bool:
    """检查 whisper 是否已安装"""
    # 非打包环境：直接尝试导入
    if not getattr(sys, 'frozen', False):
        try:
            importlib.import_module("whisper")
            return True
        except ImportError:
            return False

    # 打包环境：通过系统 Python 检查
    python_path = _find_python()
    if not python_path:
        return False
    try:
        result = subprocess.run(
            [python_path, "-c", "import whisper; print('ok')"],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def _find_python() -> str:
    """查找可用的 Python 解释器路径"""
    import shutil
    import os

    # 非打包环境直接用当前解释器
    if not getattr(sys, 'frozen', False):
        return sys.executable

    # 打包环境：尝试多种方式找 Python
    # 1. PATH 中的 python
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found

    # 2. Windows py launcher
    if os.name == 'nt':
        py = shutil.which("py")
        if py:
            return py

    # 3. 常见安装路径
    if os.name == 'nt':
        import glob
        patterns = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python*\python.exe"),
            os.path.expandvars(r"%ProgramFiles%\Python*\python.exe"),
            os.path.expandvars(r"C:\Python*\python.exe"),
        ]
        for pattern in patterns:
            matches = sorted(glob.glob(pattern), reverse=True)
            if matches:
                return matches[0]

    return ""


def install_whisper() -> bool:
    """
    安装 whisper 及其依赖（CPU 版本）
    返回是否安装成功
    """
    python_path = _find_python()
    if not python_path:
        return False
    try:
        # 安装 openai-whisper，使用 PyTorch CPU 版本（约 200MB）
        subprocess.run(
            [
                python_path,
                "-m",
                "pip",
                "install",
                "openai-whisper",
                "--index-url",
                "https://download.pytorch.org/whl/cpu",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_whisper() -> Optional[Any]:
    """
    获取 whisper 模块
    如果未安装返回 None
    """
    try:
        return importlib.import_module("whisper")
    except ImportError:
        return None


def load_model(model_name: str = "base") -> Optional[Any]:
    """
    加载 whisper 模型
    如果 whisper 未安装返回 None
    """
    whisper = get_whisper()
    if whisper is None:
        return None
    return whisper.load_model(model_name)
