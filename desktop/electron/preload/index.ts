import { contextBridge, ipcRenderer } from 'electron'

const electronAPI = {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    toggle: () => ipcRenderer.invoke('window:toggle'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    isMaximized: () => ipcRenderer.invoke('window:is-maximized'),
    edgeCheck: () => ipcRenderer.invoke('window:edge-check')
  },

  file: {
    select: (filters?: any) => ipcRenderer.invoke('file:select', filters),
    selectDirectory: () => ipcRenderer.invoke('file:select-directory'),
    selectFiles: (filters?: any) => ipcRenderer.invoke('file:select-files', filters),
    save: (defaultPath?: string, filters?: any) => ipcRenderer.invoke('file:save', defaultPath, filters),
    openExplorer: (filePath: string) => {
      console.log('[Preload] openExplorer:', filePath)
      return ipcRenderer.invoke('file:open-explorer', filePath)
    },
    openFile: (filePath: string) => {
      console.log('[Preload] openFile:', filePath)
      return ipcRenderer.invoke('file:open-file', filePath)
    },
    readDirectoryTree: (dirPath: string, maxDepth?: number) => ipcRenderer.invoke('file:read-directory-tree', dirPath, maxDepth)
  },

  api: {
    getSessions: () => ipcRenderer.invoke('api:get-sessions'),
    getSessionHistory: (sessionId: string, maxTurns?: number) => ipcRenderer.invoke('api:get-session-history', sessionId, maxTurns),
    createSession: (userName?: string) => ipcRenderer.invoke('api:create-session', userName),
    deleteSession: (sessionId: string) => ipcRenderer.invoke('api:delete-session', sessionId),
    updateSessionName: (sessionId: string, name: string) => ipcRenderer.invoke('api:update-session-name', sessionId, name),
    clearSessionHistory: (sessionId: string) => ipcRenderer.invoke('api:clear-session-history', sessionId),
    executeTask: (task: string, sessionId: string, modelOverride?: string) => ipcRenderer.invoke('api:execute-task', task, sessionId, modelOverride),
    getTaskStatus: (executionId: string) => ipcRenderer.invoke('api:get-task-status', executionId),
    retryTask: (executionId: string, stepIndex?: number, userInput?: string) => ipcRenderer.invoke('api:retry-task', executionId, stepIndex, userInput),
    cancelTask: (executionId: string) => ipcRenderer.invoke('api:cancel-task', executionId),
    getCheckpoints: () => ipcRenderer.invoke('api:get-checkpoints'),
    resumeCheckpoint: (sessionId: string) => ipcRenderer.invoke('api:resume-checkpoint', sessionId),
    deleteCheckpoint: (sessionId: string) => ipcRenderer.invoke('api:delete-checkpoint', sessionId),
    getSkills: () => ipcRenderer.invoke('api:get-skills'),
    installSkill: (skillData: any, skillFiles: Record<string, string>) => ipcRenderer.invoke('api:install-skill', skillData, skillFiles),
    diagnoseSkill: (skillId: string) => ipcRenderer.invoke('api:diagnose-skill', skillId),
    reloadSkill: (skillId: string) => ipcRenderer.invoke('api:reload-skill', skillId),
    getResourceUsage: () => ipcRenderer.invoke('api:get-resource-usage'),
    getConfig: () => ipcRenderer.invoke('api:get-config'),
    updateConfig: (config: any) => ipcRenderer.invoke('api:update-config', config),
    getSessionInfo: (sessionId: string) => ipcRenderer.invoke('api:get-session-info', sessionId),
    getWorkspaceSessions: (workspacePath?: string) => ipcRenderer.invoke('api:get-workspace-sessions', workspacePath)
  },

  workspace: {
    getCurrent: () => ipcRenderer.invoke('workspace:get-current'),
    switch: (workspacePath: string, force?: boolean) => ipcRenderer.invoke('workspace:switch', workspacePath, force),
    initialize: (workspacePath?: string) => ipcRenderer.invoke('workspace:initialize', workspacePath),
    validate: (workspacePath: string) => ipcRenderer.invoke('workspace:validate', workspacePath)
  },


}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)

export type ElectronAPI = typeof electronAPI
