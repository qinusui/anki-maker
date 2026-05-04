"""
Whisper 动态管理模块
打包时不包含 whisper 和 torch，用户首次使用时自动下载安装
"""
import importlib
import subprocess
import sys
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def is_whisper_installed() -> bool:
    """检查 faster-whisper 是否已安装"""
    # 非打包环境：直接尝试导入
    if not getattr(sys, 'frozen', False):
        try:
            importlib.import_module("faster_whisper")
            return True
        except ImportError:
            return False

    # 打包环境：通过系统 Python 检查
    python_path = _find_python()
    if not python_path:
        return False
    try:
        result = subprocess.run(
            [python_path, "-c", "import faster_whisper; print('ok')"],
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


_PIP_SOURCES = [
    ("https://pypi.org/simple/", "pypi.org"),
    ("https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
    ("https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
]


def install_whisper() -> tuple[bool, str]:
    """
    安装 faster-whisper 及其依赖，自动尝试多个 pip 源
    返回 (是否安装成功, 错误信息)
    """
    python_path = _find_python()
    if not python_path:
        return False, "未找到系统 Python，请先安装 Python 3.8+"
    logger.info(f"Using Python for whisper install: {python_path}")

    last_error = ""
    for source_url, host in _PIP_SOURCES:
        logger.info(f"尝试从 {source_url} 安装...")
        try:
            result = subprocess.run(
                [
                    python_path, "-m", "pip", "install",
                    "faster-whisper",
                    "-i", source_url,
                    "--trusted-host", host,
                    "--timeout", "30",
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                return True, ""
            last_error = result.stderr[:500] or "pip install 失败"
            logger.warning(f"从 {source_url} 安装失败: {last_error}")
        except subprocess.TimeoutExpired:
            last_error = f"从 {source_url} 安装超时"
            logger.warning(last_error)
        except FileNotFoundError:
            return False, f"Python 路径无效: {python_path}"
        except Exception as e:
            last_error = str(e)[:500]
            logger.warning(f"从 {source_url} 安装异常: {last_error}")

    return False, f"所有源均安装失败，最后错误: {last_error}"


def get_whisper() -> Optional[Any]:
    """
    获取 faster_whisper 模块
    如果未安装返回 None
    """
    try:
        return importlib.import_module("faster_whisper")
    except ImportError:
        return None


def load_model(model_name: str = "base") -> Optional[Any]:
    """
    加载 faster-whisper WhisperModel
    如果未安装返回 None
    """
    faster_whisper = get_whisper()
    if faster_whisper is None:
        return None
    return faster_whisper.WhisperModel(model_name)
