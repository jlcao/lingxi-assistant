import { app, BrowserWindow, ipcMain } from 'electron'
import { FileManager } from './fileManager'
import { WindowManager } from './windowManager'
import { BackendManager } from './backendManager'
import { FileWatcher } from './fileWatcher'

// 导入日志模块
import { logger } from './logger'

class App {
  private windowManager: WindowManager
  private backendManager: BackendManager
  private fileManager: FileManager
  private fileWatcher: FileWatcher
  private isQuitting: boolean = false

  constructor() {
    this.backendManager = new BackendManager()
    this.windowManager = new WindowManager()
    this.fileManager = new FileManager()
    this.fileWatcher = new FileWatcher()

    this.setupIpcHandlers()

    // 确保前端退出时后端也会退出（只添加一次）
    process.on('exit', () => {
      this.backendManager.stopBackendService()
    })
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
    // ===== 系统相关 IPC 处理 =====
    ipcMain.handle('system:get-backend-port', async () => {
      return this.backendManager.getBackendPort()
    })

    // ===== 窗口相关 IPC 处理 =====
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

    // ===== 文件相关 IPC 处理 =====
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

    // ===== 工作区相关 IPC 处理 =====
    ipcMain.handle('workspace:get-current', async () => {
      const workspacePath = this.fileWatcher.getCurrentWorkspace()
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

      // 设置文件监控
      this.setupFileWatcher(workspacePath)

      return { success: true, message: 'Workspace switched' }
    })

    ipcMain.handle('workspace:initialize', async (_, workspacePath) => {
      logger.log(`[App] workspace:initialize called with: ${workspacePath}`)

      // 设置文件监控
      this.setupFileWatcher(workspacePath)

      return { success: true, message: 'Workspace initialized' }
    })

    ipcMain.handle('workspace:validate', async (_, workspacePath) => {
      return { success: true, message: 'Workspace validated' }
    })


  }

  async start(): Promise<void> {
    // 修复：将所有逻辑包裹在 once 中，防止 ready 事件重复触发
    app.once('ready', async () => {
      // 启动后端服务并等待完成
      logger.log('[App] 正在启动后端服务...')
      const backendStarted = await this.backendManager.startBackendService()

      if (backendStarted) {
        logger.log('[App] 后端服务启动成功，创建主窗口')
        // 创建主窗口
        this.windowManager.createMainWindow()

        // 新增：自动初始化工作区监控
        try {
          const currentWorkspace = this.fileWatcher.getCurrentWorkspace()
          if (currentWorkspace) {
            logger.log(`[App] 自动初始化工作区监控: ${currentWorkspace}`)
            this.setupFileWatcher(currentWorkspace)
          }
        } catch (error) {
          logger.error('[App] 获取当前工作区失败:', error)
        }
      } else {
        logger.error('[App] 后端服务启动失败，无法继续')
        // 可以选择退出应用或显示错误界面
        const { dialog } = require('electron')
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
      this.backendManager.stopBackendService()

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
      this.fileWatcher.cleanup()
    } catch (error) {
      logger.error('[App] 清理文件监控器时出错:', error)
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
    this.fileWatcher.setupFileWatcher(workspace, (workspacePath, changes) => {
      const mainWindow = this.windowManager.getWindow()
      if (!mainWindow) {
        logger.log('[App] No main window, skipping file change event')
        return
      }

      mainWindow.webContents.send('ws:workspace-files-changed', {
        source: 'file_watcher',
        workspace: workspacePath,
        changes: changes,
        timestamp: Date.now()
      })
    })
  }
}


// 修复：确保只实例化一次App
let appInstance: App | null = null

if (!appInstance) {
  appInstance = new App()
  appInstance.start()
}