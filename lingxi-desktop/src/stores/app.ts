import { defineStore } from 'pinia'

interface Session {
  id: string
  name: string
}

interface Checkpoint {
  id: string
  name: string
  timestamp: number
}

interface ThoughtChain {
  taskId: string
  steps: any[]
  status: string
}

interface ResourceUsage {
  cpu: number
  memory: number
  disk: number
}

export const useAppStore = defineStore('app', {
  state: () => ({
    currentWorkspace: '',
    currentSessionId: null as string | null,
    sessions: [] as Session[],
    selectedSessions: [] as string[],
    turns: {} as Record<string, any[]>, // 改为按会话ID存储消息
    checkpoints: [] as Checkpoint[],
    activeCheckpoints: [] as Checkpoint[],
    wsConnected: false,
    thoughtChain: null as ThoughtChain | null,
    modelRoute: null as any,
    resourceUsage: null as ResourceUsage | null,
    loading: false
  }),
  actions: {
    setCurrentWorkspace(path: string) {
      this.currentWorkspace = path
    },
    setCurrentSession(id: string | null) {
      this.currentSessionId = id
    },
    setSessions(sessions: Session[]) {
      this.sessions = sessions
    },
    setTurns(sessionId: string, turns: any[]) {
      this.turns[sessionId] = turns
    },
    
    getTurns(sessionId: string): any[] {
      return this.turns[sessionId] || []
    },
    
    addTurn(sessionId: string, turn: any) {
      if (!this.turns[sessionId]) {
        this.turns[sessionId] = []
      }
      this.turns[sessionId].push(turn)
    },
    setCheckpoints(checkpoints: Checkpoint[]) {
      this.checkpoints = checkpoints
      this.activeCheckpoints = checkpoints
    },
    setWsConnected(connected: boolean) {
      this.wsConnected = connected
    },
    setThoughtChain(thoughtChain: ThoughtChain) {
      this.thoughtChain = thoughtChain
    },
    setModelRoute(modelRoute: any) {
      this.modelRoute = modelRoute
    },
    setResourceUsage(resourceUsage: ResourceUsage) {
      this.resourceUsage = resourceUsage
    },
    setLoading(loading: boolean) {
      this.loading = loading
    },
    addSession(name: string) {
      const id = Date.now().toString()
      this.sessions.unshift({ id, name })
      return id
    },
    deleteSession(id: string) {
      this.sessions = this.sessions.filter(session => session.id !== id)
    },
    toggleSessionSelection(id: string) {
      const index = this.selectedSessions.indexOf(id)
      if (index > -1) {
        this.selectedSessions.splice(index, 1)
      } else {
        this.selectedSessions.push(id)
      }
    }
  }
})
