"""
构建 Whisper 插件包
创建独立 venv，安装 faster-whisper，打包为 zip 供 Inno Setup 使用。

用法: python scripts/build_whisper_plugin.py [--output-dir dist]
"""
import subprocess
import sys
import os
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PIP_SOURCES = [
    ("https://pypi.org/simple/", "pypi.org"),
    ("https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
    ("https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
]


def build_plugin(output_dir: Path):
    """构建 whisper 插件 venv"""
    plugin_dir = output_dir / "whisper_plugin"

    # 清理旧的
    if plugin_dir.exists():
        print(f"清理旧目录: {plugin_dir}")
        shutil.rmtree(plugin_dir)

    # 1. 创建 venv
    print("创建 Python venv...")
    subprocess.run(
        [sys.executable, "-m", "venv", str(plugin_dir)],
        check=True
    )

    # 获取 venv 中的 Python 和 pip
    if os.name == 'nt':
        venv_python = plugin_dir / "Scripts" / "python.exe"
        venv_pip = plugin_dir / "Scripts" / "pip.exe"
    else:
        venv_python = plugin_dir / "bin" / "python"
        venv_pip = plugin_dir / "bin" / "pip"

    # 2. 升级 pip
    print("升级 pip...")
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True, timeout=120
    )

    # 3. 安装 faster-whisper（尝试多个源）
    print("安装 faster-whisper...")
    installed = False
    for source_url, host in PIP_SOURCES:
        print(f"  尝试: {source_url}")
        try:
            result = subprocess.run(
                [str(venv_pip), "install", "faster-whisper",
                 "-i", source_url,
                 "--trusted-host", host,
                 "--timeout", "30"],
                capture_output=True, text=True, timeout=600
            )
            if result.returncode == 0:
                print("  安装成功!")
                installed = True
                break
            else:
                print(f"  失败: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print("  超时")

    if not installed:
        print("错误: 所有源均安装失败")
        sys.exit(1)

    # 4. 验证
    print("验证安装...")
    result = subprocess.run(
        [str(venv_python), "-c", "import faster_whisper; print('OK')"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"验证失败: {result.stderr}")
        sys.exit(1)

    # 5. 清理 venv 中不需要的文件减小体积
    print("清理不需要的文件...")
    _clean_venv(plugin_dir)

    # 6. 计算大小
    total_size = sum(f.stat().st_size for f in plugin_dir.rglob('*') if f.is_file())
    print(f"插件构建完成: {plugin_dir}")
    print(f"总大小: {total_size / 1024 / 1024:.1f} MB")

    return plugin_dir


def _clean_venv(plugin_dir: Path):
    """清理 venv 中的缓存和测试文件"""
    import stat

    def _remove_readonly(func, path, exc_info):
        """解除只读属性后重试删除"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    # 删除 __pycache__
    for d in plugin_dir.rglob("__pycache__"):
        shutil.rmtree(d, onerror=_remove_readonly, ignore_errors=True)
    # 删除测试目录
    for test_dir in plugin_dir.rglob("tests"):
        if test_dir.is_dir():
            shutil.rmtree(test_dir, onerror=_remove_readonly, ignore_errors=True)


def pack_zip(plugin_dir: Path, output_path: Path):
    """打包插件为 zip"""
    print(f"打包为 {output_path}...")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in plugin_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(plugin_dir.parent)
                zf.write(file, arcname)
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"压缩包大小: {size_mb:.1f} MB")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="构建 Whisper 插件")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "dist"),
                        help="输出目录")
    parser.add_argument("--zip", action="store_true",
                        help="同时生成 zip 压缩包")
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    plugin = build_plugin(output)

    if args.zip:
        zip_path = output / "whisper_plugin.zip"
        pack_zip(plugin, zip_path)
