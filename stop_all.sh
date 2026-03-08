#!/bin/bash

echo "====================================="
echo "灵犀智能助手 - 停止服务脚本"
echo "====================================="

# 停止后端服务
echo "正在停止后端服务..."
pkill -f "python3 -m lingxi --web" 2> /dev/null

# 停止前端服务
echo "正在停止前端服务..."
pkill -f "npm run dev" 2> /dev/null

echo "服务已停止！"
echo ""
echo "按任意键关闭此窗口..."
read -n 1 -s