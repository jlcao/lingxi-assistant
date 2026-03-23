@echo off

chcp 65001 >nul

echo 灵犀智能助手 - 简易启动脚本
echo ============================
echo 正在启动后端服务...

rem 启动后端服务
start "后端服务" cmd /k "cd lingxi && call .venv\Scripts\activate && echo 后端服务启动中... && python -m lingxi --web"

rem 等待3秒
ping localhost -n 4 >nul

echo 正在启动前端服务...

rem 启动前端服务
start "前端服务" cmd /k "cd lingxi-desktop && echo 前端服务启动中... && npm run dev"

echo 服务启动完成！
echo 后端服务：http://localhost:5000
echo 前端服务：http://localhost:5173
echo 
echo 按任意键关闭此窗口...
pause