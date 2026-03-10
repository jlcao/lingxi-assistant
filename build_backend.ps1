# 构建灵犀后端
$PROJECT_ROOT = $PSScriptRoot
$DIST_DIR = Join-Path $PROJECT_ROOT "dist"
$FRONTEND_DIR = Join-Path $PROJECT_ROOT "lingxi-desktop\electron\main\backend"

# 清理之前的构建
if (Test-Path $DIST_DIR) {
    Remove-Item -Path $DIST_DIR -Recurse -Force
}

if (Test-Path $FRONTEND_DIR) {
    Remove-Item -Path $FRONTEND_DIR -Recurse -Force
}

# 安装依赖
pip install -r "$PROJECT_ROOT\requirements.txt"
pip install pyinstaller

# 使用 PyInstaller 构建后端
pyinstaller "$PROJECT_ROOT\backend.spec"

# 创建前端后端目录
New-Item -ItemType Directory -Path $FRONTEND_DIR -Force

# 复制构建结果到前端
Copy-Item -Path "$DIST_DIR\lingxi-backend\*" -Destination $FRONTEND_DIR -Recurse -Force

Write-Host "后端构建完成并复制到前端项目中"
Write-Host "构建结果位于: $FRONTEND_DIR"
