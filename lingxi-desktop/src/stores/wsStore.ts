import { defineStore } from 'pinia'
import { WsClient } from '../utils/wsClient'

export const useWsStore = defineStore('ws', {
  state: () => ({
    wsClient: null as WsClient | null,
    isConnected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 10
  }),

  getters: {
    client: (state) => state.wsClient
  },

  actions: {
    initWsClient() {
      if (!this.wsClient) {
        const wsUrl = 'ws://127.0.0.1:5000/ws'
        this.wsClient = new WsClient(wsUrl)
        this.setupEventListeners()
      }
      return this.wsClient
    },

    setupEventListeners() {
      if (!this.wsClient) return

      this.wsClient.onConnected(() => {
        this.isConnected = true
        this.reconnectAttempts = 0
      })

      this.wsClient.onDisconnected(() => {
        this.isConnected = false
      })

      this.wsClient.onError((error) => {
        console.error('[WS Store] WebSocket error:', error)
      })
    },

    connect(sessionId?: string) {
      const client = this.initWsClient()
      client.connect(sessionId)
    },

    disconnect() {
      if (this.wsClient) {
        this.wsClient.disconnect()
      }
    },

    sendMessage(message: string, sessionId?: string) {
      if (this.wsClient) {
        this.wsClient.send({
          type: 'stream_chat',
          content: message,
          sessionId: sessionId || 'default'
        })
      }
    },

    stopTask(taskId: string) {
      if (this.wsClient) {
        this.wsClient.send({
          type: 'stop_task',
          taskId: taskId
        })
      }
    },

    onConnected(callback: () => void) {
      const client = this.initWsClient()
      client.onConnected(callback)
    },

    onDisconnected(callback: () => void) {
      const client = this.initWsClient()
      client.onDisconnected(callback)
    },

    onError(callback: (error: Error) => void) {
      const client = this.initWsClient()
      client.onError(callback)
    },

    onTaskStart(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onTaskStart(callback)
    },

    onTaskEnd(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onTaskEnd(callback)
    },

    onTaskStopped(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onTaskStopped(callback)
    },

    onTaskFailed(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onTaskFailed(callback)
    },

    onThinkStart(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onThinkStart(callback)
    },

    onThinkStream(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onThinkStream(callback)
    },

    onThinkFinal(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onThinkFinal(callback)
    },

    onPlanStart(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onPlanStart(callback)
    },

    onPlanFinal(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onPlanFinal(callback)
    },

    onStepStart(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onStepStart(callback)
    },

    onStepEnd(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onStepEnd(callback)
    },

    onWorkspaceFilesChanged(callback: (data: any) => void) {
      const client = this.initWsClient()
      client.onWorkspaceFilesChanged(callback)
    },

    removeAllListeners(eventType?: string) {
      if (this.wsClient) {
        this.wsClient.removeAllListeners(eventType)
      }
    },

    cleanup() {
      if (this.wsClient) {
        this.wsClient.disconnect()
        this.wsClient = null
        this.isConnected = false
        this.reconnectAttempts = 0
      }
    }
  }
})
