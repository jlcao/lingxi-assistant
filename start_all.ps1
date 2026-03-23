# 灵犀智能助手启动脚本 (PowerShell 版本)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "灵犀智能助手 - 一键启动脚本" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# 检查 Python 是否安装
Write-Host "检查 Python 安装..."
Try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python 版本: $pythonVersion"
} Catch {
    Write-Host "错误：未找到 Python。请先安装 Python 3.8+。" -ForegroundColor Red
    Read-Host "按 Enter 键退出..."
    Exit 1
}

# 检查 npm 是否安装
Write-Host "检查 npm 安装..."
Try {
    $npmVersion = npm --version 2>&1
    Write-Host "npm 版本: $npmVersion"
} Catch {
    Write-Host "错误：未找到 npm。请先安装 Node.js。" -ForegroundColor Red
    Read-Host "按 Enter 键退出..."
    Exit 1
}

Write-Host "" -ForegroundColor White
Write-Host "步骤 1：环境初始化" -ForegroundColor Green
Write-Host "--------------------" -ForegroundColor Green

# 检查并初始化 Python 虚拟环境
if (!(Test-Path "lingxi\.venv")) {
    Write-Host "正在创建 Python 虚拟环境..."
    cd lingxi
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误：虚拟环境创建失败。" -ForegroundColor Red
        Read-Host "按 Enter 键退出..."
        Exit 1
    }
    cd ..
    Write-Host "虚拟环境创建成功" -ForegroundColor Green
} else {
    Write-Host "虚拟环境已存在" -ForegroundColor Yellow
}

# 激活虚拟环境
Write-Host "正在激活 Python 虚拟环境..."
cd lingxi
.venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：虚拟环境激活失败。" -ForegroundColor Red
    Read-Host "按 Enter 键退出..."
    Exit 1
}
Write-Host "虚拟环境激活成功" -ForegroundColor Green

# 安装后端依赖
Write-Host "正在安装后端依赖..."
pip install -r ..\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：后端依赖安装失败。" -ForegroundColor Red
    Read-Host "按 Enter 键退出..."
    Exit 1
}
Write-Host "后端依赖安装成功" -ForegroundColor Green
cd ..

# 安装前端依赖
Write-Host "正在安装前端依赖..."
cd lingxi-desktop
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：前端依赖安装失败。" -ForegroundColor Red
    Read-Host "按 Enter 键退出..."
    Exit 1
}
Write-Host "前端依赖安装成功" -ForegroundColor Green
cd ..

Write-Host "环境初始化完成！" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "步骤 2：启动服务" -ForegroundColor Green
Write-Host "--------------------" -ForegroundColor Green

# 启动后端服务
Write-Host "正在启动后端服务..."
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -NoExit -Command cd lingxi; .venv\Scripts\Activate.ps1; Write-Host '后端服务启动中...' -ForegroundColor Cyan; python -m lingxi --web"

# 等待2秒让后端服务启动
Write-Host "等待后端服务启动..."
Start-Sleep -Seconds 2

# 启动前端开发模式
Write-Host "正在启动前端开发模式..."
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -NoExit -Command cd lingxi-desktop; Write-Host '前端服务启动中...' -ForegroundColor Cyan; npm run dev"

Write-Host "服务启动完成！" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "后端服务地址：http://localhost:5000" -ForegroundColor White
Write-Host "前端开发地址：http://localhost:5173" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "按 Enter 键关闭此窗口..." -ForegroundColor White
Read-Host