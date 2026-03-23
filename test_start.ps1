# 简化测试脚本

# 显示基本信息
Write-Host "测试脚本开始运行..."
Write-Host "当前目录: $PWD"
Write-Host "脚本路径: $PSCommandPath"

# 测试基本命令
Write-Host "\n测试 Python 命令:"
python --version

Write-Host "\n测试 npm 命令:"
npm --version

Write-Host "\n测试目录结构:"
get-childitem .

Write-Host "\n测试完成，按 Enter 键退出..."
Read-Host