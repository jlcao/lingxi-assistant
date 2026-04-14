import { dialog, shell } from 'electron'
import * as fs from 'fs'
import * as path from 'path'
import type { FileFilter } from '../../src/types'

export interface FileTreeNode {
  id: string
  label: string
  path: string
  children?: FileTreeNode[]
  isDirectory: boolean
}

export class FileManager {
  async selectFile(filters?: FileFilter[]): Promise<string | null> {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: filters ? this.convertFilters(filters) : undefined
    })

    return result.canceled ? null : result.filePaths[0]
  }

  async selectDirectory(): Promise<string | null> {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory']
    })

    return result.canceled ? null : result.filePaths[0]
  }

  async selectFiles(filters?: FileFilter[]): Promise<string[]> {
    const result = await dialog.showOpenDialog({
      properties: ['openFile', 'multiSelections'],
      filters: filters ? this.convertFilters(filters) : undefined
    })

    return result.canceled ? [] : result.filePaths
  }

  async saveFile(defaultPath?: string, filters?: FileFilter[]): Promise<string | null> {
    const result = await dialog.showSaveDialog({
      defaultPath,
      filters: filters ? this.convertFilters(filters) : undefined
    })

    return result.canceled ? null : result.filePath
  }

  async openInExplorer(filePath: string): Promise<void> {
    await shell.showItemInFolder(filePath)
  }

  async openFile(filePath: string): Promise<string> {
    console.log('[FileManager] openFile called with:', filePath)
    try {
      const result = await shell.openPath(filePath)
      console.log('[FileManager] File open result:', result, 'for:', filePath)
      if (result) {
        console.error('[FileManager] File open failed with error:', result)
        throw new Error(`shell.openPath 返回错误：${result}`)
      }
      console.log('[FileManager] 文件打开成功！', filePath)
      return 'success'
    } catch (error) {
      console.error('[FileManager] Failed to open file:', filePath, error)
      throw error
    }
  }

  async openExternal(url: string): Promise<void> {
    await shell.openExternal(url)
  }

  private convertFilters(filters: FileFilter[]): Electron.FileFilter[] {
    return filters.map((filter) => ({
      name: filter.name,
      extensions: filter.extensions
    }))
  }

  validateFilePath(filePath: string): boolean {
    try {
      const resolvedPath = path.resolve(filePath)
      return !resolvedPath.includes('..')
    } catch {
      return false
    }
  }

  validateFileSize(filePath: string, maxSize: number = 100 * 1024 * 1024): boolean {
    try {
      const stats = fs.statSync(filePath)
      return stats.size <= maxSize
    } catch {
      return false
    }
  }

  async readDirectoryTree(dirPath: string, maxDepth: number = 3): Promise<FileTreeNode | null> {
    try {
      if (!fs.existsSync(dirPath)) {
        return null
      }
      return this.buildTree(dirPath, dirPath, 0, maxDepth)
    } catch (error) {
      console.error('Failed to read directory tree:', error)
      return null
    }
  }

  private buildTree(
    currentPath: string,
    rootPath: string,
    depth: number,
    maxDepth: number
  ): FileTreeNode {
    const stats = fs.statSync(currentPath)
    const name = path.basename(currentPath)
    const relativePath = path.relative(rootPath, currentPath)

    const node: FileTreeNode = {
      id: relativePath || name,
      label: name,
      path: currentPath,
      isDirectory: stats.isDirectory()
    }

    if (stats.isDirectory() && depth < maxDepth) {
      try {
        const entries = fs.readdirSync(currentPath, { withFileTypes: true })
        const children: FileTreeNode[] = []

        const ignorePatterns = ['node_modules', '.git', '.svn', '__pycache__', '.DS_Store', 'dist', 'build', '.cache']
        
        for (const entry of entries) {
          if (ignorePatterns.includes(entry.name)) {
            continue
          }
          const childPath = path.join(currentPath, entry.name)
          try {
            const childNode = this.buildTree(childPath, rootPath, depth + 1, maxDepth)
            children.push(childNode)
          } catch {
            continue
          }
        }

        children.sort((a, b) => {
          if (a.isDirectory && !b.isDirectory) return -1
          if (!a.isDirectory && b.isDirectory) return 1
          return a.label.localeCompare(b.label)
        })

        if (children.length > 0) {
          node.children = children
        }
      } catch {
        node.children = []
      }
    }

    return node
  }
}
