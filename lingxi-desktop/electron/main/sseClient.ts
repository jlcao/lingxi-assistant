import { EventEmitter } from 'events'
import type { SSEEvent, UUID } from '../../src/types'

interface SSECallbacks {
  onTaskStart?: (data: {execution_id: UUID; task: string; task_level: string; model: string}) => void
  onPlanStart?: (data: {execution_id: UUID; task_id: UUID}) => void
  onThinkStart?: (data: {execution_id: UUID; task_id: UUID; step_id: UUID; content: string}) => void
  onThinkStream?: (data: {execution_id: UUID; task_id: UUID; step_id: UUID; content: string}) => void
  onThinkFinal?: (data: {execution_id: UUID; task_id: UUID; step_id: UUID; thought: string}) => void
  onPlanFinal?: (data: {execution_id: UUID; task_id: UUID; plan: any[]}) => void
  onStepStart?: (data: {execution_id: UUID; task_id: UUID; step_id: UUID; step_index: number; description: string}) => void
  onStepEnd?: (data: {execution_id: UUID; task_id: UUID; step_id: UUID; step_index: number; result: any; status: string}) => void
  onTaskEnd?: (data: {execution_id: UUID; task_id: UUID; result: any; status: string}) => void
  onTaskFailed?: (data: {execution_id: UUID; task_id: UUID; error: string; error_code: string; traceback?: string; recoverable?: boolean}) => void
  onTaskCancelled?: (data: {execution_id: UUID; task_id: UUID; cancelled_at: number; reason: string; current_step: number; completed_steps: number; can_resume: boolean}) => void
  onPing?: (data: {timestamp: number}) => void
  onStreamEnd?: () => void
  onError?: (error: Error) => void
  onReconnecting?: (attempt: number, maxRetries: number) => void
  onReconnectSuccess?: () => void
  onReconnectFailed?: () => void
}

interface SSEClientConfig {
  connectionTimeout: number
  heartbeatTimeout: number
  maxRetries: number
  retryDelay: number
  enableBuffer: boolean
  bufferSize: number
  flushInterval: number
}

export class SSEClient extends EventEmitter {
  private controller: AbortController | null = null
  private reader: ReadableStreamDefaultReader | null = null
  private connectionTimeoutTimer: NodeJS.Timeout | null = null
  private heartbeatTimeoutTimer: NodeJS.Timeout | null = null
  private lastHeartbeatTime: number | null = null
  private retryCount = 0
  private isReconnecting = false
  private eventBuffer: SSEEvent[] = []
  private flushTimer: NodeJS.Timeout | null = null
  private callbacks: SSECallbacks = {}
  private currentTaskData: {
    task: string
    session_id: string
    model_override?: string | null
    enable_heartbeat?: boolean
    heartbeat_interval?: number
  } | null = null

  private config: SSEClientConfig = {
    connectionTimeout: 30000,
    heartbeatTimeout: 90000,
    maxRetries: 3,
    retryDelay: 1000,
    enableBuffer: true,
    bufferSize: 100,
    flushInterval: 100
  }

  private baseUrl: string

  constructor(baseUrl: string) {
    super()
    this.baseUrl = baseUrl
  }

  async executeTaskStream(
    data: {
      task: string
      session_id: string
      model_override?: string | null
      enable_heartbeat?: boolean
      heartbeat_interval?: number
    },
    callbacks: SSECallbacks,
    options?: Partial<SSEClientConfig>
  ): Promise<void> {
    this.config = { ...this.config, ...options }
    this.callbacks = callbacks
    this.currentTaskData = data

    if (this.config.enableBuffer) {
      this.startFlushTimer()
    }

    await this.connect(data)
  }

  private async connect(data: {
    task: string
    session_id: string
    model_override?: string | null
    enable_heartbeat?: boolean
    heartbeat_interval?: number
  }): Promise<void> {
    this.controller = new AbortController()

    this.startConnectionTimeout(this.config.connectionTimeout)

    try {
      const response = await fetch(`${this.baseUrl}/api/tasks/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data),
        signal: this.controller.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      if (this.connectionTimeoutTimer) {
        clearTimeout(this.connectionTimeoutTimer)
        this.connectionTimeoutTimer = null
      }

      this.reader = response.body!.getReader()

      this.startHeartbeatTimeout(this.config.heartbeatTimeout)

      await this.readStream()

    } catch (error) {
      this.handleError(error as Error)
    }
  }

  private async readStream(): Promise<void> {
    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await this.reader!.read()
        if (done) break

        const chunk = decoder.decode(value)
        const events = this.parseSSEEvents(chunk)

        events.forEach(event => {
          this.handleEvent(event)
        })
      }
    } catch (error) {
      this.handleError(error as Error)
    }
  }

  private parseSSEEvents(chunk: string): SSEEvent[] {
    const events: SSEEvent[] = []
    const lines = chunk.split('\n')
    let currentEvent: any = null
    let currentData = ''

    for (const line of lines) {
      const trimmedLine = line.trim()

      if (trimmedLine === '') {
        if (currentEvent && currentData) {
          try {
            currentEvent.data = JSON.parse(currentData)
            events.push(currentEvent)
          } catch (e) {
            console.error('[SSEClient] Failed to parse event data:', currentData)
          }
          currentEvent = null
          currentData = ''
        }
        continue
      }

      if (trimmedLine.startsWith('event:')) {
        currentEvent = {
          event_type: trimmedLine.substring(6).trim()
        }
      } else if (trimmedLine.startsWith('data:')) {
        const dataContent = trimmedLine.substring(5).trim()
        if (currentData) {
          currentData += '\n' + dataContent
        } else {
          currentData = dataContent
        }
      } else if (trimmedLine.startsWith(':')) {
        continue
      }
    }

    return events
  }

  private handleEvent(event: SSEEvent): void {
    if (event.event_type === 'ping') {
      this.lastHeartbeatTime = Date.now()
      this.resetHeartbeatTimeout(this.config.heartbeatTimeout)
      this.callbacks.onPing?.(event.data as any)
      return
    }

    if (event.event_type === 'stream_end') {
      this.cleanup()
      this.callbacks.onStreamEnd?.()
      return
    }

    if (event.event_type === 'task_cancelled') {
      this.callbacks.onTaskCancelled?.(event.data as any)
      return
    }

    if (this.config.enableBuffer) {
      this.addToBuffer(event)
    } else {
      this.dispatchImmediate(event)
    }
  }

  private startConnectionTimeout(timeout: number): void {
    this.connectionTimeoutTimer = setTimeout(() => {
      this.handleConnectionTimeout()
    }, timeout)
  }

  private startHeartbeatTimeout(timeout: number): void {
    this.heartbeatTimeoutTimer = setTimeout(() => {
      this.handleHeartbeatTimeout()
    }, timeout)
  }

  private resetHeartbeatTimeout(timeout: number): void {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer)
    }
    this.startHeartbeatTimeout(timeout)
  }

  private handleConnectionTimeout(): void {
    console.warn('[SSEClient] SSE连接超时')
    this.reconnect()
  }

  private handleHeartbeatTimeout(): void {
    console.warn('[SSEClient] SSE心跳超时')
    this.reconnect()
  }

  private async reconnect(): Promise<void> {
    if (this.retryCount >= this.config.maxRetries) {
      console.error('[SSEClient] 达到最大重试次数，放弃重连')
      this.callbacks.onReconnectFailed?.()
      return
    }

    if (this.isReconnecting) {
      return
    }

    this.isReconnecting = true
    this.retryCount++

    const delay = this.config.retryDelay * Math.pow(2, this.retryCount - 1)
    console.info(`[SSEClient] 第${this.retryCount}次重连，延迟${delay}ms`)
    this.callbacks.onReconnecting?.(this.retryCount, this.config.maxRetries)

    await new Promise(resolve => setTimeout(resolve, delay))

    try {
      if (!this.currentTaskData) {
        throw new Error('没有保存的任务数据，无法重连')
      }
      await this.connect(this.currentTaskData)
      this.retryCount = 0
      this.isReconnecting = false
      this.callbacks.onReconnectSuccess?.()
      console.info('[SSEClient] 重连成功')
    } catch (error) {
      console.error('[SSEClient] 重连失败:', error)
      this.isReconnecting = false
      this.reconnect()
    }
  }

  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flushBuffer()
    }, this.config.flushInterval)
  }

  private stopFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
      this.flushTimer = null
    }
  }

  private addToBuffer(event: SSEEvent): void {
    if (this.isPriorityEvent(event)) {
      this.flushBuffer()
      this.dispatchImmediate(event)
      return
    }

    this.eventBuffer.push(event)

    if (this.eventBuffer.length >= this.config.bufferSize) {
      this.flushBuffer()
    }
  }

  private flushBuffer(): void {
    if (this.eventBuffer.length === 0) {
      return
    }

    const events = [...this.eventBuffer]
    this.eventBuffer = []

    events.forEach(event => {
      this.dispatchImmediate(event)
    })
  }

  private isPriorityEvent(event: SSEEvent): boolean {
    const priorityEvents = ['task_start', 'task_end', 'task_failed', 'task_cancelled', 'step_start', 'step_end']
    return priorityEvents.includes(event.event_type)
  }

  private dispatchImmediate(event: SSEEvent): void {
    switch (event.event_type) {
      case 'task_start':
        this.callbacks.onTaskStart?.(event.data as any)
        break
      case 'plan_start':
        this.callbacks.onPlanStart?.(event.data as any)
        break
      case 'think_start':
        this.callbacks.onThinkStart?.(event.data as any)
        break
      case 'think_stream':
        this.callbacks.onThinkStream?.(event.data as any)
        break
      case 'think_final':
        this.callbacks.onThinkFinal?.(event.data as any)
        break
      case 'plan_final':
        this.callbacks.onPlanFinal?.(event.data as any)
        break
      case 'step_start':
        this.callbacks.onStepStart?.(event.data as any)
        break
      case 'step_end':
        this.callbacks.onStepEnd?.(event.data as any)
        break
      case 'task_end':
        this.callbacks.onTaskEnd?.(event.data as any)
        break
      case 'task_failed':
        this.callbacks.onTaskFailed?.(event.data as any)
        break
      default:
        console.warn('[SSEClient] Unknown event type:', event.event_type)
    }
  }

  private handleError(error: Error): void {
    console.error('[SSEClient] SSE错误:', error)

    if (error.name === 'AbortError') {
      this.callbacks.onError?.(new Error('请求已被客户端取消'))
      return
    }

    this.reconnect()
  }

  private cleanup(): void {
    this.stopFlushTimer()
    this.flushBuffer()

    if (this.connectionTimeoutTimer) {
      clearTimeout(this.connectionTimeoutTimer)
      this.connectionTimeoutTimer = null
    }
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer)
      this.heartbeatTimeoutTimer = null
    }
    if (this.reader) {
      this.reader.cancel()
      this.reader = null
    }
    if (this.controller) {
      this.controller.abort()
      this.controller = null
    }
  }

  abort(): void {
    this.cleanup()
  }

  getConnectionStatus(): {
    connected: boolean
    lastHeartbeat: number | null
    retryCount: number
    bufferedEvents: number
  } {
    return {
      connected: this.reader !== null,
      lastHeartbeat: this.lastHeartbeatTime,
      retryCount: this.retryCount,
      bufferedEvents: this.eventBuffer.length
    }
  }

  async reconnectManual(): Promise<void> {
    this.cleanup()
    this.retryCount = 0
    this.isReconnecting = false
    await this.reconnect()
  }
}
