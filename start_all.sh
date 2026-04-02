#!/bin/bash

echo "====================================="
echo "灵犀智能助手 - 一键启动脚本"
echo "====================================="

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 Python。请先安装 Python 3.8+。"
    read -p "按任意键退出..."
    exit 1
fi

# 检查 npm 是否安装
if ! command -v npm &> /dev/null; then
    echo "错误：未找到 npm。请先安装 Node.js。"
    read -p "按任意键退出..."
    exit 1
fi

echo "步骤 1：环境初始化"
echo "--------------------"

# 检查并初始化 Python 虚拟环境
if [ ! -d "lingxi/.venv" ]; then
    echo "正在创建 Python 虚拟环境..."
    cd lingxi
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "错误：虚拟环境创建失败。"
        read -p "按任意键退出..."
        exit 1
    fi
    cd ..
fi

# 激活虚拟环境
echo "正在激活 Python 虚拟环境..."
source lingxi/.venv/bin/activate
if [ $? -ne 0 ]; then
    echo "错误：虚拟环境激活失败。"
    read -p "按任意键退出..."
    exit 1
fi

# 安装后端依赖
echo "正在安装后端依赖..."
cd lingxi
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误：后端依赖安装失败。"
    read -p "按任意键退出..."
    exit 1
fi
cd ..

# 安装前端依赖
echo "正在安装前端依赖..."
cd lingxi-desktop
npm install
if [ $? -ne 0 ]; then
    echo "错误：前端依赖安装失败。"
    read -p "按任意键退出..."
    exit 1
fi
cd ..

echo "环境初始化完成！"
echo ""
echo "步骤 2：启动服务"
echo "--------------------"

# 启动后端服务
echo "正在启动后端服务..."
bash -c "source lingxi/.venv/bin/activate && cd lingxi && python3 -m lingxi --web" &

# 等待2秒让后端服务启动
sleep 2

# 启动前端开发模式
echo "正在启动前端开发模式..."
npm run dev --prefix lingxi-desktop &

echo "服务启动完成！"
echo ""
echo "后端服务地址：http://localhost:8000"
echo "前端开发地址：http://localhost:5173"
echo ""
echo "按任意键关闭此窗口..."
read -n 1 -s