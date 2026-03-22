import { BrowserWindow, Menu, Tray, app, nativeImage, screen } from 'electron'
import path from 'path'

export class WindowManager {
  private mainWindow: BrowserWindow | null = null
  private tray: Tray | null = null
  private isEdgeHidden: boolean = false
  private edgePosition: { x: number; y: number } | null = null
  private edgeHideTimeout: NodeJS.Timeout | null = null

  createMainWindow(): BrowserWindow {
    this.mainWindow = new BrowserWindow({
      width: 1200,
      height: 900,
      minWidth: 800,
      minHeight: 600,
      frame: false,
      transparent: false,
      resizable: true,
      icon: path.join(__dirname, '../../build/icon.ico'),
      webPreferences: {
        preload: path.join(__dirname, '../preload/index.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false
      }
    })

    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.loadURL('http://localhost:5175')
      this.mainWindow.webContents.openDevTools()
    } else {
      this.mainWindow.loadFile(path.join(__dirname, '../../dist/index.html'))
    }

    this.mainWindow.on('close', (event) => {
      event.preventDefault()
      this.minimizeToTray()
    })

    this.mainWindow.on('minimize', () => {
      this.hideToEdge()
    })

    this.setupTray()

    return this.mainWindow
  }

  private setupTray(): void {
    try {
      // 尝试多种可能的图标路径
      const possibleIconPaths = [
        path.join(__dirname, '../../src/assets/images/logo_256x256.ico'),
        path.join(__dirname, '../../../src/assets/images/logo_256x256.ico'),
        path.join(__dirname, '../../build/icon.ico'),
        path.join(process.resourcesPath, 'app.asar.unpacked/build/icon.ico'),
        path.join(process.resourcesPath, 'app.asar/build/icon.ico')
      ]

      let trayIcon = null
      for (const iconPath of possibleIconPaths) {
        try {
          trayIcon = nativeImage.createFromPath(iconPath)
          if (!trayIcon.isEmpty()) {
            console.log(`[Tray] 使用图标路径：${iconPath}`)
            break
          }
        } catch (error) {
          continue
        }
      }

      if (!trayIcon || trayIcon.isEmpty()) {
        // 如果所有路径都失败，创建一个简单的图标
        console.warn('[Tray] 未找到图标文件，使用默认图标')
        trayIcon = nativeImage.createEmpty()
      }

      this.tray = new Tray(trayIcon)
    } catch (error) {
      console.error('[Tray] 创建系统托盘失败:', error)
      // If all else fails, use default tray
      this.tray = new Tray(nativeImage.createEmpty())
    }
    this.tray.setToolTip('Lingxi Agent')

    // 创建右键菜单
    const contextMenu = Menu.buildFromTemplate([
      {
        label: '显示/隐藏窗口',
        click: () => {
          if (this.mainWindow) {
            if (this.mainWindow.isVisible()) {
              this.mainWindow.hide()
            } else {
              this.mainWindow.show()
              this.mainWindow.focus()
            }
          }
        }
      },
      {
        type: 'separator'
      },
      {
        label: '退出',
        click: () => {
          if (this.mainWindow) {
            this.mainWindow.destroy()
          }
          app.quit()
        }
      }
    ])

    // 设置右键菜单
    this.tray.setContextMenu(contextMenu)

    this.tray.on('click', () => {
      if (this.mainWindow) {
        if (this.mainWindow.isVisible()) {
          this.mainWindow.hide()
        } else {
          this.mainWindow.show()
          this.mainWindow.focus()
        }
      }
    })
  }

  minimizeToTray(): void {
    if (this.mainWindow) {
      this.mainWindow.hide()
    }
  }

  hideToEdge(): void {
    if (!this.mainWindow) return

    const bounds = this.mainWindow.getBounds()
    this.edgePosition = { x: bounds.x, y: bounds.y }

    if (this.edgeHideTimeout) {
      clearTimeout(this.edgeHideTimeout)
    }

    this.edgeHideTimeout = setTimeout(() => {
      if (this.mainWindow) {
        this.isEdgeHidden = true
        this.mainWindow.hide()
      }
    }, 300)
  }

  restoreFromEdge(): void {
    if (!this.mainWindow || !this.edgePosition) return

    this.isEdgeHidden = false

    if (this.edgeHideTimeout) {
      clearTimeout(this.edgeHideTimeout)
      this.edgeHideTimeout = null
    }

    this.mainWindow.setPosition(this.edgePosition.x, this.edgePosition.y)
    this.mainWindow.show()
    this.mainWindow.focus()
  }

  toggleWindow(): void {
    if (!this.mainWindow) return

    if (this.isEdgeHidden) {
      this.restoreFromEdge()
    } else if (this.mainWindow.isVisible()) {
      this.hideToEdge()
    } else {
      this.mainWindow.show()
      this.mainWindow.focus()
    }
  }

  checkEdgePosition(): boolean {
    if (!this.mainWindow) return false

    const bounds = this.mainWindow.getBounds()
    const { width: screenWidth } = screen.getPrimaryDisplay().workAreaSize

    return bounds.x >= screenWidth - 50 || bounds.x <= 50
  }

  getWindow(): BrowserWindow | null {
    return this.mainWindow
  }

  isHidden(): boolean {
    return this.isEdgeHidden || (this.mainWindow ? !this.mainWindow.isVisible() : true)
  }

  maximizeWindow(): void {
    if (!this.mainWindow) return

    if (this.mainWindow.isMaximized()) {
      this.mainWindow.unmaximize()
    } else {
      this.mainWindow.maximize()
    }
  }

  isMaximized(): boolean {
    return this.mainWindow ? this.mainWindow.isMaximized() : false
  }
}
