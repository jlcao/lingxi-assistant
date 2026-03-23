@echo off

chcp 65001 >nul

echo 测试批处理脚本

echo 当前目录: %cd%
echo 1. 测试 Python 命令:
python --version
echo 2. 测试 npm 命令:
npm --version
echo 3. 测试目录切换:
cd lingxi
echo 切换到 lingxi 目录: %cd%
cd ..
echo 切换回根目录: %cd%

echo 测试完成，按任意键退出...
pause