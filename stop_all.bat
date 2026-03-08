@echo off

echo =====================================
echo 灵犀智能助手 - 停止服务脚本
echo =====================================

rem 停止后端服务
echo 正在停止后端服务...
taskkill /FI "WINDOWTITLE eq 后端服务" /F 2>nul

rem 停止前端服务
echo 正在停止前端服务...
taskkill /FI "WINDOWTITLE eq 前端服务" /F 2>nul

echo 服务已停止！
echo.
echo 按任意键关闭此窗口...
pause >nul