@echo off

rem 获取脚本所在目录的绝对路径
set "SCRIPT_DIR=%~dp0"

rem 切换到脚本目录
cd "%SCRIPT_DIR%"

echo 灵犀智能助手启动器
echo ===================
echo 脚本目录: %SCRIPT_DIR%
echo 正在清理占用端口的服务...

rem 清理占用5000端口的服务（后端）
netstat -ano | findstr :5000 > kill5000.txt
for /f "tokens=5" %%a in (kill5000.txt) do (
    taskkill /f /pid %%a 2>nul
    if not errorlevel 1 echo 已杀掉占用5000端口的进程（PID: %%a）
)
del kill5000.txt 2>nul

rem 清理占用5173端口的服务（前端）
netstat -ano | findstr :5173 > kill5173.txt
for /f "tokens=5" %%a in (kill5173.txt) do (
    taskkill /f /pid %%a 2>nul
    if not errorlevel 1 echo 已杀掉占用5173端口的进程（PID: %%a）
)
del kill5173.txt 2>nul

echo 清理完成，正在启动服务...

rem 启动后端服务
start "灵犀后端服务" cmd /k "cd "%SCRIPT_DIR%" && python -m lingxi --web"

rem 等待2秒
ping localhost -n 3 >nul

rem 启动前端服务
start "灵犀前端服务" cmd /k "cd "%SCRIPT_DIR%lingxi-desktop" && npm run dev"

echo 服务启动完成！
echo 后端服务地址：http://localhost:5000
echo 前端服务地址：http://localhost:5173
echo 
echo 服务已在新窗口中启动
echo 关闭此窗口不会影响服务运行
echo 
echo 按任意键关闭...
pause >nul