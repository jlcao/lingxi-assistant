import { dialog, shell } from 'electron'
import type { FileFilter } from '../../src/types'

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
      const path = require('path')
      const resolvedPath = path.resolve(filePath)
      return !resolvedPath.includes('..')
    } catch {
      return false
    }
  }

  validateFileSize(filePath: string, maxSize: number = 100 * 1024 * 1024): boolean {
    try {
      const fs = require('fs')
      const stats = fs.statSync(filePath)
      return stats.size <= maxSize
    } catch {
      return false
    }
  }
}
