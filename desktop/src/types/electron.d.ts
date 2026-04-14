declare global {
  interface FileTreeNode {
    id: string
    label: string
    path: string
    children?: FileTreeNode[]
    isDirectory: boolean
  }

  interface Window {
    electronAPI: {
      system: {
        getBackendPort: () => number
      }
      window: {
        minimize: () => Promise<void>
        toggle: () => Promise<void>
        maximize: () => Promise<void>
        isMaximized: () => Promise<boolean>
        edgeCheck: () => Promise<boolean>
      }
      file: {
        select: (filters?: any) => Promise<string | null>
        selectDirectory: () => Promise<string | null>
        selectFiles: (filters?: any) => Promise<string[]>
        save: (defaultPath?: string, filters?: any) => Promise<string | null>
        openExplorer: (filePath: string) => Promise<void>
        openFile: (filePath: string) => Promise<string>
        readDirectoryTree: (dirPath: string, maxDepth?: number) => Promise<FileTreeNode | null>
      }
      api: {
        getSessions: () => Promise<any[]>
        getWorkspaceSessions: (workspacePath: string) => Promise<{ sessions: any[] }>
        getSessionHistory: (sessionId: string, maxTurns?: number) => Promise<any>
        createSession: (userName?: string) => Promise<any>
        deleteSession: (sessionId: string) => Promise<void>
        executeTask: (task: string, sessionId: string, modelOverride?: string) => Promise<any>
        getTaskStatus: (executionId: string) => Promise<any>
        retryTask: (executionId: string, stepIndex?: number, userInput?: string) => Promise<void>
        cancelTask: (executionId: string) => Promise<void>
        getCheckpoints: () => Promise<any[]>
        resumeCheckpoint: (sessionId: string) => Promise<any>
        deleteCheckpoint: (sessionId: string) => Promise<void>
        getSkills: () => Promise<any[]>
        installSkill: (skillData: any, skillFiles: Record<string, string>) => Promise<any>
        diagnoseSkill: (skillId: string) => Promise<any>
        reloadSkill: (skillId: string) => Promise<void>
        getResourceUsage: () => Promise<any>
        getConfig: () => Promise<any>
        updateConfig: (config: any) => Promise<void>
        getSessionInfo: (sessionId: string) => Promise<any>
        updateSessionTitle: (sessionId: string, title: string) => Promise<void>
      }
      workspace: {
        getCurrent: () => Promise<any>
        switch: (workspacePath: string, force?: boolean) => Promise<any>
        initialize: (workspacePath?: string) => Promise<any>
        validate: (workspacePath: string) => Promise<any>
      }
      ws: {
        connect: (sessionId?: string) => Promise<void>
        disconnect: () => Promise<void>
        isConnected: () => Promise<boolean>
        sendMessage: (message: string, sessionId?: string) => Promise<void>
        onConnected: (callback: () => void) => void
        onDisconnected: (callback: () => void) => void
        onThoughtChain: (callback: (data: any) => void) => void
        onStepStart: (callback: (data: any) => void) => void
        onStepEnd: (callback: (data: any) => void) => void
        onTaskStart: (callback: (data: any) => void) => void
        onTaskEnd: (callback: (data: any) => void) => void
        onTaskFailed: (callback: (data: any) => void) => void
        onThinkStart: (callback: (data: any) => void) => void
        onThinkStream: (callback: (data: any) => void) => void
        onThinkFinal: (callback: (data: any) => void) => void
        onPlanStart: (callback: (data: any) => void) => void
        onPlanFinal: (callback: (data: any) => void) => void
        removeAllListeners: (channel: string) => void
      }
    }
  }
}

export {}
