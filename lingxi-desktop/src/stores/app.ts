import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session, Turn, Step, Checkpoint } from '@/types'

export const useAppStore = defineStore('app', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const turns = ref<Turn[]>([])
  const activeCheckpoints = ref<Checkpoint[]>([])
  const loading = ref(false)

  const currentSession = computed(() => {
    return sessions.value.find(session => session.sessionId === currentSessionId.value) || null
  })

  function setSessions(newSessions: Session[]) {
    sessions.value = newSessions
  }

  function setCurrentSession(sessionId: string | null) {
    currentSessionId.value = sessionId
  }

  function setTurns(newTurns: Turn[]) {
    turns.value = newTurns
  }

  function addTurn(turn: Turn) {
    turns.value.push(turn)
  }

  function setActiveCheckpoints(checkpoints: Checkpoint[]) {
    activeCheckpoints.value = checkpoints
  }

  function setLoading(isLoading: boolean) {
    loading.value = isLoading
  }

  function setCurrentTask(sessionId: string, taskId: string | null) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session) {
      session.currentTaskId = taskId
    }
  }

  function updateTaskStatus(sessionId: string, taskId: string, status: string) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && session.tasks) {
      const task = session.tasks.find(t => t.taskId === taskId)
      if (task) {
        task.status = status
        task.planThinking = false
      }
    }
  }

  function addTask(sessionId: string, taskId: string, taskData: any) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session) {
      if (!session.tasks) {
        session.tasks = []
      }
      const existingTaskIndex = session.tasks.findIndex(t => t.taskId === taskId)
      if (existingTaskIndex >= 0) {
        session.tasks[existingTaskIndex] = { ...session.tasks[existingTaskIndex], ...taskData }
      } else {
        session.tasks.push({ taskId, ...taskData })
      }
    }
  }

  function addStep(sessionId: string, taskId: string, stepIndex: number, stepInfo: Step) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && session.tasks) {
      const task = session.tasks.find(t => t.taskId === taskId)
      if (task) {
        if (!task.steps) {
          task.steps = []
        }
        debugger
        task.steps[stepIndex] = stepInfo
      }
    }
  }

  function addThought(sessionId: string, taskId: string, stepIndex: number, content: string) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && session.tasks) {
      const task = session.tasks.find(t => t.taskId === taskId)
      if (task && task.steps && task.steps[stepIndex]) {
        task.steps[stepIndex].thought = task.steps[stepIndex].thought + content
      }
    }
  }

  function addThinkThought(sessionId: string, taskId: string, content: string) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && session.tasks) {
      const task = session.tasks.find(t => t.taskId === taskId)
      if (task) {
        task.planThinkingContent = task.planThinkingContent + content
      }
    }
  }

  function stepThinkFinal(sessionId: string, taskId: string, stepIndex: number, isThinking: boolean) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && session.tasks) {
      const task = session.tasks.find(t => t.taskId === taskId)
      if (task && task.steps && task.steps[stepIndex]) {
        task.steps[stepIndex].isThinking = isThinking
      }
    }
  }

  function planThinkFinal(sessionId: string, taskId: string, isThinking: boolean) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && session.tasks) {
      const task = session.tasks.find(t => t.taskId === taskId)
      if (task) {
        task.planThinking = isThinking
      }
    }
  }

  function updateSessionTitle(sessionId: string, title: string) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session) {
      session.title = title
    }
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    turns,
    activeCheckpoints,
    loading,
    setSessions,
    setCurrentSession,
    setTurns,
    addTurn,
    setActiveCheckpoints,
    setLoading,
    setCurrentTask,
    updateTaskStatus,
    addTask,
    addStep,
    addThought,
    addThinkThought,
    stepThinkFinal,
    planThinkFinal,
    updateSessionTitle
  }
})
