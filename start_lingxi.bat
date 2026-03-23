@echo off

echo 启动灵犀智能助手...

rem 启动后端服务
start cmd /k "python -m lingxi --web"

rem 等待2秒
ping localhost -n 3 > nul

rem 启动前端服务
start cmd /k "cd lingxi-desktop && npm run dev"

echo 服务启动完成！
echo 后端服务地址：http://localhost:5000
echo 前端服务地址：http://localhost:5173
echo 
echo 按任意键关闭...
pause > nul