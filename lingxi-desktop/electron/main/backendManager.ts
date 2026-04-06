import { ChildProcess, spawn } from 'child_process'
import { app, dialog } from 'electron'
import * as fs from 'fs'
import * as path from 'path'
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
          logger.log('[BackendManager] 后端可执行文件不存在，进入开发模式，直接连接后端端口')
          this.isBackendStarted = true
          resolve(true)
          return
        }
        logger.log(`[BackendManager] 启动后端服务: ${backendPath}`)

        this.backendProcess = spawn(backendPath, [], {
          detached: false,
          stdio: 'pipe',
          killSignal: 'SIGTERM',
          env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        })

        this.isBackendStarted = true
        const iconv = require('iconv-lite')
        let backendStarted = false

        this.backendProcess.stdout?.on('data', (data) => {
          let output: string
          try {
            output = iconv.decode(data, 'gbk')
          } catch (e) {
            output = data.toString()
          }
          logger.log(`[Backend] ${output}`)

          if (!backendStarted) {
            const startupKeywords = [
              'Started server process',
              'Application startup complete',
              'Uvicorn running',
              'FastAPI 应用启动成功',
              '服务器配置',
              'Running on http://',
              'Listening on http://',
              'http://localhost:5000'
            ]
            for (const keyword of startupKeywords) {
              if (output.includes(keyword)) {
                logger.log(`[BackendManager] 检测到启动关键词: ${keyword}`)
                backendStarted = true
                logger.log('[BackendManager] 后端服务启动完成')
                resolve(true)
                break
              }
            }
          }
        })

        this.backendProcess.stderr?.on('data', (data) => {
          let output: string
          try {
            output = iconv.decode(data, 'gbk')
          } catch (e) {
            output = data.toString()
          }
          console.error(`[Backend] ${output}`)

          if (!backendStarted) {
            const startupKeywords = [
              'Started server process',
              'Application startup complete',
              'Uvicorn running',
              'FastAPI 应用启动成功',
              '服务器配置',
              'Running on http://',
              'Listening on http://',
              'http://localhost:5000'
            ]

            for (const keyword of startupKeywords) {
              if (output.includes(keyword)) {
                logger.log(`[BackendManager] 检测到启动关键词: ${keyword}`)
                backendStarted = true
                logger.log('[BackendManager] 后端服务启动完成')
                resolve(true)
                break
              }
            }
          }
        })

        this.backendProcess.on('error', (error) => {
          console.error('[BackendManager] 启动后端服务失败:', error)
          dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${(error as Error).message}`)
          this.isBackendStarted = false
          resolve(false)
        })

        this.backendProcess.on('exit', (code, signal) => {
          logger.log(`[BackendManager] 后端服务退出，代码: ${code}, 信号: ${signal}`)
          this.backendProcess = null
          this.isBackendStarted = false
          if (!backendStarted) {
            if (code === 1) {
              logger.log('[BackendManager] 后端服务可能因为端口绑定失败而退出，但已尝试启动')
              resolve(true)
            } else {
              resolve(false)
            }
          }
        })

        setTimeout(() => {
          if (!backendStarted) {
            console.error('[BackendManager] 后端服务启动超时')
            this.isBackendStarted = false
            resolve(false)
          }
        }, 30000)

      } catch (error) {
        console.error('[BackendManager] 启动后端服务时出错:', error)
        dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${(error as Error).message}`)
        this.isBackendStarted = false
        resolve(false)
      }
    })
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
