import { ChildProcess, spawn } from 'child_process'
import { app, dialog } from 'electron'
import * as fs from 'fs'
import * as path from 'path'
import * as http from 'http'
import * as net from 'net'
import { logger } from './logger'

export class BackendManager {
  private backendProcess: ChildProcess | null = null
  private backendPort: number = 5000
  private isBackendStarted: boolean = false
  private executableName: string = process.platform === 'win32' ? 'lingxi-backend.exe' : 'lingxi-backend'

  async startBackendService(): Promise<boolean> {
    if (this.isBackendStarted || this.backendProcess) {
      logger.log('[BackendManager] 后端服务已启动，跳过重复启动')
      return Promise.resolve(true)
    }

    return new Promise((resolve) => {
      try {
        let appPath = app.getAppPath()

        if (appPath.endsWith('.asar')) {
          appPath = path.dirname(appPath)
        }

        const possiblePaths = [
          'd:\\resource\\python\\lingxi\\lingxi-desktop\\electron\\main\\backend\\' + this.executableName,
          path.join(appPath, 'electron', 'main', 'backend', this.executableName),
          path.join(appPath, 'backend', this.executableName),
          path.join(path.dirname(appPath), 'backend', this.executableName),
          path.join(path.dirname(appPath), 'resources', 'backend', this.executableName),
          path.join(path.dirname(appPath), this.executableName),
          path.join(path.dirname(appPath), 'resources', this.executableName)
        ]

        let backendPath = ''

        for (const possiblePath of possiblePaths) {
          if (fs.existsSync(possiblePath)) {
            logger.log(`[BackendManager] 找到后端可执行文件: ${possiblePath}`)
            backendPath = possiblePath
            break
          }
        }

        if (!backendPath) {
          this.startWithPythonSource(resolve)
          return
        }
        logger.log(`[BackendManager] 启动后端服务: ${backendPath}`)

        this.startWithExecutable(backendPath, resolve)
      } catch (error) {
        console.error('[BackendManager] 启动后端服务时出错:', error)
        dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${(error as Error).message}`)
        this.isBackendStarted = false
        resolve(false)
      }
    })
  }

  private startWithExecutable(backendPath: string, resolve: (value: boolean) => void): void {
    this.spawnProcess(backendPath, [], (success: boolean, exitCode?: number | null) => {
      if (!success && exitCode === 255) {
        logger.log('[BackendManager] 打包可执行文件启动失败，回退到 Python 源码模式')
        this.startWithPythonSource(resolve)
      } else {
        resolve(success)
      }
    })
  }

  private startWithPythonSource(resolve: (value: boolean) => void): void {
    let appPath = app.getAppPath()
    if (appPath.endsWith('.asar')) {
      appPath = path.dirname(appPath)
    }

    const projectRoot = path.dirname(appPath)
    const startWebServer = path.join(projectRoot, 'start_web_server.py')
    const venvPython = process.platform === 'win32'
      ? path.join(projectRoot, 'lingxi', '.venv', 'Scripts', 'python.exe')
      : path.join(projectRoot, 'lingxi', '.venv', 'bin', 'python3')

    let pythonPath = venvPython
    if (!fs.existsSync(venvPython)) {
      pythonPath = process.platform === 'win32' ? 'python' : 'python3'
      logger.log('[BackendManager] 未找到虚拟环境 Python，使用系统 Python')
    } else {
      logger.log(`[BackendManager] 使用虚拟环境 Python: ${venvPython}`)
    }

    if (!fs.existsSync(startWebServer)) {
      logger.log('[BackendManager] 未找到 start_web_server.py，进入开发模式')
      this.isBackendStarted = true
      resolve(true)
      return
    }

    logger.log(`[BackendManager] 使用 Python 源码模式启动后端: ${pythonPath} ${startWebServer}`)

    this.spawnProcess(pythonPath, [startWebServer], (success: boolean) => {
      resolve(success)
    })
  }

  private spawnProcess(command: string, args: string[], callback: (success: boolean, exitCode?: number | null) => void): void {
    this.backendProcess = spawn(command, args, {
      detached: false,
      stdio: 'pipe',
      killSignal: 'SIGTERM',
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    })

    this.isBackendStarted = true
    const iconv = require('iconv-lite')
    let backendStarted = false
    let portCheckInterval: NodeJS.Timeout | null = null

    // 监听进程输出，仅用于日志记录
    this.backendProcess.stdout?.on('data', (data) => {
      let output: string
      try {
        output = iconv.decode(data, 'gbk')
      } catch (e) {
        output = data.toString()
      }
      logger.log(`[Backend] ${output}`)
    })

    this.backendProcess.stderr?.on('data', (data) => {
      let output: string
      try {
        output = iconv.decode(data, 'gbk')
      } catch (e) {
        output = data.toString()
      }
      console.error(`[Backend] ${output}`)
    })

    this.backendProcess.on('error', (error) => {
      console.error('[BackendManager] 启动后端服务失败:', error)
      dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${(error as Error).message}`)
      this.isBackendStarted = false
      if (portCheckInterval) {
        clearInterval(portCheckInterval)
      }
      callback(false)
    })

    this.backendProcess.on('exit', (code, signal) => {
      logger.log(`[BackendManager] 后端服务退出，代码: ${code}, 信号: ${signal}`)
      this.backendProcess = null
      this.isBackendStarted = false
      if (portCheckInterval) {
        clearInterval(portCheckInterval)
      }
      if (!backendStarted) {
        if (code === 1) {
          logger.log('[BackendManager] 后端服务可能因为端口绑定失败而退出，但已尝试启动')
          callback(true, code)
        } else {
          callback(false, code)
        }
      }
    })

    // 开始检查端口是否可用
    let checkCount = 0
    const maxChecks = 60 // 30秒 / 500ms = 60次
    
    portCheckInterval = setInterval(() => {
      this.checkBackendPort((isAvailable) => {
        if (isAvailable) {
          if (!backendStarted) {
            backendStarted = true
            logger.log('[BackendManager] 后端服务启动完成（端口检查成功）')
            if (portCheckInterval) {
              clearInterval(portCheckInterval)
            }
            callback(true)
          }
        } else {
          checkCount++
          if (checkCount >= maxChecks) {
            if (!backendStarted) {
              console.error('[BackendManager] 后端服务启动超时')
              this.isBackendStarted = false
              if (portCheckInterval) {
                clearInterval(portCheckInterval)
              }
              callback(false)
            }
          }
        }
      })
    }, 500) // 每500毫秒检查一次
  }

  private checkBackendPort(callback: (isAvailable: boolean) => void): void {
    // 首先尝试使用 HTTP 请求检查
    const options = {
      hostname: 'localhost',
      port: this.backendPort,
      path: '/api/status',
      method: 'GET',
      timeout: 1000
    }

    const req = http.request(options, (res) => {
      logger.log(`[BackendManager] 后端服务 HTTP 检查成功，状态码: ${res.statusCode}`)
      callback(true)
    })

    req.on('error', () => {
      // HTTP 请求失败，尝试使用 TCP 连接检查端口是否开放
      this.checkPortWithTcp(this.backendPort, callback)
    })

    req.setTimeout(1000, () => {
      req.destroy()
      this.checkPortWithTcp(this.backendPort, callback)
    })

    req.end()
  }

  private checkPortWithTcp(port: number, callback: (isAvailable: boolean) => void): void {
    const socket = new net.Socket()
    let isConnected = false

    socket.setTimeout(1000)

    socket.on('connect', () => {
      isConnected = true
      logger.log(`[BackendManager] 后端服务端口 ${port} 检查成功（TCP 连接）`)
      socket.end()
      callback(true)
    })

    socket.on('error', () => {
      if (!isConnected) {
        callback(false)
      }
    })

    socket.on('timeout', () => {
      socket.destroy()
      callback(false)
    })

    socket.connect(port, 'localhost')
  }

  stopBackendService(): void {
    const { execSync } = require('child_process')
    try {
      if (!this.backendProcess) {
        logger.log('[BackendManager] 后端进程已不存在，无需停止')
        return
      }

      const pid = this.backendProcess.pid
      logger.log(`[BackendManager] 开始停止后端服务 (PID: ${pid})`)

      let isStopping = true

      try {
        this.backendProcess.kill()
        logger.log(`[BackendManager] 已发送终止信号到进程 ${pid}`)

        const startTime = Date.now()
        while (Date.now() - startTime < 1000) {
          if (pid) {
            try {
              process.kill(pid, 0)
            } catch (e) {
              logger.log(`[BackendManager] 进程 ${pid} 已优雅退出`)
              isStopping = false
              break
            }
          }
        }
      } catch (killError) {
        logger.log(`[BackendManager] 优雅关闭失败: ${(killError as Error).message}`)
      }

      if (isStopping && process.platform === 'win32' && pid) {
        try {
          const cmd = `taskkill /F /PID ${pid} /T`
          logger.log(`[BackendManager] 执行强制终止命令: ${cmd}`)

          const result = execSync(cmd, {
            stdio: ['ignore', 'pipe', 'pipe'],
            encoding: 'binary',
            timeout: 3000
          })

          const iconv = require('iconv-lite')
          const output = iconv.decode(Buffer.from(result, 'binary'), 'gbk')
          logger.log(`[BackendManager] taskkill执行成功: ${output.trim()}`)
          isStopping = false
        } catch (taskkillError: any) {
          logger.error(`[BackendManager] taskkill执行失败: ${taskkillError.message} (状态码: ${taskkillError.status || '未知'})`)
        }
      }

      this.backendProcess = null
      this.isBackendStarted = false

      if (process.platform === 'win32') {
        try {
          const killAllCmd = `taskkill /F /IM ${this.executableName}`
          logger.log(`[BackendManager] 执行强制杀掉所有后端进程命令: ${killAllCmd}`)

          const killAllResult = execSync(killAllCmd, {
            stdio: ['ignore', 'pipe', 'pipe'],
            encoding: 'binary',
            timeout: 3000
          })
          const iconv = require('iconv-lite')
          const killAllOutput = iconv.decode(Buffer.from(killAllResult, 'binary'), 'gbk')
          logger.log(`[BackendManager] 强制杀掉所有后端进程成功: ${killAllOutput.trim()}`)
        } catch (killAllError: any) {
          logger.error(`[BackendManager] 强制杀掉所有后端进程失败: ${killAllError.message} (状态码: ${killAllError.status || '未知'})`)
        }
      } else {
        try {
          const killAllCmd = `pkill -f ${this.executableName}`
          logger.log(`[BackendManager] 执行强制杀掉所有后端进程命令: ${killAllCmd}`)

          const killAllResult = execSync(killAllCmd, {
            stdio: ['ignore', 'pipe', 'pipe'],
            encoding: 'utf8',
            timeout: 3000
          })
          logger.log(`[BackendManager] 强制杀掉所有后端进程成功: ${killAllResult.trim()}`)
        } catch (killAllError: any) {
          logger.error(`[BackendManager] 强制杀掉所有后端进程失败: ${killAllError.message} (状态码: ${killAllError.status || '未知'})`)
        }
      }
      logger.log(`[BackendManager] 后端服务停止流程完成（PID: ${pid}）`)
    } catch (error) {
      logger.error('[BackendManager] 停止后端服务时发生致命错误:', error)
      this.backendProcess = null
      this.isBackendStarted = false
    }
  }

  getBackendPort(): number {
    return this.backendPort
  }

  isBackendRunning(): boolean {
    return this.isBackendStarted && this.backendProcess !== null
  }
}
