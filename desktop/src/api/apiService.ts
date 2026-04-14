import { ApiClient } from './apiClient'

class ApiService {
  private static instance: ApiService
  public client: ApiClient

  private constructor() {
    // 使用默认端口初始化，后续可以通过init方法更新
    this.client = new ApiClient('http://127.0.0.1:5000')
  }

  public static getInstance(): ApiService {
    if (!ApiService.instance) {
      ApiService.instance = new ApiService()
    }
    return ApiService.instance
  }

  public async init(): Promise<void> {
    // 从主进程获取后端端口
    if (window.electronAPI?.system?.getBackendPort) {
      try {
        const backendPort = await window.electronAPI.system.getBackendPort()
        this.client = new ApiClient(`http://127.0.0.1:${backendPort}`)
        console.log(`API服务初始化完成，使用端口: ${backendPort}`)
      } catch (error) {
        console.error('获取后端端口失败:', error)
      }
    }
  }
}

export const apiService = ApiService.getInstance()
