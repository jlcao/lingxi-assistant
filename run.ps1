# 灵犀智能助手启动脚本

# 获取脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "灵犀智能助手启动器"
Write-Host "==================="
Write-Host "脚本目录: $scriptDir"
Write-Host "正在清理占用端口的服务..."

# 清理占用5000端口的服务（后端）
try {
    $processes5000 = netstat -ano | Select-String ":5000"
    foreach ($process in $processes5000) {
        $pid = $process.ToString().Split()[-1]
        Stop-Process -Id $pid -Force
        Write-Host "已杀掉占用5000端口的进程（PID: $pid）"
    }
} catch {
    Write-Host "清理5000端口时出错: $($_.Exception.Message)"
}

# 清理占用5173端口的服务（前端）
try {
    $processes5173 = netstat -ano | Select-String ":5173"
    foreach ($process in $processes5173) {
        $pid = $process.ToString().Split()[-1]
        Stop-Process -Id $pid -Force
        Write-Host "已杀掉占用5173端口的进程（PID: $pid）"
    }
} catch {
    Write-Host "清理5173端口时出错: $($_.Exception.Message)"
}

Write-Host "清理完成，正在启动服务..."

# 启动后端服务
$backendCmd = "cd '$($scriptDir)\lingxi' ; & '$($scriptDir)\lingxi\.venv\Scripts\activate.ps1' ; python -m lingxi --web"
Start-Process cmd.exe -ArgumentList "/c", $backendCmd -WindowStyle Normal -Title "灵犀后端服务"

# 等待2秒
Start-Sleep -Seconds 2

# 启动前端服务
$frontendCmd = "cd '$($scriptDir)\lingxi-desktop' ; npm run dev"
Start-Process cmd.exe -ArgumentList "/c", $frontendCmd -WindowStyle Normal -Title "灵犀前端服务"

Write-Host "服务启动完成！"
Write-Host "后端服务地址：http://localhost:5000"
Write-Host "前端服务地址：http://localhost:5173"
Write-Host ""
Write-Host "服务已在新窗口中启动"
Write-Host "关闭此窗口不会影响服务运行"
Write-Host ""
Write-Host "按任意键关闭..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
