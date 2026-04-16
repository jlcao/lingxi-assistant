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
  WorkspaceInitResult,
  WorkspaceSwitchResult,
  WorkspaceValidationResult,
  Thread,
  ThreadState,
  RunHistory,
  RunInput,
  Model,
  ModelDetail,
  MCPConfig,
  SkillDetail,
  FileUploadResponse,
  FileListResponse,
  SuccessResponse
} from '../types'

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
    workspace_path?: string
  }): Promise<ApiResponse<{ sessions: Session[] }>> {
    return this.client.get('/api/sessions', { params })
  }

  async searchThreads(params?: {
    metadata?: Record<string, any>
    limit?: number
    offset?: number
    status?: string
  }): Promise<Thread[]> {
    return this.client.post('/api/threads/search', params || {})
  }

  async getSession(sessionId: string): Promise<ApiResponse<SessionDetail>> {
    return this.client.get(`/api/sessions/${sessionId}`)
  }

  async getSessionHistory(sessionId: string, params?: {
    max_turns?: number
    include_steps?: boolean
    task_status?: string
  }): Promise<ApiResponse<{ session_id: string; total_turns: number; history: HistoryItem[] }>> {
    return this.client.get(`/api/sessions/${sessionId}/history`, { params })
  }

  async createSession(data: {
    user_name?: string
    title?: string
  } = {}): Promise<ApiResponse<{ session_id: string; first_message?: string }>> {
    return this.client.post('/api/sessions', data)
  }

  async deleteSession(sessionId: string): Promise<ApiResponse<{ success: boolean; deleted_tasks_count: number; deleted_steps_count: number }>> {
    return this.client.delete(`/api/sessions/${sessionId}`)
  }

  async deleteAllSessions(): Promise<ApiResponse<{ success: boolean; deleted_sessions_count: number }>> {
    return this.client.delete('/api/sessions')
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
    //return this.client.get('/api/checkpoints', { params })
    return Promise.resolve({ code: 0, message: 'success', data: { total: 0, checkpoints: [] } })
  }

  async resumeCheckpoint(taskId: string): Promise<ApiResponse<{ execution_id: string; task: string; status: string; message: string; resumed_from_step: number }>> {
    //return this.client.post(`/api/checkpoints/${taskId}/resume`)
    return Promise.resolve({ code: 0, message: 'success', data: { execution_id: '', task: '', status: '', message: '', resumed_from_step: 0 } })
  }

  async deleteCheckpoint(taskId: string): Promise<ApiResponse<{ success: boolean; deleted_steps_count: number }>> {
    //return this.client.delete(`/api/checkpoints/${taskId}`)
    return Promise.resolve({ code: 0, message: 'success', data: { success: true, deleted_steps_count: 0 } })
  }

  // 保留原有的getSkills方法，用于兼容旧的API
  async getSkills(params?: {
    status?: string
    page?: number
    page_size?: number
    keyword?: string
  }): Promise<ApiResponse<{ total: number; skills: Skill[] }>> {
    return this.client.get('/api/skills', { params })
  }

  // 保留原有的installSkill方法，用于兼容旧的API
  async installSkill(data: {
    skill_data: SkillManifest
    skill_files: Record<string, string>
    auto_fix?: boolean
  }): Promise<ApiResponse<{ skill_id: string; status: string; message: string; installed_at: string }>> {
    return this.client.post('/api/skills/install', data)
  }

  // 新的Gateway API方法，使用不同的方法名以避免冲突
  async getGatewaySkills(): Promise<{ skills: Skill[] }> {
    return this.client.get('/api/skills')
  }

  async installGatewaySkill(file: File): Promise<SuccessResponse & { skill: { name: string; display_name: string; path: string } }> {
    const formData = new FormData()
    formData.append('file', file)

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }

    return this.client.post('/api/skills/install', formData, config)
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

  // LangGraph API
  async createThread(metadata?: Record<string, any>): Promise<Thread> {
    return this.client.post('/api/langgraph/threads', { metadata: metadata || {} })
  }

  async getThreadState(threadId: string): Promise<ThreadState> {
    return this.client.get(`/api/langgraph/threads/${threadId}/state`)
  }

  async createRun(threadId: string, input: RunInput): Promise<Response> {
    const config: RequestInit = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(input)
    }

    const response = await fetch(`${this.baseUrl}/api/langgraph/threads/${threadId}/runs`, config)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response
  }

  async getRunHistory(threadId: string): Promise<RunHistory> {
    return this.client.get(`/api/langgraph/threads/${threadId}/runs`)
  }

  async streamRun(threadId: string, input: RunInput): Promise<Response> {
    const config: RequestInit = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(input)
    }

    const response = await fetch(`${this.baseUrl}/api/langgraph/threads/${threadId}/runs/stream`, config)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response
  }

  // Gateway API
  async getModels(): Promise<{ models: Model[] }> {
    return this.client.get('/api/models')
  }

  async getModelDetails(modelName: string): Promise<ModelDetail> {
    return this.client.get(`/api/models/${modelName}`)
  }

  async getMCPConfig(): Promise<MCPConfig> {
    return this.client.get('/api/mcp/config')
  }

  async updateMCPConfig(config: MCPConfig): Promise<SuccessResponse> {
    return this.client.put('/api/mcp/config', config)
  }

  async getSkillDetails(skillName: string): Promise<SkillDetail> {
    return this.client.get(`/api/skills/${skillName}`)
  }

  async enableSkill(skillName: string): Promise<SuccessResponse> {
    return this.client.post(`/api/skills/${skillName}/enable`)
  }

  async disableSkill(skillName: string): Promise<SuccessResponse> {
    return this.client.post(`/api/skills/${skillName}/disable`)
  }

  // File Uploads
  async uploadFiles(threadId: string, files: File[]): Promise<FileUploadResponse> {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }

    return this.client.post(`/api/threads/${threadId}/uploads`, formData, config)
  }

  async listUploadedFiles(threadId: string): Promise<FileListResponse> {
    return this.client.get(`/api/threads/${threadId}/uploads/list`)
  }

  async deleteFile(threadId: string, filename: string): Promise<SuccessResponse> {
    return this.client.delete(`/api/threads/${threadId}/uploads/${filename}`)
  }

  async deleteThread(threadId: string): Promise<SuccessResponse> {
    return this.client.delete(`/api/threads/${threadId}`)
  }

  // Artifacts
  async getArtifact(threadId: string, path: string, download?: boolean): Promise<Blob> {
    const params = download ? { download: 'true' } : {}
    const response = await this.client.get(`/api/threads/${threadId}/artifacts/${path}`, {
      params,
      responseType: 'blob'
    })
    return response as unknown as Blob
  }
}

