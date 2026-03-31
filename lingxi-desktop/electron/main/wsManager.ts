import { dialog } from 'electron'
import { WsClient } from './wsClient'
import { logger } from './logger'

export class WsManager {
  private wsClient: WsClient | null = null
  private isWsInitialized: boolean = false
  private backendPort: number
  private onMessageCallback?: (channel: string, data: any) => void

  constructor(backendPort: number) {
    this.backendPort = backendPort
  }

  initWsClient(onMessageCallback?: (channel: string, data: any) => void): void {
    if (this.isWsInitialized || this.wsClient) {
      logger.log('[WsManager] WS客户端已初始化，跳过重复初始化')
      return
    }

    this.onMessageCallback = onMessageCallback
    this.isWsInitialized = true
    this.wsClient = new WsClient(`ws://127.0.0.1:${this.backendPort}/ws`)

    this.setupEventListeners()
  }

  private setupEventListeners(): void {
    if (!this.wsClient) return

    this.wsClient.on('error', (err: Error) => {
      // 连接被拒绝的友好提示
      if (err.message.includes('ECONNREFUSED')) {
        dialog.showErrorBox(
          'WebSocket连接失败',
          '无法连接到本地5000端口的WS服务端，请确认：\n1. 后端服务已启动\n2. 5000端口未被其他程序占用\n3. 服务端WS地址配置正确（当前：ws://127.0.0.1:5000/ws）'
        )
      } else {
        // 其他错误的通用提示
        dialog.showErrorBox('WebSocket错误', `连接异常：${err.message}`)
      }
      // 转发错误到渲染进程，前端可自定义展示
      this.onMessageCallback?.('ws:error', err.message)
    })

    // 监听重连失败事件，提示用户
    this.wsClient.on('reconnect_failed', () => {
      dialog.showErrorBox(
        'WS重连失败',
        '已尝试10次重连仍无法连接到服务端，请检查服务端状态后手动重新连接'
      )
      this.onMessageCallback?.('ws:reconnect-failed')
    })

    // 原有WS事件转发逻辑
    this.wsClient.on('connected', () => {
      this.onMessageCallback?.('ws:connected')
    })

    this.wsClient.on('disconnected', () => {
      this.onMessageCallback?.('ws:disconnected')
    })

    this.wsClient.on('thought_chain', (data) => {
      this.onMessageCallback?.('ws:thought-chain', data)
    })

    this.wsClient.on('task_start', (data) => {
      this.onMessageCallback?.('ws:task-start', data)
    })

    this.wsClient.on('task_end', (data) => {
      this.onMessageCallback?.('ws:task-end', data)
    })

    this.wsClient.on('think_start', (data) => {
      this.onMessageCallback?.('ws:think-start', data)
    })

    this.wsClient.on('think_stream', (data) => {
      this.onMessageCallback?.('ws:think-stream', data)
    })

    this.wsClient.on('think_final', (data) => {
      this.onMessageCallback?.('ws:think-final', data)
    })

    this.wsClient.on('plan_start', (data) => {
      this.onMessageCallback?.('ws:plan-start', data)
    })

    this.wsClient.on('plan_final', (data) => {
      this.onMessageCallback?.('ws:plan-final', data)
    })

    this.wsClient.on('step_start', (data) => {
      this.onMessageCallback?.('ws:step-start', data)
    })

    this.wsClient.on('step_end', (data) => {
      this.onMessageCallback?.('ws:step-end', data)
    })

    this.wsClient.on('task_failed', (data) => {
      this.onMessageCallback?.('ws:task-failed', data)
    })

    this.wsClient.on('task_stopped', (data) => {
      this.onMessageCallback?.('ws:task-stopped', data)
    })

    this.wsClient.on('workspace_files_changed', (data) => {
      this.onMessageCallback?.('ws:workspace-files-changed', data)
    })
  }

  connect(sessionId: string): void {
    if (!this.wsClient && !this.isWsInitialized) {
      this.initWsClient()
    }
    this.wsClient?.connect(sessionId)
  }

  disconnect(): void {
    this.wsClient?.disconnect()
  }

  isConnected(): boolean {
    return this.wsClient?.isConnected() || false
  }

  send(message: any): void {
    this.wsClient?.send(message)
  }

  cleanup(): void {
    if (this.wsClient) {
      logger.log('[WsManager] 断开 WebSocket 连接')
      this.wsClient.disconnect()
      this.wsClient = null
      this.isWsInitialized = false
    }
  }

  isInitialized(): boolean {
    return this.isWsInitialized
  }
}
