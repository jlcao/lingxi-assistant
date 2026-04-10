import type {
  ThoughtChainData,
  StepStatusData,
  SkillCallData,
  ModelRouteData,
  WorkspaceFilesChangedEvent
} from '../types'

// 实现一个简单的EventEmitter，兼容浏览器环境
class EventEmitter {
  private events: Map<string, Array<(...args: any[]) => void>> = new Map()

  on(event: string, listener: (...args: any[]) => void): this {
    if (!this.events.has(event)) {
      this.events.set(event, [])
    }
    this.events.get(event)?.push(listener)
    return this
  }

  emit(event: string, ...args: any[]): boolean {
    const listeners = this.events.get(event)
    if (listeners) {
      listeners.forEach(listener => listener(...args))
      return true
    }
    return false
  }

  removeAllListeners(event?: string): this {
    if (event) {
      this.events.delete(event)
    } else {
      this.events.clear()
    }
    return this
  }
}

export class WsClient extends EventEmitter {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 10
  private reconnectInterval: number = 1000
  private maxReconnectInterval: number = 30000
  private heartbeatInterval: number = 30000
  private heartbeatTimer: number | null = null
  private isManualClose: boolean = false
  private lastSessionId: string | undefined

  constructor(url: string) {
    super()
    this.url = url
    this.on('error', (err) => {
      console.error('[WsClient] 错误:', err)
    })
  }

  connect(sessionId?: string): void {
    this.lastSessionId = sessionId
    this.isManualClose = false
    const wsUrl = sessionId ? `${this.url}?sessionId=${sessionId}` : this.url

    console.log(`[WsClient] 尝试连接WS服务端: ${wsUrl}`)

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    try {
      this.ws = new WebSocket(wsUrl)
      this.setupEventHandlers()
    } catch (error) {
      this.emit('error', new Error(`初始化WS连接失败: ${(error as Error).message}`))
      this.scheduleReconnect()
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      console.log('[WsClient] WS连接成功 ✅')
      this.reconnectAttempts = 0
      this.emit('connected')
      this.startHeartbeat()
    }

    this.ws.onmessage = (event) => {
      try {
        const message = event.data
        const parsed = JSON.parse(message)
        this.handleMessage(parsed)
      } catch (error) {
        this.emit('error', new Error(`消息解析失败: ${(error as Error).message}`))
      }
    }

    this.ws.onerror = (error) => {
      const errMsg = error instanceof Error ? error.message : '未知错误'
      if (errMsg.includes('ECONNREFUSED')) {
        const tip = `[WsClient] 连接被拒绝 ❌，请检查: 1. WS服务端是否启动 2. 5000端口是否被占用 3. 服务端地址是否正确(${this.url})`
        this.emit('error', new Error(tip))
        console.error(tip)
      } else {
        this.emit('error', new Error(`WS连接错误: ${errMsg}`))
      }
    }

    this.ws.onclose = () => {
      this.stopHeartbeat()
      console.log('[WsClient] WS连接关闭 ❌')
      this.emit('disconnected')

      if (!this.isManualClose) {
        this.scheduleReconnect()
      }
    }
  }

  private handleMessage(data: any): void {
    if (!data) {
      console.error('[WsClient] 收到空消息，忽略')
      return
    }
    
    const { type, payload } = data

    switch (type) {
      case 'thought_chain':
        this.emit('thought_chain', payload as ThoughtChainData)
        break
      case 'heartbeat':
        break
      case 'step_start':
        this.emit('step_start', payload || data)
        break
      case 'step_end':
        this.emit('step_end', payload || data)
        break
      case 'task_start':
        this.emit('task_start', payload || data)
        break
      case 'task_end':
        this.emit('task_end', payload || data)
        break
      case 'think_start':
        this.emit('think_start', payload || data)
        break
      case 'think_stream':
        this.emit('think_stream', payload || data)
        break
      case 'think_final':
        this.emit('think_final', payload || data)
        break
      case 'plan_start':
        this.emit('plan_start', payload || data)
        break
      case 'plan_final':
        this.emit('plan_final', payload || data)
        break
      case 'task_failed':
        this.emit('task_failed', payload || data)
        break
      case 'task_stopped':
        this.emit('task_stopped', payload || data)
        break
      case 'workspace_files_changed':
        this.emit('workspace_files_changed', payload as WorkspaceFilesChangedEvent)
        break
      default:
        this.emit('unknown', data)
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      this.send({ type: 'ping' })
    }, this.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      window.clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit('reconnect_failed', '达到最大重连次数，停止重连')
      console.error(`[WsClient] 重连失败：已尝试${this.reconnectAttempts}次，超过上限`)
      return
    }

    const interval = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectInterval
    )

    this.reconnectAttempts++
    this.emit('reconnecting', this.reconnectAttempts, interval)
    console.log(`[WsClient] 准备重连：第${this.reconnectAttempts}次，间隔${interval/1000}s`)

    window.setTimeout(() => {
      this.connect(this.lastSessionId)
    }, interval)
  }

  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  disconnect(): void {
    this.isManualClose = true
    this.stopHeartbeat()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.reconnectAttempts = 0
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  onConnected(callback: () => void): void {
    this.on('connected', callback)
  }

  onDisconnected(callback: () => void): void {
    this.on('disconnected', callback)
  }

  onError(callback: (error: Error) => void): void {
    this.on('error', callback)
  }

  onThoughtChain(callback: (data: ThoughtChainData) => void): void {
    this.on('thought_chain', callback)
  }

  onStepStart(callback: (data: any) => void): void {
    this.on('step_start', callback)
  }

  onStepEnd(callback: (data: any) => void): void {
    this.on('step_end', callback)
  }

  onTaskStart(callback: (data: any) => void): void {
    this.on('task_start', callback)
  }

  onTaskEnd(callback: (data: any) => void): void {
    this.on('task_end', callback)
  }

  onTaskStopped(callback: (data: any) => void): void {
    this.on('task_stopped', callback)
  }

  onTaskFailed(callback: (data: any) => void): void {
    this.on('task_failed', callback)
  }

  onThinkStart(callback: (data: any) => void): void {
    this.on('think_start', callback)
  }

  onThinkStream(callback: (data: any) => void): void {
    this.on('think_stream', callback)
  }

  onThinkFinal(callback: (data: any) => void): void {
    this.on('think_final', callback)
  }

  onPlanStart(callback: (data: any) => void): void {
    this.on('plan_start', callback)
  }

  onPlanFinal(callback: (data: any) => void): void {
    this.on('plan_final', callback)
  }

  onWorkspaceFilesChanged(callback: (data: WorkspaceFilesChangedEvent) => void): void {
    this.on('workspace_files_changed', callback)
  }

  removeAllListeners(eventType?: string): void {
    if (eventType) {
      super.removeAllListeners(eventType)
    } else {
      super.removeAllListeners()
    }
  }
}
