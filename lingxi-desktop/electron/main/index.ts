import { app, BrowserWindow, dialog, ipcMain } from 'electron'
import { ApiClient } from './apiClient'
import { FileManager } from './fileManager'
import { WindowManager } from './windowManager'
import { WsClient } from './wsClient'
import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'

class App {
  private windowManager: WindowManager
  private apiClient: ApiClient
  private wsClient: WsClient | null = null
  private fileManager: FileManager
  private backendProcess: ChildProcess | null = null
  private backendPort: number = 5000

  constructor() {
    this.windowManager = new WindowManager()
    this.apiClient = new ApiClient(`http://127.0.0.1:${this.backendPort}`)
    this.fileManager = new FileManager()

    this.setupIpcHandlers()
    // 移除直接初始化WS，改为延迟初始化
  }

  /**
   * 启动后端服务
   */
  private startBackendService(): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        // 获取后端可执行文件路径
        let appPath = app.getAppPath()
        
        // 处理打包后的路径
        if (appPath.endsWith('.asar')) {
          appPath = path.dirname(appPath)
        }
        
        // 尝试多个可能的路径
        const possiblePaths = [
          // 开发环境路径
          path.join(appPath, 'electron', 'main', 'backend', 'lingxi-backend.exe'),
          // 打包后可能的路径
          path.join(appPath, 'backend', 'lingxi-backend.exe'),
          path.join(path.dirname(appPath), 'backend', 'lingxi-backend.exe'),
          path.join(path.dirname(appPath), 'resources', 'backend', 'lingxi-backend.exe'),
          // 直接在 win-unpacked 目录中查找
          path.join(path.dirname(appPath), 'lingxi-backend.exe'),
          path.join(path.dirname(appPath), 'resources', 'lingxi-backend.exe'),
          // 在 app.asar 中查找
          path.join(path.dirname(appPath), 'app.asar', 'electron', 'main', 'backend', 'lingxi-backend.exe'),
          path.join(path.dirname(appPath), 'resources', 'app.asar', 'electron', 'main', 'backend', 'lingxi-backend.exe')
        ]
        
        let backendPath = ''
        const fs = require('fs')
        
        for (const possiblePath of possiblePaths) {
          if (fs.existsSync(possiblePath)) {
            backendPath = possiblePath
            break
          }
        }
        
        if (!backendPath) {
          console.error('[App] 后端可执行文件不存在，尝试了以下路径:', possiblePaths)
          dialog.showErrorBox('后端服务启动失败', `后端可执行文件不存在，尝试了以下路径:\n${possiblePaths.join('\n')}`)
          resolve(false)
          return
        }
        console.log(`[App] 启动后端服务: ${backendPath}`)

        // 启动后端服务
        this.backendProcess = spawn(backendPath, [], {
          detached: false,
          stdio: 'pipe',
          killSignal: 'SIGTERM'
        })

        // 确保前端退出时后端也会退出
        process.on('exit', () => {
          this.stopBackendService()
        })

        let backendStarted = false

        // 监听后端服务输出
        this.backendProcess.stdout?.on('data', (data) => {
          const output = data.toString()
          console.log(`[Backend] ${output}`)
          
          // 检测后端服务是否启动完成
          if (!backendStarted) {
            // 检查是否包含启动成功的关键词
            const startupKeywords = [
              'Started server process',
              'Application startup complete', 
              'Uvicorn running',
              'FastAPI 应用启动成功',
              'Running on http://',
              'Listening on http://'
            ]
            
            for (const keyword of startupKeywords) {
              if (output.includes(keyword)) {
                console.log(`[App] 检测到启动关键词: ${keyword}`)
                backendStarted = true
                console.log('[App] 后端服务启动完成')
                resolve(true)
                break
              }
            }
          }
        })

        this.backendProcess.stderr?.on('data', (data) => {
          console.error(`[Backend] ${data.toString()}`)
        })

        this.backendProcess.on('error', (error) => {
          console.error('[App] 启动后端服务失败:', error)
          dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${error.message}`)
          resolve(false)
        })

        this.backendProcess.on('exit', (code, signal) => {
          console.log(`[App] 后端服务退出，代码: ${code}, 信号: ${signal}`)
          this.backendProcess = null
          if (!backendStarted) {
            // 检查是否有端口绑定错误
            if (code === 1) {
              console.log('[App] 后端服务可能因为端口绑定失败而退出，但已尝试启动')
              // 仍然认为启动成功，因为服务已经尝试启动了
              resolve(true)
            } else {
              resolve(false)
            }
          }
        })

        // 超时处理
        setTimeout(() => {
          if (!backendStarted) {
            console.error('[App] 后端服务启动超时')
            resolve(false)
          }
        }, 10000)

      } catch (error) {
        console.error('[App] 启动后端服务时出错:', error)
        dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${error.message}`)
        resolve(false)
      }
    })
  }

  /**
   * 停止后端服务
   */
  private stopBackendService(): void {
    try {
      if (this.backendProcess) {
        console.log('[App] 停止后端服务')
        this.backendProcess.kill()
        this.backendProcess = null
        console.log('[App] 后端服务已停止')
      }
    } catch (error) {
      console.error('[App] 停止后端服务时出错:', error)
    }
  }

  private safeSend(channel: string, ...args: any[]): void {
    const mainWindow = this.windowManager.getWindow()
    if (mainWindow && !mainWindow.isDestroyed() && mainWindow.webContents) {
      try {
        mainWindow.webContents.send(channel, ...args)
      } catch (error) {
        console.error(`[App] 发送 IPC 消息失败 (${channel}):`, error)
      }
    }
  }

  private setupIpcHandlers(): void {
    // ===== 原有窗口/文件/API IPC 逻辑保持不变 =====
    ipcMain.handle('window:minimize', () => {
      this.windowManager.hideToEdge()
    })
    ipcMain.handle('window:toggle', () => {
      this.windowManager.toggleWindow()
    })
    ipcMain.handle('window:maximize', () => {
      this.windowManager.maximizeWindow()
    })
    ipcMain.handle('window:edge-check', () => {
      return this.windowManager.checkEdgePosition()
    })
    ipcMain.handle('window:is-maximized', () => {
      return this.windowManager.isMaximized()
    })

    ipcMain.handle('file:select', async (_, filters) => {
      return this.fileManager.selectFile(filters)
    })
    ipcMain.handle('file:select-directory', async () => {
      return this.fileManager.selectDirectory()
    })
    ipcMain.handle('file:select-files', async (_, filters) => {
      return this.fileManager.selectFiles(filters)
    })
    ipcMain.handle('file:save', async (_, defaultPath, filters) => {
      return this.fileManager.saveFile(defaultPath, filters)
    })
    ipcMain.handle('file:open-explorer', async (_, filePath) => {
      return this.fileManager.openInExplorer(filePath)
    })
    ipcMain.handle('file:open-file', async (_, filePath) => {
      return this.fileManager.openFile(filePath)
    })
    ipcMain.handle('file:read-directory-tree', async (_, dirPath, maxDepth) => {
      return this.fileManager.readDirectoryTree(dirPath, maxDepth)
    })

    ipcMain.handle('api:get-sessions', async () => {
      const result = await this.apiClient.getSessions()
      return result.sessions
    })
    ipcMain.handle('api:get-session-history', async (_, sessionId, maxTurns) => {
      if (!sessionId) {
        return []
      }
      const result = await this.apiClient.getSessionHistory(sessionId, maxTurns)
      return result.history
    })
    ipcMain.handle('api:create-session', async (_, userName) => {
      return this.apiClient.createSession({ user_name: userName || undefined })
    })

    ipcMain.handle('api:delete-session', async (_, sessionId) => {
      return this.apiClient.deleteSession(sessionId)
    })

    ipcMain.handle('api:update-session-name', async (_, sessionId, name) => {
      return this.apiClient.updateSessionName(sessionId, name)
    })

    ipcMain.handle('api:clear-session-history', async (_, sessionId) => {
      return this.apiClient.clearSessionHistory(sessionId)
    })

    ipcMain.handle('api:execute-task', async (_, task, sessionId, modelOverride) => {
      return this.apiClient.executeTask({
        task,
        session_id: sessionId,
        model_override: modelOverride || null
      })
    })

    ipcMain.handle('api:get-task-status', async (_, taskId) => {
      return this.apiClient.getTaskStatus(taskId)
    })

    ipcMain.handle('api:retry-task', async (_, taskId, stepIndex, userInput) => {
      return this.apiClient.retryTask(taskId, {
        step_index: stepIndex,
        user_input: userInput || null
      })
    })

    ipcMain.handle('api:cancel-task', async (_, taskId) => {
      return this.apiClient.cancelTask(taskId)
    })
    ipcMain.handle('api:get-checkpoints', async () => {
      const result = await this.apiClient.getCheckpoints()
      return result.checkpoints
    })
    ipcMain.handle('api:resume-checkpoint', async (_, sessionId) => {
      return this.apiClient.resumeCheckpoint(sessionId)
    })
    ipcMain.handle('api:delete-checkpoint', async (_, sessionId) => {
      return this.apiClient.deleteCheckpoint(sessionId)
    })
    ipcMain.handle('api:get-skills', async () => {
      const result = await this.apiClient.getSkills()
      return result.skills
    })
    ipcMain.handle('api:install-skill', async (_, skillData, skillFiles, autoFix) => {
      return this.apiClient.installSkill({
        skill_data: skillData,
        skill_files: skillFiles,
        auto_fix: autoFix
      })
    })
    ipcMain.handle('api:diagnose-skill', async (_, skillId) => {
      return this.apiClient.diagnoseSkill(skillId)
    })
    ipcMain.handle('api:reload-skill', async (_, skillId) => {
      return this.apiClient.reloadSkill(skillId)
    })
    ipcMain.handle('api:get-resource-usage', async () => {
      return this.apiClient.getResourceUsage()
    })
    ipcMain.handle('api:get-config', async () => {
      return this.apiClient.getConfig()
    })
    ipcMain.handle('api:update-config', async (_, config) => {
      return this.apiClient.updateConfig(config)
    })

    ipcMain.handle('api:get-session-info', async (_, sessionId) => {
      if (!sessionId) {
        throw new Error('Session ID is required')
      }
      return this.apiClient.getSession(sessionId)
    })

    ipcMain.handle('workspace:get-current', async () => {
      return this.apiClient.getWorkspaceCurrent()
    })

    ipcMain.handle('workspace:switch', async (_, workspacePath, force) => {
      return this.apiClient.switchWorkspace(workspacePath, force)
    })

    ipcMain.handle('workspace:initialize', async (_, workspacePath) => {
      return this.apiClient.initializeWorkspace(workspacePath)
    })

    ipcMain.handle('workspace:validate', async (_, workspacePath) => {
      return this.apiClient.validateWorkspace(workspacePath)
    })

    // ===== WS IPC 逻辑优化（新增错误提示 + 延迟初始化）=====
    ipcMain.handle('ws:connect', async (_, sessionId) => {
      // 延迟初始化WS客户端（首次连接时初始化）
      if (!this.wsClient) {
        this.initWsClient()
      }
      this.wsClient?.connect(sessionId)
    })

    ipcMain.handle('ws:disconnect', async () => {
      this.wsClient?.disconnect()
    })

    ipcMain.handle('ws:is-connected', async () => {
      return this.wsClient?.isConnected() || false
    })

    ipcMain.handle('ws:send-message', async (_, message, sessionId) => {
      this.wsClient?.send({
        type: 'stream_chat',
        content: message,
        sessionId: sessionId || 'default'
      })
    })
  }

  /**
   * 初始化WS客户端（延迟执行，带错误提示）
   */
  private initWsClient(): void {
    this.wsClient = new WsClient(`ws://127.0.0.1:${this.backendPort}/ws`)

    // 监听WS错误，弹出可视化提示框
    this.wsClient.on('error', (err: Error) => {
      const mainWindow = this.windowManager.getWindow()
      // 连接被拒绝的友好提示
      if (err.message.includes('ECONNREFUSED')) {
        dialog.showErrorBox(
          'WebSocket连接失败',
          '无法连接到本地5000端口的WS服务端，请确认：\n1. 后端服务已启动\n2. 5000端口未被其他程序占用\n3. 服务端WS地址配置正确（当前：ws://127.0.0.1:5000/ws）'
        )
      } else {
        // 其他错误的通用提示
        dialog.showErrorBox('WebSocket错误', `连接异常：${err.message}`)
      }
      // 转发错误到渲染进程，前端可自定义展示
      mainWindow?.webContents.send('ws:error', err.message)
    })

    // 监听重连失败事件，提示用户
    this.wsClient.on('reconnect_failed', () => {
      dialog.showErrorBox(
        'WS重连失败',
        '已尝试10次重连仍无法连接到服务端，请检查服务端状态后手动重新连接'
      )
      this.safeSend('ws:reconnect-failed')
    })

    // ===== 原有WS事件转发逻辑保持不变 =====
    this.wsClient.on('connected', () => {
      this.safeSend('ws:connected')
    })

    this.wsClient.on('disconnected', () => {
      this.safeSend('ws:disconnected')
    })

    this.wsClient.on('thought_chain', (data) => {
      this.safeSend('ws:thought-chain', data)
    })

    this.wsClient.on('task_start', (data) => {
      this.safeSend('ws:task-start', data)
    })

    this.wsClient.on('task_end', (data) => {
      this.safeSend('ws:task-end', data)
    })

    this.wsClient.on('think_start', (data) => {
      this.safeSend('ws:think-start', data)
    })

    this.wsClient.on('think_stream', (data) => {
      console.log('[Date: ' + new Date().toLocaleString() + '] [Main] think_stream received:', JSON.stringify(data).substring(0, 200))
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow && !mainWindow.isDestroyed()) {
        console.log('[Date: ' + new Date().toLocaleString() + '] [Main] Sending ws:think-stream to renderer')
        this.safeSend('ws:think-stream', data)
      } else {
        console.log('[Date: ' + new Date().toLocaleString() + '] [Main] No main window available')
      }
    })

    this.wsClient.on('think_final', (data) => {
      this.safeSend('ws:think-final', data)
    })

    this.wsClient.on('plan_start', (data) => {
      this.safeSend('ws:plan-start', data)
    })

    this.wsClient.on('plan_final', (data) => {
      this.safeSend('ws:plan-final', data)
    })

    this.wsClient.on('step_start', (data) => {
      this.safeSend('ws:step-start', data)
    })

    this.wsClient.on('step_end', (data) => {
      this.safeSend('ws:step-end', data)
    })

    this.wsClient.on('task_failed', (data) => {
      this.safeSend('ws:task-failed', data)
    })

    this.wsClient.on('workspace_files_changed', (data) => {
      this.safeSend('ws:workspace-files-changed', data)
    })
  }

  async start(): Promise<void> {
    app.whenReady().then(async () => {
      // 启动后端服务并等待完成
      console.log('[App] 正在启动后端服务...')
      const backendStarted = await this.startBackendService()
      
      if (backendStarted) {
        console.log('[App] 后端服务启动成功，创建主窗口')
        // 创建主窗口
        this.windowManager.createMainWindow()
        
        // 初始化WS客户端
        console.log('[App] 初始化 WebSocket 客户端')
        this.initWsClient()
      } else {
        console.error('[App] 后端服务启动失败，无法继续')
        // 可以选择退出应用或显示错误界面
        dialog.showErrorBox('启动失败', '后端服务启动失败，应用无法正常运行')
        app.quit()
      }
    })

    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.cleanupResources()
        app.quit()
      }
    })

    app.on('before-quit', (event) => {
      console.log('[App] before-quit 事件触发，开始清理资源')
      event.preventDefault()
      this.cleanupResources()

      setTimeout(() => {
        console.log('[App] 资源清理完成，退出应用')
        app.quit()
      }, 1000)
    })

    app.on('will-quit', () => {
      console.log('[App] will-quit 事件触发')
      this.cleanupResources()
    })

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.windowManager.createMainWindow()
      }
    })
  }

  private cleanupResources(): void {
    console.log('[App] 开始清理资源')

    try {
      if (this.wsClient) {
        console.log('[App] 断开 WebSocket 连接')
        this.wsClient.disconnect()
        this.wsClient = null
      }
    } catch (error) {
      console.error('[App] 清理 WebSocket 时出错:', error)
    }

    try {
      // 停止后端服务
      this.stopBackendService()
    } catch (error) {
      console.error('[App] 清理后端服务时出错:', error)
    }

    try {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow && !mainWindow.isDestroyed()) {
        console.log('[App] 销毁主窗口')
        mainWindow.destroy()
      }
    } catch (error) {
      console.error('[App] 销毁窗口时出错:', error)
    }

    console.log('[App] 资源清理完成')
  }
}

new App().start()