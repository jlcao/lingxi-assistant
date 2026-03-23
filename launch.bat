@echo off

chcp 65001 >nul

echo 灵犀智能助手 - 快速启动
echo ======================
echo 正在启动服务...

rem 启动后端服务
start "灵犀后端服务" cmd /c "cd lingxi && .venv\Scripts\activate && python -m lingxi --web"

rem 等待2秒
ping localhost -n 3 >nul

rem 启动前端服务
start "灵犀前端服务" cmd /c "cd lingxi-desktop && npm run dev"

echo 服务启动完成！
echo 后端：http://localhost:5000
echo 前端：http://localhost:5173
echo 
echo 服务已在新窗口中启动
echo 关闭此窗口不会影响服务运行
echo 
echo 按任意键关闭...
pause >nul