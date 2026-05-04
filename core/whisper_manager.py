"""
Whisper 插件管理模块
主程序检测 whisper_plugin/ 目录是否存在来启用转录功能，
不再依赖系统 Python 的 pip 安装。
"""
import os
import sys
import subprocess
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def _get_install_dir() -> str:
    """获取安装目录（exe 所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_whisper_plugin_path() -> str:
    """获取 whisper 插件目录路径"""
    return os.path.join(_get_install_dir(), "whisper_plugin")


def whisper_available() -> bool:
    """检测 whisper 插件是否已安装"""
    plugin = get_whisper_plugin_path()
    # 检查 venv 中的 Python 和 faster_whisper 包
    if os.name == 'nt':
        python_path = os.path.join(plugin, "Scripts", "python.exe")
    else:
        python_path = os.path.join(plugin, "bin", "python")
    return os.path.isfile(python_path)


def _get_plugin_python() -> str:
    """获取插件 venv 中的 Python 路径"""
    plugin = get_whisper_plugin_path()
    if os.name == 'nt':
        return os.path.join(plugin, "Scripts", "python.exe")
    return os.path.join(plugin, "bin", "python")


def is_whisper_installed() -> bool:
    """检查 whisper 是否可用（安装包用插件检测，开发环境直接导入）"""
    # 非打包环境：直接尝试导入
    if not getattr(sys, 'frozen', False):
        try:
            import importlib
            importlib.import_module("faster_whisper")
            return True
        except ImportError:
            return False

    # 打包环境：通过插件 venv 检测
    if not whisper_available():
        return False
    python_path = _get_plugin_python()
    try:
        result = subprocess.run(
            [python_path, "-c", "import faster_whisper; print('ok')"],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def install_whisper() -> tuple[bool, str]:
    """
    安装 faster-whisper
    - 安装包模式：在插件 venv 内安装
    - 开发模式：在当前 Python 环境安装
    返回 (是否安装成功, 错误信息)
    """
    # 非打包环境：直接用当前 Python
    if not getattr(sys, 'frozen', False):
        python_path = sys.executable
    else:
        python_path = _get_plugin_python()
        if not os.path.isfile(python_path):
            return False, "Whisper 插件未安装，请先安装 ClipLingo_Whisper_Setup.exe"

    _PIP_SOURCES = [
        ("https://pypi.org/simple/", "pypi.org"),
        ("https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
        ("https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
    ]

    last_error = ""
    for source_url, host in _PIP_SOURCES:
        logger.info(f"尝试从 {source_url} 安装 faster-whisper...")
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "install",
                 "faster-whisper",
                 "-i", source_url,
                 "--trusted-host", host,
                 "--timeout", "30"],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode == 0:
                return True, ""
            last_error = result.stderr[:500] or "pip install 失败"
            logger.warning(f"从 {source_url} 安装失败: {last_error}")
        except subprocess.TimeoutExpired:
            last_error = f"从 {source_url} 安装超时"
        except Exception as e:
            last_error = str(e)[:500]

    return False, f"安装失败: {last_error}"


def get_whisper() -> Optional[Any]:
    """获取 faster_whisper 模块（非打包环境用）"""
    try:
        import importlib
        return importlib.import_module("faster_whisper")
    except ImportError:
        return None


def load_model(model_name: str = "base") -> Optional[Any]:
    """加载 faster-whisper WhisperModel"""
    faster_whisper = get_whisper()
    if faster_whisper is None:
        return None
    return faster_whisper.WhisperModel(model_name)
