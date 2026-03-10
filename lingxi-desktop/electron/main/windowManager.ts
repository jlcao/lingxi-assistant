import { BrowserWindow, screen, Tray, nativeImage } from 'electron'
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
        sandbox: true
      }
    })

    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.loadURL('http://localhost:5173')
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
      const iconPath = path.join(__dirname, '../../build/icon.ico')
      const trayIcon = nativeImage.createFromPath(iconPath)
      this.tray = new Tray(trayIcon)
    } catch (error) {
      // If icon file doesn't exist, use default tray
      this.tray = new Tray(nativeImage.createEmpty())
    }
    this.tray.setToolTip('Lingxi Agent')

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
