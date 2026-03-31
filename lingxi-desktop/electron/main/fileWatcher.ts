import * as fs from 'fs'
import * as path from 'path'
import { logger } from './logger'

export class FileWatcher {
  private workspaceWatcher: fs.FSWatcher | null = null
  private workspacePath: string | null = null
  private fileChangeTimeout: NodeJS.Timeout | null = null
  private pendingChanges: Map<string, 'added' | 'modified' | 'deleted'> = new Map()
  private onFileChangeCallback?: (workspace: string, changes: Array<{ path: string; type: string }>) => void

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

  setupFileWatcher(workspace: string, onFileChangeCallback?: (workspace: string, changes: Array<{ path: string; type: string }>) => void): void {
    logger.log(`[FileWatcher] Setting up file watcher for workspace: ${workspace}`)

    if (this.workspaceWatcher) {
      this.workspaceWatcher.close()
      this.workspaceWatcher = null
    }

    this.onFileChangeCallback = onFileChangeCallback

    try {
      if (!fs.existsSync(workspace)) {
        logger.log(`[FileWatcher] Workspace directory does not exist: ${workspace}`)
        return
      }

      this.workspacePath = workspace
      this.workspaceWatcher = fs.watch(workspace, {
        recursive: true,
        persistent: true,
        encoding: 'utf8'
      }, (eventType, filename) => {
        if (this.shouldIgnoreFile(filename)) {
          return
        }
        logger.log(`[FileWatcher] File change detected: ${eventType}, ${filename}`)

        const changeKey = `${eventType}:${filename}`
        const existingChange = this.pendingChanges.get(changeKey)

        if (existingChange) {
          logger.log(`[FileWatcher] Change already pending, skipping: ${changeKey}`)
          return
        }

        this.pendingChanges.set(changeKey, eventType as 'added' | 'modified' | 'deleted')

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
      logger.error(`[FileWatcher] Failed to set up file watcher: ${error}`)
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
   * 发送文件变化事件
   */
  private sendFileChangeEvent(workspace: string): void {
    logger.log('[FileWatcher] Sending workspace_files_changed event')

    // 获取待发送的变化列表
    const changes = Array.from(this.pendingChanges.entries()).map(([key, type]) => ({
      path: key.split(':')[1] || key,
      type: type
    }))

    this.onFileChangeCallback?.(workspace, changes)
  }

  cleanup(): void {
    try {
      // 清理文件监控器
      if (this.workspaceWatcher) {
        logger.log('[FileWatcher] 关闭文件监控器')
        this.workspaceWatcher.close()
        this.workspaceWatcher = null
      }

      if (this.fileChangeTimeout) {
        clearTimeout(this.fileChangeTimeout)
        this.fileChangeTimeout = null
      }

      this.pendingChanges.clear()
      this.workspacePath = null
    } catch (error) {
      logger.error('[FileWatcher] 清理文件监控器时出错:', error)
    }
  }

  getCurrentWorkspace(): string | null {
    return this.workspacePath
  }

  isWatching(): boolean {
    return this.workspaceWatcher !== null
  }
}
