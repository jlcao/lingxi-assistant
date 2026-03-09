import EventEmitter from 'events'
import WebSocket from 'ws'
import type {
  ThoughtChainData,
  StepStatusData,
  SkillCallData,
  ModelRouteData,
  WorkspaceFilesChangedEvent
} from '../../src/types'

export class WsClient extends EventEmitter {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 10
  private reconnectInterval: number = 1000
  private maxReconnectInterval: number = 30000
  private heartbeatInterval: number = 30000
  private heartbeatTimer: NodeJS.Timeout | null = null
  private isManualClose: boolean = false
  private lastSessionId: string | undefined // 新增：保存sessionId用于重连

  constructor(url: string) {
    super()
    this.url = url
    // 全局错误监听，方便调试
    this.on('error', (err) => {
      console.error('[WsClient] 错误:', err)
    })
  }

  connect(sessionId?: string): void {
    // 保存最新的sessionId
    this.lastSessionId = sessionId
    this.isManualClose = false
    const wsUrl = sessionId ? `${this.url}?sessionId=${sessionId}` : this.url

    console.log(`[WsClient] 尝试连接WS服务端: ${wsUrl}`)

    // 修复：连接前清理旧连接，避免冲突
    if (this.ws) {
      this.ws.removeAllListeners()
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

    this.ws.on('open', () => {
      console.log('[WsClient] WS连接成功 ✅')
      this.reconnectAttempts = 0
      this.emit('connected')
      this.startHeartbeat()
    })

    this.ws.on('message', (data) => {
      try {
        const message = data.toString()
        const parsed = JSON.parse(message)
        this.handleMessage(parsed)
      } catch (error) {
        this.emit('error', new Error(`消息解析失败: ${(error as Error).message}`))
      }
    })

    // 修复：精准捕获ECONNREFUSED错误并给出明确提示
    this.ws.on('error', (error) => {
      const errMsg = (error as Error).message
      if (errMsg.includes('ECONNREFUSED')) {
        const tip = `[WsClient] 连接被拒绝 ❌，请检查: 1. WS服务端是否启动 2. 5000端口是否被占用 3. 服务端地址是否正确(${this.url})`
        this.emit('error', new Error(tip))
        console.error(tip)
      } else {
        this.emit('error', new Error(`WS连接错误: ${errMsg}`))
      }
    })

    this.ws.on('close', () => {
      this.stopHeartbeat()
      console.log('[WsClient] WS连接关闭 ❌')
      this.emit('disconnected')

      if (!this.isManualClose) {
        this.scheduleReconnect()
      }
    })
  }

  private handleMessage(data: any): void {
    if (!data) {
      console.warn('[WsClient] 收到空消息，忽略')
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
      case 'workspace_files_changed':
        this.emit('workspace_files_changed', payload as WorkspaceFilesChangedEvent)
        break
      default:
        this.emit('unknown', data)
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'heartbeat' })
    }, this.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
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

    // 修复：重连时携带上次的sessionId
    setTimeout(() => {
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
    this.reconnectAttempts = 0 // 重置重连次数
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  onThoughtChain(callback: (data: ThoughtChainData) => void): void {
    this.on('thought_chain', callback)
  }

  onStepStatus(callback: (data: StepStatusData) => void): void {
    this.on('step_status', callback)
  }

  onSkillCall(callback: (data: SkillCallData) => void): void {
    this.on('skill_call', callback)
  }

  onResourceUpdate(callback: (data: any) => void): void {
    this.on('resource_update', callback)
  }

  onModelRoute(callback: (data: ModelRouteData) => void): void {
    this.on('model_route', callback)
  }

  onTaskStart(callback: (data: any) => void): void {
    this.on('task_start', callback)
  }

  onTaskEnd(callback: (data: any) => void): void {
    this.on('task_end', callback)
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

  onStepEnd(callback: (data: any) => void): void {
    this.on('step_end', callback)
  }

  onTaskFailed(callback: (data: any) => void): void {
    this.on('task_failed', callback)
  }

  onWorkspaceFilesChanged(callback: (data: WorkspaceFilesChangedEvent) => void): void {
    this.on('workspace_files_changed', callback)
  }

  off(eventType: string, callback: (...args: any[]) => void): this {
    this.removeListener(eventType, callback)
    return this
  }
}