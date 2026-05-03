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
    try:
        importlib.import_module("whisper")
        return True
    except ImportError:
        return False


def install_whisper() -> bool:
    """
    安装 whisper 及其依赖（CPU 版本）
    返回是否安装成功
    """
    try:
        # 安装 openai-whisper，使用 PyTorch CPU 版本（约 200MB）
        subprocess.run(
            [
                sys.executable,
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
