# PyInstaller 配置文件 for 灵犀后端
import os
import sys
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT, TOC

# ========== 核心优化1：稳定获取项目根目录 ==========
# 兼容 spec 文件在任意路径执行的情况
if '__file__' in locals():
    spec_file_dir = os.path.dirname(os.path.abspath(__file__))
else:
    spec_file_dir = os.path.abspath('.')
project_root = os.path.abspath(os.path.join(spec_file_dir, '.'))

# ========== 核心优化2：明确 Python 解释器路径（用于打包后技能执行） ==========
# 获取当前环境的 Python 解释器路径（打包时会包含到目录中）
python_exe_path = sys.executable
python_exe_name = os.path.basename(python_exe_path)

# 分析需要包含的模块和文件
analysis = Analysis(
    ['start_web_server.py'],
    pathex=[project_root],
    # ========== 核心优化3：包含 Python 解释器二进制文件 ==========
    binaries=[
        (python_exe_path, '.'),  # 将 Python 解释器复制到打包后的根目录
    ],
    datas=[
        # 包含配置文件
        ('config.yaml', '.'),
        # 包含技能目录（递归包含所有子目录和文件）
        ('lingxi/skills', 'lingxi/skills'),
        # 确保用户技能目录模板被包含（如果有）
        ('.lingxi/skills', '.lingxi/skills'),
        # 包含其他必要的静态资源（根据实际需求补充）
        # ('static', 'static'),
        # ('templates', 'templates'),
    ],
    hiddenimports=[
        # 项目核心模块
        'lingxi.core.assistant.async_main',
        'lingxi.core.event.websocket_subscriber',
        'lingxi.web.routes.tasks',
        'lingxi.web.routes.checkpoints',
        'lingxi.web.routes.skills',
        'lingxi.web.routes.config',
        'lingxi.web.routes.sessions',
        'lingxi.web.routes.workspace',
        'lingxi.web.routes.resources',
        # 第三方依赖
        'psutil',
        'yaml',
        'json',
        'importlib.util',
        'subprocess',
        'logging',
        'pathlib',
        'argparse',
        'tempfile',
        'pandas',         
        'pandas.core',    
        'pandas.io',       
        'numpy',          
        'pytz',            
        'tzdata',       
        'dateutil', 
        # 补充技能加载器需要的隐式导入
        'lingxi.skills.skill_loader',  # 确保技能加载器本身被包含
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的模块，减小打包体积
        'tkinter',
        'unittest',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,  # 关键：不压缩成单个归档，便于访问内部文件（包括解释器）
)

# 创建可执行文件
pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher=None,
)

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
    upx_exclude=[python_exe_name],  # 不对 Python 解释器做 UPX 压缩，避免损坏
    runtime_tmpdir=None,
    console=True,  # 保留控制台以便查看日志（调试必备）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 创建分发目录（--onedir 模式核心）
coll = COLLECT(
    executable,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[python_exe_name],  # 排除解释器的 UPX 压缩
    name='lingxi-backend',
)

# ========== 核心优化4：添加打包后路径验证钩子（可选） ==========
# 用于在打包完成后验证关键文件是否存在
def verify_build():
    build_dir = os.path.join(project_root, 'dist', 'lingxi-backend')
    # 验证 Python 解释器是否存在
    python_exe = os.path.join(build_dir, python_exe_name)
    if os.path.exists(python_exe):
        print(f"✅ Python 解释器已成功打包：{python_exe}")
    else:
        print(f"❌ 未找到 Python 解释器：{python_exe}")
    
    # 验证技能目录是否存在
    skills_dir = os.path.join(build_dir, 'lingxi', 'skills')
    if os.path.exists(skills_dir):
        print(f"✅ 技能目录已成功打包：{skills_dir}")
    else:
        print(f"❌ 未找到技能目录：{skills_dir}")

# 仅在直接执行 spec 文件时运行验证
if __name__ == '__main__':
    verify_build()