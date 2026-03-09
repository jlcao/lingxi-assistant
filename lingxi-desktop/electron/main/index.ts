import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import { WindowManager } from './windowManager'
import { ApiClient } from './apiClient'
import { WsClient } from './wsClient'
import { FileManager } from './fileManager'

class App {
  private windowManager: WindowManager
  private apiClient: ApiClient
  private wsClient: WsClient | null = null
  private fileManager: FileManager

  constructor() {
    this.windowManager = new WindowManager()
    this.apiClient = new ApiClient('http://127.0.0.1:5000')
    this.fileManager = new FileManager()

    this.setupIpcHandlers()
    // 移除直接初始化WS，改为延迟初始化
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
    this.wsClient = new WsClient('ws://127.0.0.1:5000/ws')

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
      const mainWindow = this.windowManager.getWindow()
      mainWindow?.webContents.send('ws:reconnect-failed')
    })

    // ===== 原有WS事件转发逻辑保持不变 =====
    this.wsClient.on('connected', () => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:connected')
      }
    })

    this.wsClient.on('disconnected', () => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:disconnected')
      }
    })

    this.wsClient.on('thought_chain', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:thought-chain', data)
      }
    })

    this.wsClient.on('task_start', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:task-start', data)
      }
    })

    this.wsClient.on('task_end', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:task-end', data)
      }
    })

    this.wsClient.on('think_start', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:think-start', data)
      }
    })

    this.wsClient.on('think_stream', (data) => {
      console.log('[Date: ' + new Date().toLocaleString() + '] [Main] think_stream received:', JSON.stringify(data).substring(0, 200))
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        console.log('[Date: ' + new Date().toLocaleString() + '] [Main] Sending ws:think-stream to renderer')
        mainWindow.webContents.send('ws:think-stream', data)
      } else {
        console.log('[Date: ' + new Date().toLocaleString() + '] [Main] No main window available')
      }
    })

    this.wsClient.on('think_final', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:think-final', data)
      }
    })

    this.wsClient.on('plan_start', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:plan-start', data)
      }
    })

    this.wsClient.on('plan_final', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:plan-final', data)
      }
    })

    this.wsClient.on('step_start', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:step-start', data)
      }
    })

    this.wsClient.on('step_end', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:step-end', data)
      }
    })

    this.wsClient.on('task_failed', (data) => {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow) {
        mainWindow.webContents.send('ws:task-failed', data)
      }
    })
  }

  start(): void {
    app.whenReady().then(() => {
      this.windowManager.createMainWindow()
      // 可选：如果需要启动时自动连接WS，可延迟1秒初始化
      // setTimeout(() => {
      //   this.initWsClient()
      //   this.wsClient?.connect()
      // }, 1000)
    })

    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.wsClient?.disconnect()
        app.quit()
      }
    })

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.windowManager.createMainWindow()
      }
    })
  }
}

new App().start()