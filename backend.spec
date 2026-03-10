# PyInstaller 配置文件 for 灵犀后端

import os
import sys
from pathlib import Path

# 获取项目根目录
# 使用固定路径，因为在 PyInstaller 处理 spec 文件时 __file__ 变量可能没有定义
project_root = os.path.abspath('.')

# 分析需要包含的模块和文件
analysis = Analysis(
    ['start_web_server.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        # 包含配置文件
        ('config.yaml', '.'),
        # 包含技能目录
        ('lingxi/skills', 'lingxi/skills'),
        # 包含其他必要的资源文件
    ],
    hiddenimports=[
        'lingxi.core.assistant.async_main',
        'lingxi.core.event.websocket_subscriber',
        'lingxi.web.routes.tasks',
        'lingxi.web.routes.checkpoints',
        'lingxi.web.routes.skills',
        'lingxi.web.routes.config',
        'lingxi.web.routes.sessions',
        'lingxi.web.routes.workspace',
        'lingxi.web.routes.resources',
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 创建可执行文件
pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=None)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name='lingxi-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台以便查看日志
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 创建分发目录
coll = COLLECT(
    executable,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lingxi-backend',
)
