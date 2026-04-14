import * as path from 'path'
import * as fs from 'fs'
import { app } from 'electron'

// 日志模块
export class Logger {
  private logDir: string
  private logFile: string
  private errorFile: string
  private originalLog: (...args: any[]) => void
  private originalError: (...args: any[]) => void

  constructor() {
    // 获取运行目录（可执行文件所在目录）
    const basePath = path.dirname(process.execPath)
    this.logDir = path.join(basePath, 'logs')
    this.logFile = path.join(this.logDir, 'electron.log')
    this.errorFile = path.join(this.logDir, 'electron-error.log')

    // 确保日志目录存在
    this.ensureLogDir()

    // 重定向 console.log 和 console.error
    this.redirectConsole()
  }

  private ensureLogDir(): void {
    try {
      if (!fs.existsSync(this.logDir)) {
        fs.mkdirSync(this.logDir, { recursive: true })
      }
    } catch (error) {
      console.error('创建日志目录失败:', error)
    }
  }

  private redirectConsole(): void {
    this.originalLog = console.log
    this.originalError = console.error

    console.log = (...args) => {
      this.originalLog(...args)
      this._writeLog('log', ...args)
    }

    console.error = (...args) => {
      this.originalError(...args)
      this._writeLog('error', ...args)
    }
  }

  private _writeLog(level: 'log' | 'error', ...args): void {
    try {
      const timestamp = new Date().toISOString()
      const message = args.map(arg => {
        if (typeof arg === 'object') {
          try {
            return JSON.stringify(arg)
          } catch {
            return String(arg)
          }
        }
        return String(arg)
      }).join(' ')

      const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}\n`

      // 写入对应的日志文件
      if (level === 'error') {
        fs.appendFileSync(this.errorFile, logMessage)
      } else {
        fs.appendFileSync(this.logFile, logMessage)
      }
    } catch (error) {
      // 避免日志写入失败导致应用崩溃
      console.error('写入日志文件失败:', error)
    }
  }

  // 公共方法
  public info(...args): void {
    this.originalLog(...args)
    this._writeLog('log', ...args)
  }

  public error(...args): void {
    this.originalError(...args)
    this._writeLog('error', ...args)
  }

  public log(...args): void {
    this.originalLog(...args)
    this._writeLog('log', ...args)
  }
}

// 导出单例实例
export const logger = new Logger()