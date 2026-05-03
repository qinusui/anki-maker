# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# 获取 frontend/dist 的绝对路径
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(SPEC)), 'frontend', 'dist')

a = Analysis(
    ['backend/main.py'],
    pathex=['backend', '.'],
    binaries=[
        ('bin/ffmpeg.exe', 'bin'),
        ('bin/ffprobe.exe', 'bin'),
    ],
    datas=[
        (frontend_dist, 'frontend/dist'),
        ('backend/static', 'backend/static'),
        ('core', 'core'),
    ],
    hiddenimports=[
        'api',
        'api.subtitles',
        'api.process',
        'api.cards',
        'models',
        'models.schemas',
        'services',
        'core',
        'core.ai_process',
        'core.media_cut',
        'core.pack_apkg',
        'core.parse_srt',
        'core.whisper_manager',
        'openai',
        'genanki',
        'pysrt',
        'dotenv',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'paddlepaddle', 'paddleocr', 'cv2', 'opencv',
        'whisper', 'openai-whisper',
        'torch', 'torchvision', 'torchaudio',
        'numpy', 'pandas', 'numba', 'llvmlite',
        'PIL', 'pillow',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='anki-maker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='anki-maker',
)
