# 灵犀智能助手启动脚本

Write-Host "清理占用端口的服务..."

# 清理占用5000端口的服务
netstat -ano | findstr :5000 > ports5000.txt
if (Test-Path ports5000.txt) {
    $content = Get-Content ports5000.txt
    if ($content) {
        foreach ($line in $content) {
            $parts = $line -split "\s+"
            if ($parts.Length -gt 4) {
                $processId = $parts[4]
                try {
                    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                    Write-Host "已清理占用5000端口的进程（PID: $processId）"
                } catch {
                    # 忽略错误
                }
            }
        }
    }
    Remove-Item ports5000.txt
}

# 清理占用5173端口的服务
netstat -ano | findstr :5173 > ports5173.txt
if (Test-Path ports5173.txt) {
    $content = Get-Content ports5173.txt
    if ($content) {
        foreach ($line in $content) {
            $parts = $line -split "\s+"
            if ($parts.Length -gt 4) {
                $processId = $parts[4]
                try {
                    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                    Write-Host "已清理占用5173端口的进程（PID: $processId）"
                } catch {
                    # 忽略错误
                }
            }
        }
    }
    Remove-Item ports5173.txt
}

Write-Host "正在启动后端服务..."
# 启动后端服务
Start-Process cmd.exe -ArgumentList "/k", "python -m lingxi --web"

# 等待2秒
Start-Sleep -Seconds 2

Write-Host "正在启动前端服务..."
# 启动前端服务
Start-Process cmd.exe -ArgumentList "/k", "cd lingxi-desktop && npm run dev"

Write-Host "服务启动完成！"
Write-Host "后端服务地址：http://localhost:5000"
Write-Host "前端服务地址：http://localhost:5173"
Write-Host ""
Write-Host "服务已在新窗口中启动"
Write-Host "关闭此窗口不会影响服务运行"
Write-Host ""
Write-Host "按任意键关闭..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
