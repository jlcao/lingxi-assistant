import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TaskStartData, TaskEndData, TaskFailedData, StepStartData, StepEndData, ThinkStartData, ThinkStreamData, ThinkFinalData, PlanStartData, PlanFinalData, WorkspaceFilesChangedEvent } from '@/types'

type Listener = (...args: any[]) => void

export const useWsStore = defineStore('ws', () => {
  const ws = ref<WebSocket | null>(null)
  const listeners = ref<Map<string, Listener[]>>(new Map())

  function connect(sessionId: string) {
    // 断开之前的连接
    if (ws.value) {
      ws.value.close()
    }

    // 建立新连接
    const wsUrl = `ws://127.0.0.1:5000/ws?sessionId=${sessionId}`
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const { type, payload } = data
        
        // 触发对应的监听器
        if (listeners.value.has(type)) {
          const typeListeners = listeners.value.get(type)!
          typeListeners.forEach(listener => {
            listener(payload)
          })
        }
      } catch (error) {
        console.error('WebSocket message parse error:', error)
      }
    }

    ws.value.onclose = () => {
      console.log('WebSocket disconnected')
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  function on(event: string, listener: Listener) {
    if (!listeners.value.has(event)) {
      listeners.value.set(event, [])
    }
    listeners.value.get(event)!.push(listener)
  }

  function off(event: string, listener: Listener) {
    if (listeners.value.has(event)) {
      const typeListeners = listeners.value.get(event)!
      const index = typeListeners.indexOf(listener)
      if (index !== -1) {
        typeListeners.splice(index, 1)
      }
    }
  }

  function removeAllListeners() {
    listeners.value.clear()
  }

  // 事件监听器方法
  function onTaskStart(listener: (data: TaskStartData) => void) {
    on('task_start', listener)
  }

  function onTaskEnd(listener: (data: TaskEndData) => void) {
    on('task_end', listener)
  }

  function onTaskFailed(listener: (data: TaskFailedData) => void) {
    on('task_failed', listener)
  }

  function onStepStart(listener: (data: StepStartData) => void) {
    on('step_start', listener)
  }

  function onStepEnd(listener: (data: StepEndData) => void) {
    on('step_end', listener)
  }

  function onThinkStart(listener: (data: ThinkStartData) => void) {
    on('think_start', listener)
  }

  function onThinkStream(listener: (data: ThinkStreamData) => void) {
    on('think_stream', listener)
  }

  function onThinkFinal(listener: (data: ThinkFinalData) => void) {
    on('think_final', listener)
  }

  function onPlanStart(listener: (data: PlanStartData) => void) {
    on('plan_start', listener)
  }

  function onPlanFinal(listener: (data: PlanFinalData) => void) {
    on('plan_final', listener)
  }

  function onWorkspaceFilesChanged(listener: (data: WorkspaceFilesChangedEvent) => void) {
    on('workspace_files_changed', listener)
  }

  function onTaskStopped(listener: (data: any) => void) {
    on('task_stopped', listener)
  }

  function sendMessage(message: string, sessionId: string) {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connect(sessionId)
    }

    setTimeout(() => {
      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({
          type: 'stream_chat',
          content: message,
          sessionId: sessionId,
          thinkingMode: false
        }))
      }
    }, 100)
  }

  return {
    ws,
    connect,
    disconnect,
    on,
    off,
    removeAllListeners,
    onTaskStart,
    onTaskEnd,
    onTaskFailed,
    onStepStart,
    onStepEnd,
    onThinkStart,
    onThinkStream,
    onThinkFinal,
    onPlanStart,
    onPlanFinal,
    onWorkspaceFilesChanged,
    onTaskStopped,
    sendMessage
  }
})
