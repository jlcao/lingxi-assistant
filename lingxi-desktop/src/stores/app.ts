import { defineStore } from 'pinia'

interface Session {
  sessionId: string
  userName: string
  title: string
  tasks: Task[]
  totalTokens:number
  createdAt: number
  updatedAt: number
}

interface Task {
  taskId: string
  taskType: string
  plan: string[]
  userInput: string
  result: string
  description: string
  status: string
  replanCount: number
  errorInfo: string
  inputTokens: number
  outputTokens: number
  createdAt: number
  updatedAt: number
    
  planThinking: boolean
  planThinkingContent: string

  steps: Step[]
}

interface Step {
  stepId: string
  stepIndex: number
  stepType: string
  description: string
  status: string
  thought: string
  result: string
  skillCall: string
  isThinking: boolean
  resultDescription: string
  createdAt: number
  updatedAt: number
}

interface Checkpoint {
  id: string
  name: string
  timestamp: number
}

interface ResourceUsage {
  cpu: number
  memory: number
  disk: number
}

export const useAppStore = defineStore('app', {
  state: () => ({
    currentSessionName: '',
    currentWorkspace: '',
    currentSessionId: null as string | null,
    sessions: [] as Session[],
    checkpoints: [] as Checkpoint[],
    activeCheckpoints: [] as Checkpoint[],
    wsConnected: false,
    modelRoute: null as any,
    resourceUsage: null as ResourceUsage | null,
    loading: false,
    selectedSessions: [] as string[]
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
    setCheckpoints(checkpoints: Checkpoint[]) {
      this.checkpoints = checkpoints
      this.activeCheckpoints = checkpoints
    },
    setWsConnected(connected: boolean) {
      this.wsConnected = connected
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
      const sessionId = Date.now().toString()
      this.sessions.unshift({ 
        sessionId: sessionId, 
        userName: name,
        title: name, 
        tasks: [],  
        totalTokens: 0,
        createdAt: Date.now(),
        updatedAt: Date.now()
      })
      this.setCurrentSession(sessionId)
      return sessionId
    },
    deleteSession(id: string) {
      this.sessions = this.sessions.filter(session => session.sessionId !== id)
    },
    toggleSessionSelection(id: string) {
      const index = this.selectedSessions.indexOf(id)
      if (index > -1) {
        this.selectedSessions.splice(index, 1)
      } else {
        this.selectedSessions.push(id)
      }
    },
    addTask(sessionId:string ,taskId: string, task: Task) {
      const sessionIndex = this.sessions.findIndex(session => session.sessionId === sessionId)
      if (sessionIndex !== -1) {
        const taskIndex = this.sessions[sessionIndex].tasks.findIndex(t => t.taskId === taskId)
        if (taskIndex !== -1) {
          const oldTask = this.sessions[sessionIndex].tasks[taskIndex] 
          this.sessions[sessionIndex].tasks[taskIndex] = {
            ...oldTask,
            ...task,
            updatedAt: Date.now()
          }
        }
        else {
          this.sessions[sessionIndex].tasks.push(task)
        }
      }
    },
    addStep(sessionId: string,taskId: string,stepIndex: number, step: Step) {
      const sessionIndex = this.sessions.findIndex(session => session.sessionId === sessionId)
      if (sessionIndex !== -1) {
        const taskIndex = this.sessions[sessionIndex].tasks.findIndex(t => t.taskId === taskId)
        if (taskIndex !== -1) {
          if(stepIndex > 0){
            stepIndex -= 1
          }
          if(this.sessions[sessionIndex].tasks[taskIndex].steps && 
            this.sessions[sessionIndex].tasks[taskIndex].steps[stepIndex]){
              const oldStep = this.sessions[sessionIndex].tasks[taskIndex].steps[stepIndex]
              this.sessions[sessionIndex].tasks[taskIndex].steps[stepIndex] = {
                ...oldStep,
                ...step,
                updatedAt: Date.now()
              }
          } else {
            if (this.sessions[sessionIndex].tasks[taskIndex].steps){
              this.sessions[sessionIndex].tasks[taskIndex].steps.push ({
                ...step,
                updatedAt: Date.now()
              })
            } else {
              this.sessions[sessionIndex].tasks[taskIndex].steps = [step]
            }
          }
        }
      }
    },
    addThought(sessionId: string,taskId: string,stepIndex: number, thought: string) {
      const sessionIndex = this.sessions.findIndex(session => session.sessionId === sessionId)
      if (sessionIndex !== -1) {
        const taskIndex = this.sessions[sessionIndex].tasks.findIndex(t => t.taskId === taskId)
        if (taskIndex !== -1) {
          if(stepIndex > 0){
            stepIndex -= 1
          }
          const step = this.sessions[sessionIndex].tasks[taskIndex].steps[stepIndex]
          if (step) {
            step.thought = (step.thought || '') + thought
            step.updatedAt = Date.now()
          }
        }
      }
    },
    addThinkThought(sessionId: string,taskId: string, thought: string) {
      const sessionIndex = this.sessions.findIndex(session => session.sessionId === sessionId)
      if (sessionIndex !== -1) {
        const taskIndex = this.sessions[sessionIndex].tasks.findIndex(t => t.taskId === taskId)
        if (taskIndex !== -1) {
          this.sessions[sessionIndex].tasks[taskIndex].planThinkingContent += thought
          this.sessions[sessionIndex].tasks[taskIndex].planThinking = true
          this.sessions[sessionIndex].tasks[taskIndex].updatedAt = Date.now()
        }
      }
    },
    planThinkFinal(sessionId: string,taskId: string, isThinking: boolean) {
      console.log('planThinkFinal 开关',sessionId,taskId,isThinking)
      const sessionIndex = this.sessions.findIndex(session => session.sessionId === sessionId)
      if (sessionIndex !== -1) {
        const taskIndex = this.sessions[sessionIndex].tasks.findIndex(t => t.taskId === taskId)
        if (taskIndex !== -1) {
          console.log('planThinkFinal 开关',isThinking)
          this.sessions[sessionIndex].tasks[taskIndex].planThinking = isThinking
          this.sessions[sessionIndex].tasks[taskIndex].updatedAt = Date.now()
        }
      }
    },
    stepThinkFinal(sessionId: string,taskId: string,stepIndex: number, isThinking: boolean) {
      const sessionIndex = this.sessions.findIndex(session => session.sessionId === sessionId)
      if (sessionIndex !== -1) {
        const taskIndex = this.sessions[sessionIndex].tasks.findIndex(t => t.taskId === taskId)
        if (taskIndex !== -1) {
          if(stepIndex > 0){
            stepIndex -= 1
          }
          const step = this.sessions[sessionIndex].tasks[taskIndex].steps[stepIndex]
          if (step) {
            step.isThinking = isThinking
            step.updatedAt = Date.now()
          }
        }
      }
    }
    
  }
})
