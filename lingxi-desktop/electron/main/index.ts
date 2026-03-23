import { ChildProcess, spawn } from 'child_process'
import { app, BrowserWindow, dialog, ipcMain } from 'electron'
import * as fs from 'fs'
import * as path from 'path'
import { ApiClient } from './apiClient'
import { FileManager } from './fileManager'
import { WindowManager } from './windowManager'
import { WsClient } from './wsClient'

// 导入日志模块
import { logger } from './logger'

class App {
  private windowManager: WindowManager
  private apiClient: ApiClient
  private wsClient: WsClient | null = null
  private fileManager: FileManager
  private backendProcess: ChildProcess | null = null
  private backendPort: number = 5000
  private isQuitting: boolean = false
  // 新增：标记后端是否已启动，防止重复启动
  private isBackendStarted: boolean = false
  // 新增：标记WS是否已初始化，防止重复初始化
  private isWsInitialized: boolean = false
  // 文件监控相关
  private workspaceWatcher: fs.FSWatcher | null = null
  private workspacePath: string | null = null
  private fileChangeTimeout: NodeJS.Timeout | null = null
  private pendingChanges: Map<string, 'added' | 'modified' | 'deleted'> = new Map()

  // 忽略的文件和目录
  private readonly IGNORE_PATTERNS = [
    'node_modules',
    '.git',
    '.svn',
    '__pycache__',
    '.DS_Store',
    'dist',
    'build',
    '.cache',
    '.log'
  ]

  constructor() {
    this.windowManager = new WindowManager()
    this.apiClient = new ApiClient(`http://127.0.0.1:${this.backendPort}`)
    this.fileManager = new FileManager()

    this.setupIpcHandlers()
    // 移除直接初始化WS，改为延迟初始化

    // 确保前端退出时后端也会退出（只添加一次）
    process.on('exit', () => {
      this.stopBackendService()
    })
  }

  /**
   * 启动后端服务（增加防重复启动逻辑）
   */
  private startBackendService(): Promise<boolean> {
    // 防止重复启动

    if (this.isBackendStarted || this.backendProcess) {
      logger.log('[App] 后端服务已启动，跳过重复启动')
      return Promise.resolve(true)
    }

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
          // 用户指定的路径
          'd:\\resource\\python\\lingxi\\lingxi-desktop\\electron\\main\\backend\\lingxi-backend.exe',
          // 开发环境路径
          path.join(appPath, 'electron', 'main', 'backend', 'lingxi-backend.exe'),
          // 打包后可能的路径
          path.join(appPath, 'backend', 'lingxi-backend.exe'),
          path.join(path.dirname(appPath), 'backend', 'lingxi-backend.exe'),
          path.join(path.dirname(appPath), 'resources', 'backend', 'lingxi-backend.exe'),
          // 直接在 win-unpacked 目录中查找
          path.join(path.dirname(appPath), 'lingxi-backend.exe'),
          path.join(path.dirname(appPath), 'resources', 'lingxi-backend.exe')
        ]

        let backendPath = ''

        for (const possiblePath of possiblePaths) {
          if (fs.existsSync(possiblePath)) {
            logger.log(`[App] 找到后端可执行文件: ${possiblePath}`)
            backendPath = possiblePath
            break
          }
        }

        if (!backendPath) {
          // 后端可执行文件不存在，认为是开发模式，直接返回成功
          logger.log('[App] 后端可执行文件不存在，进入开发模式，直接连接后端端口')
          this.isBackendStarted = true // 标记后端已启动
          resolve(true)
          return
        }
        logger.log(`[App] 启动后端服务: ${backendPath}`)

        // 启动后端服务
        this.backendProcess = spawn(backendPath, [], {
          detached: false,
          stdio: 'pipe',
          killSignal: 'SIGTERM',
          env: { ...process.env, PYTHONIOENCODING: 'utf-8' }  // 新增这行
        })

        // 标记后端启动中
        this.isBackendStarted = true
        const iconv = require('iconv-lite')
        let backendStarted = false

        // 监听后端服务输出
        this.backendProcess.stdout?.on('data', (data) => {
          let output: string
          try {
            output = iconv.decode(data, 'gbk')  // 使用 GBK 解码
          } catch (e) {
            output = data.toString()
          }
          logger.log(`[Backend] ${output}`)

          // 检测后端服务是否启动完成
          if (!backendStarted) {
            // 检查是否包含启动成功的关键词
            const startupKeywords = [
              'Started server process',
              'Application startup complete',
              'Uvicorn running',
              'FastAPI 应用启动成功',
              '服务器配置',  // 新增
              'Running on http://',
              'Listening on http://',
              'http://localhost:5000'  // 新增
            ]
            for (const keyword of startupKeywords) {
              if (output.includes(keyword)) {
                logger.log(`[App] 检测到启动关键词: ${keyword}`)
                backendStarted = true
                logger.log('[App] 后端服务启动完成')
                resolve(true)
                break
              }
            }
          }
        })

        this.backendProcess.stderr?.on('data', (data) => {
          let output: string
          try {
            output = iconv.decode(data, 'gbk')  // 使用 GBK 解码
          } catch (e) {
            output = data.toString()
          }
          console.error(`[Backend] ${output}`)

          // 同样检测后端服务是否启动完成（因为输出可能在stderr）
          if (!backendStarted) {
            // 检查是否包含启动成功的关键词
            const startupKeywords = [
              'Started server process',
              'Application startup complete',
              'Uvicorn running',
              'FastAPI 应用启动成功',
              '服务器配置',  // 新增
              'Running on http://',
              'Listening on http://',
              'http://localhost:5000'  // 新增
            ]

            for (const keyword of startupKeywords) {
              if (output.includes(keyword)) {
                logger.log(`[App] 检测到启动关键词: ${keyword}`)
                backendStarted = true
                logger.log('[App] 后端服务启动完成')
                resolve(true)
                break
              }
            }
          }
        })

        this.backendProcess.on('error', (error) => {
          console.error('[App] 启动后端服务失败:', error)
          dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${error.message}`)
          this.isBackendStarted = false // 重置状态
          resolve(false)
        })

        this.backendProcess.on('exit', (code, signal) => {
          logger.log(`[App] 后端服务退出，代码: ${code}, 信号: ${signal}`)
          this.backendProcess = null
          this.isBackendStarted = false // 重置状态
          if (!backendStarted) {
            // 检查是否有端口绑定错误
            if (code === 1) {
              logger.log('[App] 后端服务可能因为端口绑定失败而退出，但已尝试启动')
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
            this.isBackendStarted = false // 重置状态
            resolve(false)
          }
        }, 30000)

      } catch (error) {
        console.error('[App] 启动后端服务时出错:', error)
        dialog.showErrorBox('后端服务启动失败', `无法启动后端服务: ${error.message}`)
        this.isBackendStarted = false // 重置状态
        resolve(false)
      }
    })
  }

  /**
  * 停止后端服务（终极修复版）
  */
  private stopBackendService(): void {
    // 提前引入依赖，避免运行时加载失败
    const { execSync } = require('child_process');
    const path = require('path');
    try {
      if (!this.backendProcess) {
        logger.log('[App] 后端进程已不存在，无需停止');
        return;
      }

      const pid = this.backendProcess.pid;
      logger.log(`[App] 开始停止后端服务 (PID: ${pid})`);

      // 标记进程正在停止，防止重复操作
      let isStopping = true;

      // ========== 步骤1：尝试优雅关闭 ==========
      try {
        // 先发送关闭信号
        this.backendProcess.kill(); // 默认SIGTERM，兼容Windows
        logger.log(`[App] 已发送终止信号到进程 ${pid}`);

        // 等待1秒，给进程优雅退出的时间
        const startTime = Date.now();
        while (Date.now() - startTime < 1000) {
          // 检查进程是否还在
          try {
            process.kill(pid, 0); // 0信号仅检查进程是否存在，不发送终止信号
          } catch (e) {
            logger.log(`[App] 进程 ${pid} 已优雅退出`);
            isStopping = false;
            break;
          }
        }
      } catch (killError) {
        logger.warn(`[App] 优雅关闭失败: ${killError.message}`);
      }

      // ========== 步骤2：Windows强制终止（仅进程仍在运行时） ==========
      if (isStopping && process.platform === 'win32' && pid) {
        try {
          // 执行taskkill命令（强制终止进程树）
          const cmd = `taskkill /F /PID ${pid} /T`;
          logger.log(`[App] 执行强制终止命令: ${cmd}`);

          // 关键：使用GBK编码，超时3秒，静默执行
          const result = execSync(cmd, {
            stdio: ['ignore', 'pipe', 'pipe'],
            encoding: 'binary', // 先以二进制读取
            timeout: 3000
          });

          // 解码输出（GBK转UTF-8）
          const iconv = require('iconv-lite');
          const output = iconv.decode(Buffer.from(result, 'binary'), 'gbk');
          logger.log(`[App] taskkill执行成功: ${output.trim()}`);
          isStopping = false;
        } catch (taskkillError: any) {
          logger.error(`[App] taskkill执行失败: ${taskkillError.message} (状态码: ${taskkillError.status || '未知'})`);
        }
      }

      // ========== 步骤3：最终状态清理 ==========
      this.backendProcess = null;
      this.isBackendStarted = false;


      // ========== 步骤4：强制杀掉所有后端进程（防止残留） ==========
      try {
        // 执行taskkill命令，强制杀掉所有 lingxi-backend.exe 进程
        const killAllCmd = `taskkill /F /IM lingxi-backend.exe`;
        logger.log(`[App] 执行强制杀掉所有后端进程命令: ${killAllCmd}`);

        // 关键：使用GBK编码，超时3秒，静默执行
        const killAllResult = execSync(killAllCmd, {
          stdio: ['ignore', 'pipe', 'pipe'],
          encoding: 'binary', // 先以二进制读取
          timeout: 3000
        });
        // 解码输出（GBK转UTF-8）
        const iconv = require('iconv-lite');
        const killAllOutput = iconv.decode(Buffer.from(killAllResult, 'binary'), 'gbk');
        logger.log(`[App] 强制杀掉所有后端进程成功: ${killAllOutput.trim()}`);
      } catch (killAllError: any) {
        logger.error(`[App] 强制杀掉所有后端进程失败: ${killAllError.message} (状态码: ${killAllError.status || '未知'})`);
      }
      logger.log(`[App] 后端服务停止流程完成（PID: ${pid}）`);
    } catch (error) {
      // 捕获所有未预期错误
      logger.error('[App] 停止后端服务时发生致命错误:', error);
      // 兜底重置状态
      this.backendProcess = null;
      this.isBackendStarted = false;
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
      logger.log(`[IPC] file:open-explorer: ${filePath}`)
      return this.fileManager.openInExplorer(filePath)
    })
    ipcMain.handle('file:open-file', async (_, filePath) => {
      logger.log(`[IPC] file:open-file: ${filePath}`)
      try {
        const result = await this.fileManager.openFile(filePath)
        logger.log(`[IPC] file:open-file result: ${result}`)
        return result
      } catch (error) {
        logger.error(`[IPC] file:open-file error:`, error)
        throw error
      }
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

    ipcMain.handle('api:get-session-info', async (_, sessionId) => {
      if (!sessionId) {
        throw new Error('Session ID is required')
      }
      return this.apiClient.getSession(sessionId)
    })

    ipcMain.handle('api:get-workspace-sessions', async (_, workspacePath) => {
      return this.apiClient.getWorkspaceSessions(workspacePath)
    })

    ipcMain.handle('workspace:get-current', async () => {
      const workspacePath = this.workspacePath || await this.apiClient.getWorkspaceCurrent()
      // 返回对象格式，而不是字符串
      if (workspacePath) {
        return {
          workspace: workspacePath,
          lingxi_dir: require('path').join(workspacePath, '.lingxi'),
          is_initialized: true
        }
      }
      return null
    })

    ipcMain.handle('workspace:switch', async (_, workspacePath, force) => {
      logger.log(`[App] workspace:switch called with: ${workspacePath}`)

      const result = await this.apiClient.switchWorkspace(workspacePath, force)

      // 设置文件监控
      this.setupFileWatcher(workspacePath)

      return result
    })

    ipcMain.handle('workspace:initialize', async (_, workspacePath) => {
      logger.log(`[App] workspace:initialize called with: ${workspacePath}`)

      const result = await this.apiClient.initializeWorkspace(workspacePath)

      // 设置文件监控
      this.setupFileWatcher(workspacePath)

      return result
    })

    ipcMain.handle('workspace:validate', async (_, workspacePath) => {
      return this.apiClient.validateWorkspace(workspacePath)
    })

    // ===== WS IPC 逻辑优化（新增错误提示 + 延迟初始化）=====
    ipcMain.handle('ws:connect', async (_, sessionId) => {
      // 延迟初始化WS客户端（首次连接时初始化）
      if (!this.wsClient && !this.isWsInitialized) {
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
   * 初始化WS客户端（增加防重复初始化逻辑）
   */
  private initWsClient(): void {
    // 防止重复初始化
    if (this.isWsInitialized || this.wsClient) {
      logger.log('[App] WS客户端已初始化，跳过重复初始化')
      return
    }

    // 标记WS初始化中
    this.isWsInitialized = true
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
      //logger.log('[Date: ' + new Date().toLocaleString() + '] [Main] think_stream received:', JSON.stringify(data).substring(0, 200))
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow && !mainWindow.isDestroyed()) {
        //logger.log('[Date: ' + new Date().toLocaleString() + '] [Main] Sending ws:think-stream to renderer')
        this.safeSend('ws:think-stream', data)
      } else {
        logger.log('[Date: ' + new Date().toLocaleString() + '] [Main] No main window available')
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
    // 修复：将所有逻辑包裹在 once 中，防止 ready 事件重复触发
    app.once('ready', async () => {
      // 启动后端服务并等待完成
      logger.log('[App] 正在启动后端服务...')
      const backendStarted = await this.startBackendService()

      if (backendStarted) {
        logger.log('[App] 后端服务启动成功，创建主窗口')
        // 创建主窗口
        this.windowManager.createMainWindow()

        // 新增：自动初始化工作区监控
        try {
          const currentWorkspace = await this.apiClient.getWorkspaceCurrent()
          if (currentWorkspace && currentWorkspace.workspace) {
            logger.log(`[App] 自动初始化工作区监控: ${currentWorkspace.workspace}`)
            this.setupFileWatcher(currentWorkspace.workspace)
          }
        } catch (error) {
          logger.error('[App] 获取当前工作区失败:', error)
        }
      } else {
        logger.error('[App] 后端服务启动失败，无法继续')
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
      if (this.isQuitting) {
        return
      }
      logger.log('[App] before-quit 事件触发，开始清理资源')
      event.preventDefault()
      this.isQuitting = true

      // 使用 stopBackendService 方法优雅关闭后端服务
      this.stopBackendService()

      // 清理其他资源
      this.cleanupResources()

      // 直接退出，不使用 setTimeout
      logger.log('[App] 资源清理完成，退出应用')
      process.exit(0)
    })

    app.on('will-quit', () => {
      if (this.isQuitting) {
        return
      }
      logger.log('[App] will-quit 事件触发')
      this.cleanupResources()
    })

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.windowManager.createMainWindow()
      }
    })
  }

  private cleanupResources(): void {
    logger.log('[App] 开始清理资源')

    try {
      // 清理文件监控器
      if (this.workspaceWatcher) {
        logger.log('[App] 关闭文件监控器')
        this.workspaceWatcher.close()
        this.workspaceWatcher = null
      }

      if (this.fileChangeTimeout) {
        clearTimeout(this.fileChangeTimeout)
        this.fileChangeTimeout = null
      }

      this.pendingChanges.clear()
    } catch (error) {
      logger.error('[App] 清理文件监控器时出错:', error)
    }
    try {
      if (this.wsClient) {
        logger.log('[App] 断开 WebSocket 连接')
        this.wsClient.disconnect()
        this.wsClient = null
        this.isWsInitialized = false // 重置WS状态
      }
    } catch (error) {
      logger.error('[App] 清理 WebSocket 时出错:', error)
    }

    try {
      const mainWindow = this.windowManager.getWindow()
      if (mainWindow && !mainWindow.isDestroyed()) {
        logger.log('[App] 销毁主窗口')
        mainWindow.destroy()
      }
    } catch (error) {
      logger.error('[App] 销毁窗口时出错:', error)
    }

    logger.log('[App] 资源清理完成')
  }
  /**
   * 设置文件监控器
   */
  private setupFileWatcher(workspace: string): void {
    logger.log(`[App] Setting up file watcher for workspace: ${workspace}`)

    if (this.workspaceWatcher) {
      this.workspaceWatcher.close()
      this.workspaceWatcher = null
    }

    try {
      if (!fs.existsSync(workspace)) {
        logger.log(`[App] Workspace directory does not exist: ${workspace}`)
        return
      }

      this.workspacePath = workspace
      this.workspaceWatcher = fs.watch(workspace, {
        recursive: true,
        persistent: true,
        //ignoreInitial: true,
        //awaitWriteFinish: false,
        encoding: 'utf8'
      }, (eventType, filename) => {
        if (this.shouldIgnoreFile(filename)) {
          return
        }
        debugger
        logger.log(`[App] File change detected: ${eventType}, ${filename}`)

        const changeKey = `${eventType}:${filename}`
        const existingChange = this.pendingChanges.get(changeKey)

        if (existingChange) {
          logger.log(`[App] Change already pending, skipping: ${changeKey}`)
          return
        }

        this.pendingChanges.set(changeKey, eventType)

        if (this.fileChangeTimeout) {
          clearTimeout(this.fileChangeTimeout)
        }

        this.fileChangeTimeout = setTimeout(() => {
          this.sendFileChangeEvent(workspace)
          this.pendingChanges.clear()
          this.fileChangeTimeout = null
        }, 2000)
      })
    } catch (error) {
      logger.error(`[App] Failed to set up file watcher: ${error}`)
    }
  }

  /**
   * 判断是否应该忽略文件
   */
  private shouldIgnoreFile(filename: string): boolean {
    const basename = path.basename(filename)
    return this.IGNORE_PATTERNS.some(pattern => basename.includes(pattern))
  }

  /**
   * 发送文件变化事件到前端
   */
  private sendFileChangeEvent(workspace: string): void {
    const mainWindow = this.windowManager.getWindow()
    if (!mainWindow) {
      logger.log('[App] No main window, skipping file change event')
      return
    }

    logger.log('[App] Sending workspace_files_changed event')

    // 获取待发送的变化列表
    const changes = Array.from(this.pendingChanges.entries()).map(([key, type]) => ({
      path: key.split(':')[1] || key,
      type: type
    }))

    mainWindow.webContents.send('ws:workspace-files-changed', {
      source: 'file_watcher',
      workspace: workspace,
      changes: changes,
      timestamp: Date.now()
    })
  }
}


// 修复：确保只实例化一次App
let appInstance: App | null = null

if (!appInstance) {
  appInstance = new App()
  appInstance.start()
}