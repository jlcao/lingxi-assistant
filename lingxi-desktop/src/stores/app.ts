import { defineStore } from 'pinia'
import type { SessionWithTasks, Task } from '../types'

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
    sessions: new Map<string, SessionWithTasks>(),
    checkpoints: [] as Checkpoint[],
    activeCheckpoints: [] as Checkpoint[],
    wsConnected: false,
    thoughtChain: null as ThoughtChain | null,
    modelRoute: null as any,
    resourceUsage: null as ResourceUsage | null,
    loading: false
  }),
  getters: {
    currentSession: (state): SessionWithTasks | null => {
      if (!state.currentSessionId) return null
      return state.sessions.get(state.currentSessionId) || null
    },
    currentTasks: (state): Task[] => {
      if (!state.currentSessionId) return []
      const session = state.sessions.get(state.currentSessionId)
      return session?.tasks || []
    },
    sessionList: (state): SessionWithTasks[] => {
      return Array.from(state.sessions.values())
    }
  },
  actions: {
    setCurrentWorkspace(path: string) {
      this.currentWorkspace = path
    },
    setCurrentSession(id: string | null) {
      this.currentSessionId = id
    },
    setSessions(sessions: SessionWithTasks[]) {
      this.sessions.clear()
      sessions.forEach(session => {
        this.sessions.set(session.id, session)
      })
    },
    addSession(session: SessionWithTasks) {
      this.sessions.set(session.id, session)
    },
    updateSession(sessionId: string, updates: Partial<SessionWithTasks>) {
      const session = this.sessions.get(sessionId)
      if (session) {
        this.sessions.set(sessionId, { ...session, ...updates })
      }
    },
    deleteSession(id: string) {
      this.sessions.delete(id)
      if (this.currentSessionId === id) {
        this.currentSessionId = null
      }
    },
    setSessionTasks(sessionId: string, tasks: Task[]) {
      const session = this.sessions.get(sessionId)
      if (session) {
        this.sessions.set(sessionId, { ...session, tasks })
      }
    },
    addTaskToSession(sessionId: string, task: Task) {
      const session = this.sessions.get(sessionId)
      if (session) {
        const updatedTasks = [...session.tasks, task]
        this.sessions.set(sessionId, { ...session, tasks: updatedTasks })
      }
    },
    updateTaskInSession(sessionId: string, taskId: string, updates: Partial<Task>) {
      const session = this.sessions.get(sessionId)
      if (session) {
        const updatedTasks = session.tasks.map(task =>
          task.task_id === taskId ? { ...task, ...updates } : task
        )
        this.sessions.set(sessionId, { ...session, tasks: updatedTasks })
      }
    },
    getTaskFromSession(sessionId: string, taskId: string): Task | null {
      const session = this.sessions.get(sessionId)
      if (!session) return null
      return session.tasks.find(task => task.task_id === taskId) || null
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
