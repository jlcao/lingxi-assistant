Write-Host "清理占用端口的服务..."

# 清理占用5000端口的服务
try {
    $output = netstat -ano | findstr :5000
    if ($output) {
        $pid = $output.Split()[-1]
        Stop-Process -Id $pid -Force
        Write-Host "已杀掉占用5000端口的进程（PID: $pid）"
    }
} catch {
    Write-Host "清理5000端口时出错"
}

# 清理占用5173端口的服务
try {
    $output = netstat -ano | findstr :5173
    if ($output) {
        $pid = $output.Split()[-1]
        Stop-Process -Id $pid -Force
        Write-Host "已杀掉占用5173端口的进程（PID: $pid）"
    }
} catch {
    Write-Host "清理5173端口时出错"
}

Write-Host "端口清理完成！"
