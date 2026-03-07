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
    openExplorer: (filePath: string) => ipcRenderer.invoke('file:open-explorer', filePath),
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
    executeTaskStream: (task: string, sessionId: string, modelOverride?: string | null, enableHeartbeat?: boolean, heartbeatInterval?: number) => ipcRenderer.invoke('api:execute-task-stream', task, sessionId, modelOverride, enableHeartbeat, heartbeatInterval),
    setSSEConfig: (config: any) => ipcRenderer.invoke('api:set-sse-config', config),
    getSSEConnectionStatus: () => ipcRenderer.invoke('api:get-sse-connection-status'),
    abortSSEStream: () => ipcRenderer.invoke('api:abort-sse-stream'),
    sseReconnect: () => ipcRenderer.invoke('api:sse-reconnect')
  },

  sse: {
    onTaskStart: (callback: (data: any) => void) => ipcRenderer.on('sse:task-start', (_, data) => callback(data)),
    onPlanStart: (callback: (data: any) => void) => ipcRenderer.on('sse:plan-start', (_, data) => callback(data)),
    onThinkStart: (callback: (data: any) => void) => ipcRenderer.on('sse:think-start', (_, data) => callback(data)),
    onThinkStream: (callback: (data: any) => void) => ipcRenderer.on('sse:think-stream', (_, data) => callback(data)),
    onThinkFinal: (callback: (data: any) => void) => ipcRenderer.on('sse:think-final', (_, data) => callback(data)),
    onPlanFinal: (callback: (data: any) => void) => ipcRenderer.on('sse:plan-final', (_, data) => callback(data)),
    onStepStart: (callback: (data: any) => void) => ipcRenderer.on('sse:step-start', (_, data) => callback(data)),
    onStepEnd: (callback: (data: any) => void) => ipcRenderer.on('sse:step-end', (_, data) => callback(data)),
    onTaskEnd: (callback: (data: any) => void) => ipcRenderer.on('sse:task-end', (_, data) => callback(data)),
    onTaskFailed: (callback: (data: any) => void) => ipcRenderer.on('sse:task-failed', (_, data) => callback(data)),
    onTaskCancelled: (callback: (data: any) => void) => ipcRenderer.on('sse:task-cancelled', (_, data) => callback(data)),
    onPing: (callback: (data: any) => void) => ipcRenderer.on('sse:ping', (_, data) => callback(data)),
    onStreamEnd: (callback: () => void) => ipcRenderer.on('sse:stream-end', callback),
    onError: (callback: (error: Error) => void) => ipcRenderer.on('sse:error', (_, error) => callback(error)),
    onReconnecting: (callback: (attempt: number, maxRetries: number) => void) => ipcRenderer.on('sse:reconnecting', (_, attempt, maxRetries) => callback(attempt, maxRetries)),
    onReconnectSuccess: (callback: () => void) => ipcRenderer.on('sse:reconnect-success', callback),
    onReconnectFailed: (callback: () => void) => ipcRenderer.on('sse:reconnect-failed', callback),
    removeAllListeners: (channel: string) => ipcRenderer.removeAllListeners(channel)
  },

  ws: {
    connect: (sessionId?: string) => ipcRenderer.invoke('ws:connect', sessionId),
    disconnect: () => ipcRenderer.invoke('ws:disconnect'),
    isConnected: () => ipcRenderer.invoke('ws:is-connected'),
    sendMessage: (message: string, sessionId?: string) => ipcRenderer.invoke('ws:send-message', message, sessionId),
    onConnected: (callback: () => void) => ipcRenderer.on('ws:connected', callback),
    onDisconnected: (callback: () => void) => ipcRenderer.on('ws:disconnected', callback),
    onThoughtChain: (callback: (data: any) => void) => ipcRenderer.on('ws:thought-chain', (_, data) => callback(data)),
    onStepStart: (callback: (data: any) => void) => ipcRenderer.on('ws:step-start', (_, data) => callback(data)),
    onStepEnd: (callback: (data: any) => void) => ipcRenderer.on('ws:step-end', (_, data) => callback(data)),
    onTaskStart: (callback: (data: any) => void) => ipcRenderer.on('ws:task-start', (_, data) => callback(data)),
    onTaskEnd: (callback: (data: any) => void) => ipcRenderer.on('ws:task-end', (_, data) => callback(data)),
    onTaskFailed: (callback: (data: any) => void) => ipcRenderer.on('ws:task-failed', (_, data) => callback(data)),
    onThinkStart: (callback: (data: any) => void) => ipcRenderer.on('ws:think-start', (_, data) => callback(data)),
    onThinkStream: (callback: (data: any) => void) => ipcRenderer.on('ws:think-stream', (_, data) => callback(data)),
    onThinkFinal: (callback: (data: any) => void) => ipcRenderer.on('ws:think-final', (_, data) => callback(data)),
    onPlanStart: (callback: (data: any) => void) => ipcRenderer.on('ws:plan-start', (_, data) => callback(data)),
    onPlanFinal: (callback: (data: any) => void) => ipcRenderer.on('ws:plan-final', (_, data) => callback(data)),
    removeAllListeners: (channel: string) => ipcRenderer.removeAllListeners(channel)
  }
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)

export type ElectronAPI = typeof electronAPI
