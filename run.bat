@echo off

rem 灵犀智能助手启动脚本

rem 清理占用5000端口的服务
netstat -ano | findstr :5000 > nul
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
        taskkill /f /pid %%a > nul 2>&1
    )
    echo 已清理占用5000端口的服务
)

rem 清理占用5173端口的服务
netstat -ano | findstr :5173 > nul
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173') do (
        taskkill /f /pid %%a > nul 2>&1
    )
    echo 已清理占用5173端口的服务
)

echo 正在启动后端服务...
start "灵犀后端服务" cmd /k "python -m lingxi --web"

rem 等待2秒
ping localhost -n 3 > nul

echo 正在启动前端服务...
start "灵犀前端服务" cmd /k "cd lingxi-desktop && npm run dev"

echo 服务启动完成！
echo 后端服务地址：http://localhost:5000
echo 前端服务地址：http://localhost:5173
echo 
echo 服务已在新窗口中启动
echo 关闭此窗口不会影响服务运行
echo 
echo 按任意键关闭...
pause > nul