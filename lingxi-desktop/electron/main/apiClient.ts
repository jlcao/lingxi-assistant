import axios, { AxiosError, AxiosInstance } from 'axios'
import type {
  ApiResponse,
  Checkpoint,
  Config,
  DiagnosticResult,
  ExecutionResult,
  ExecutionStatus,
  HistoryItem,
  ResourceUsage,
  Session,
  SessionDetail,
  Skill,
  SkillManifest,
  WorkspaceInfo,
  WorkspaceSwitchResult,
  WorkspaceInitResult,
  WorkspaceValidationResult
} from '../../src/types'

export class ApiClient {
  private client: AxiosInstance
  private baseUrl: string
  private maxRetries: number = 3
  private timeout: number = 30000

  constructor(baseUrl: string, timeout?: number) {
    this.baseUrl = baseUrl
    this.timeout = timeout || this.timeout

    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    this.client.interceptors.request.use(
      (config) => config,
      (error) => Promise.reject(error)
    )

    this.client.interceptors.response.use(
      (response) => response.data,
      async (error: AxiosError) => {
        if (!error.config) return Promise.reject(error)

        const retryCount = (error.config as any).__retryCount || 0

        if (retryCount < this.maxRetries && this.shouldRetry(error)) {
          (error.config as any).__retryCount = retryCount + 1
          await this.delay(Math.pow(2, retryCount) * 1000)
          return this.client.request(error.config)
        }

        return Promise.reject(error)
      }
    )
  }

  private shouldRetry(error: AxiosError): boolean {
    if (!error.response) return true
    const status = error.response.status
    return status >= 500 || status === 429
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  async getSessions(params?: {
    page?: number
    page_size?: number
    user_name?: string
    sort_by?: string
    order?: string
  }): Promise<{ sessions: Session[] }> {
    return this.client.get('/api/sessions', { params })
  }

  async getSession(sessionId: string): Promise<SessionDetail> {
    return this.client.get(`/api/sessions/${sessionId}`)
  }

  async getSessionHistory(sessionId: string, params?: {
    max_turns?: number
    include_steps?: boolean
    task_status?: string
  }): Promise<{ session_id: string; total_turns: number; history: HistoryItem[] }> {
    return this.client.get(`/api/sessions/${sessionId}/history`, { params })
  }

  async createSession(data: {
    user_name?: string
    title?: string
  }): Promise<{ session_id: string; first_message?: string }> {
    return this.client.post('/api/sessions', data)
  }

  async deleteSession(sessionId: string): Promise<ApiResponse<{ success: boolean; deleted_tasks_count: number; deleted_steps_count: number }>> {
    return this.client.delete(`/api/sessions/${sessionId}`)
  }

  async updateSessionName(sessionId: string, name: string): Promise<ApiResponse<{ success: boolean; message: string; updated_at: string }>> {
    return this.client.patch(`/api/sessions/${sessionId}`, { title: name })
  }

  async clearSessionHistory(sessionId: string): Promise<ApiResponse<{ success: boolean; deleted_turns_count: number }>> {
    return this.client.delete(`/api/sessions/${sessionId}/history`)
  }

  async executeTask(data: {
    task: string
    session_id: string
    model_override?: string | null
  }): Promise<ApiResponse<ExecutionResult>> {
    return this.client.post('/api/tasks/execute', data)
  }

  async getTaskStatus(taskId: string): Promise<ApiResponse<ExecutionStatus>> {
    return this.client.get(`/api/tasks/${taskId}/status`)
  }

  async retryTask(taskId: string, data?: {
    step_index?: number
    user_input?: string | null
  }): Promise<ApiResponse<{ success: boolean; message: string; execution_id: string; retry_from_step: number }>> {
    return this.client.post(`/api/tasks/${taskId}/retry`, data)
  }

  async cancelTask(taskId: string): Promise<ApiResponse<{ success: boolean; message: string; cancelled_at: number }>> {
    return this.client.post(`/api/tasks/${taskId}/cancel`)
  }

  async executeTaskStream(data: {
    task: string
    session_id: string
    model_override?: string | null
    enable_heartbeat?: boolean
    heartbeat_interval?: number
  }, options?: {
    timeout?: number
    maxRetries?: number
    retryDelay?: number
  }): Promise<Response> {
    const config: RequestInit = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    }

    if (options?.timeout) {
      config.signal = AbortSignal.timeout(options.timeout)
    }

    const response = await fetch(`${this.baseUrl}/api/tasks/stream`, config)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response
  }

  async getCheckpoints(params?: {
    status?: string
    page?: number
    page_size?: number
  }): Promise<ApiResponse<{ total: number; checkpoints: Checkpoint[] }>> {
    return this.client.get('/api/checkpoints', { params })
  }

  async resumeCheckpoint(taskId: string): Promise<ApiResponse<{ execution_id: string; task: string; status: string; message: string; resumed_from_step: number }>> {
    return this.client.post(`/api/checkpoints/${taskId}/resume`)
  }

  async deleteCheckpoint(taskId: string): Promise<ApiResponse<{ success: boolean; deleted_steps_count: number }>> {
    return this.client.delete(`/api/checkpoints/${taskId}`)
  }

  async getSkills(params?: {
    status?: string
    page?: number
    page_size?: number
    keyword?: string
  }): Promise<ApiResponse<{ total: number; skills: Skill[] }>> {
    return this.client.get('/api/skills', { params })
  }

  async installSkill(data: {
    skill_data: SkillManifest
    skill_files: Record<string, string>
    auto_fix?: boolean
  }): Promise<ApiResponse<{ skill_id: string; status: string; message: string; installed_at: string }>> {
    return this.client.post('/api/skills/install', data)
  }

  async diagnoseSkill(skillId: string): Promise<ApiResponse<DiagnosticResult>> {
    return this.client.get(`/api/skills/${skillId}/diagnose`)
  }

  async reloadSkill(skillId: string): Promise<ApiResponse<{ success: boolean; message: string; reloaded_at: string }>> {
    return this.client.post(`/api/skills/${skillId}/reload`)
  }

  async getResourceUsage(): Promise<ApiResponse<ResourceUsage>> {
    return this.client.get('/api/resources')
  }

  async getConfig(): Promise<ApiResponse<Config>> {
    return this.client.get('/api/config')
  }

  async updateConfig(config: Partial<Config>): Promise<ApiResponse<{ success: boolean; message: string; updated_at: string }>> {
    return this.client.patch('/api/config', config)
  }

  async getWorkspaceCurrent(): Promise<ApiResponse<WorkspaceInfo>> {
    return this.client.get('/api/workspace/current')
  }

  async switchWorkspace(workspacePath: string, force = false): Promise<ApiResponse<WorkspaceSwitchResult>> {
    return this.client.post('/api/workspace/switch', {
      workspace_path: workspacePath,
      force
    })
  }

  async initializeWorkspace(workspacePath?: string): Promise<ApiResponse<WorkspaceInitResult>> {
    const params = workspacePath ? { workspace_path: workspacePath } : {}
    return this.client.post('/api/workspace/initialize', params)
  }

  async validateWorkspace(workspacePath: string): Promise<ApiResponse<WorkspaceValidationResult>> {
    return this.client.get('/api/workspace/validate', {
      params: { workspace_path: workspacePath }
    })
  }

  async getWorkspaceSessions(workspacePath?: string): Promise<ApiResponse<{ success: boolean; sessions: Session[] }>> {
    const params = workspacePath ? { workspace_path: workspacePath } : {}
    return this.client.get('/api/workspace/sessions', { params })
  }
}
