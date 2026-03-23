@echo off

chcp 65001 >nul

echo =====================================
echo 灵犀智能助手 - 一键启动脚本（调试版）
echo =====================================
echo 当前目录: %cd%
echo 脚本路径: %~dp0
echo.

rem 检查 Python 是否安装
echo 检查 Python 安装...
python --version
if %errorlevel% neq 0 (
    echo 错误：未找到 Python。请先安装 Python 3.8+。
    pause
    exit /b 1
)

echo Python 安装正常

rem 检查 npm 是否安装
echo 检查 npm 安装...
npm --version
if %errorlevel% neq 0 (
    echo 错误：未找到 npm。请先安装 Node.js。
    pause
    exit /b 1
)

echo npm 安装正常
echo.
echo 步骤 1：环境初始化
echo --------------------

rem 检查并初始化 Python 虚拟环境
if not exist "lingxi\.venv" (
    echo 正在创建 Python 虚拟环境...
    cd lingxi
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo 错误：虚拟环境创建失败。
        pause
        exit /b 1
    )
    cd ..
    echo 虚拟环境创建成功
) else (
    echo 虚拟环境已存在
)

rem 激活虚拟环境
echo 正在激活 Python 虚拟环境...
cd lingxi
call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo 错误：虚拟环境激活失败。
    pause
    exit /b 1
)
echo 虚拟环境激活成功

rem 安装后端依赖
echo 正在安装后端依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误：后端依赖安装失败。
    pause
    exit /b 1
)
echo 后端依赖安装成功
cd ..

rem 安装前端依赖
echo 正在安装前端依赖...
cd lingxi-desktop
npm install
if %errorlevel% neq 0 (
    echo 错误：前端依赖安装失败。
    pause
    exit /b 1
)
echo 前端依赖安装成功
cd ..

echo 环境初始化完成！
echo.
echo 步骤 2：启动服务
echo --------------------

rem 启动后端服务
echo 正在启动后端服务...
start "后端服务" cmd /k "cd lingxi && call .venv\Scripts\activate && echo 后端服务启动中... && python -m lingxi --web"

rem 等待2秒让后端服务启动
echo 等待后端服务启动...
timeout /t 2 /nobreak >nul

rem 启动前端开发模式
echo 正在启动前端开发模式...
start "前端服务" cmd /k "cd lingxi-desktop && echo 前端服务启动中... && npm run dev"

echo 服务启动完成！
echo.
echo 后端服务地址：http://localhost:5000
echo 前端开发地址：http://localhost:5173
echo.
echo 按任意键关闭此窗口...
pause >nul