@echo off
chcp 936 >nul 2>&1  :: 强制设置为GBK编码（Windows默认ANSI），彻底解决中文乱码
setlocal enabledelayedexpansion

:: ========== 定义路径（引号包裹，避免空格/特殊字符问题） ==========
set "PROJECT_ROOT=%~dp0"
set "DIST_DIR=%PROJECT_ROOT%dist"
set "FRONTEND_DIR=%PROJECT_ROOT%lingxi-desktop\electron\main\backend"

:: ========== 清理旧构建文件 ==========
echo [1/5] 清理历史构建文件...
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%"
    echo 已删除旧构建目录: %DIST_DIR%
)
if exist "%FRONTEND_DIR%" (
    rmdir /s /q "%FRONTEND_DIR%"
    echo 已删除前端旧后端目录: %FRONTEND_DIR%
)

:: ========== 安装依赖 ==========
echo.
echo [2/5] 安装项目依赖...
pip install -r "%PROJECT_ROOT%requirements.txt"
if errorlevel 1 (
    echo 错误：依赖安装失败！
    pause
    exit /b 1
)

echo.
echo [3/5] 安装PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo 错误：PyInstaller安装失败！
    pause
    exit /b 1
)

:: ========== 打包后端 ==========
echo.
echo [4/5] 使用PyInstaller打包后端...
pyinstaller "%PROJECT_ROOT%backend.spec"
if errorlevel 1 (
    echo 错误：后端打包失败！请检查backend.spec文件是否存在。
    pause
    exit /b 1
)

:: ========== 复制产物到前端 ==========
echo.
echo [5/5] 复制打包产物到前端目录...
mkdir "%FRONTEND_DIR%" >nul 2>&1
xcopy "%DIST_DIR%\lingxi-backend" "%FRONTEND_DIR%" /s /e /y
if errorlevel 1 (
    echo 警告：部分文件复制失败，但核心打包已完成！
) else (
    echo 产物复制成功！
)

:: ========== 完成提示 ==========
echo.
echo ================ 构建完成 ================
echo 后端构建结果已复制到：%FRONTEND_DIR%
pause