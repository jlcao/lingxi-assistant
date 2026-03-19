export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  error?: {
    error_code: string
    error_detail: string
  }
}

export interface Session {
  id: string
  name: string
  createdAt: number
  updatedAt: number
  userName?: string
  hasCheckpoint: boolean
  checkpointCount: number
  checkpointExpiry?: number
}

export interface SessionWithTasks extends Session {
  tasks: Task[]
}

export interface Task {
  task_id: string
  user_input: string
  result?: string
  status: 'running' | 'completed' | 'failed'
  task_level?: 'simple' | 'complex' | 'trivial'
  created_at: number
  updated_at: number
  steps?: Step[]
  thought?: string
  thought_chain?: any
  plan?: any
}

export interface HistoryResponse {
  sessionId: string
  turns: Turn[]
}

export interface Turn {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  thoughtChain?: ThoughtChain
  modelRoute?: ModelRoute
  steps?: Step[]
}

export interface ThoughtChain {
  taskId: string
  steps: ThoughtStep[]
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface ThoughtStep {
  stepIndex: number
  type: 'analysis' | 'planning' | 'routing' | 'execution'
  content: string
  confidence?: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  thought?: string
  action?: string
  observation?: string
  error?: string
}

export interface ModelRoute {
  taskId: string
  selectedModel: string
  reason: string
  estimatedTokens: number
  estimatedCost: number
  canOverride: boolean
}

export interface StepError {
  message: string
  type: string
  suggestions: string[]
  requiresIntervention: boolean
}

export type UUID = string
export type Timestamp = number
export type DateTime = string

export interface SessionDetail {
  session_id: UUID
  user_name: string
  title: string
  current_task_id: UUID | null
  total_tokens: number
  created_at: DateTime
  updated_at: DateTime
  current_task?: TaskSummary
}

export interface TaskSummary {
  task_id: UUID
  task_type: 'simple' | 'complex' | 'trivial'
  user_input: string
  status: 'running' | 'completed' | 'failed' | 'paused'
  current_step_idx: number
  total_steps: number
  created_at: DateTime
}

export interface HistoryItem {
  task_id: UUID
  role: 'user' | 'assistant'
  content: string
  task_type: 'simple' | 'complex' | 'trivial'
  status: string
  timestamp: Timestamp
  steps?: Step[]
}

export interface ExecutionResult {
  execution_id: UUID
  task: string
  task_level: 'trivial' | 'simple' | 'complex'
  model: string
  status: 'running' | 'queued' | 'completed' | 'failed'
  estimated_duration: number
  created_at: Timestamp
}

export interface ExecutionStatus {
  execution_id: UUID
  task: string
  task_level: 'trivial' | 'simple' | 'complex'
  model: string
  status: 'running' | 'completed' | 'failed' | 'paused' | 'cancelled'
  current_step: number
  total_steps: number
  progress: number
  result?: {
    content: string
    thought_chain: any[]
    steps: any[]
  }
  error?: {
    error: string
    error_code: string
    traceback: string
  }
  input_tokens: number
  output_tokens: number
  created_at: Timestamp
  updated_at: Timestamp
}

export interface Step {
  step_id: UUID
  step_index: number
  step_type: 'thinking' | 'action'
  description: string
  thought: string
  result: string
  skill_call: string | null
  status: 'completed' | 'failed' | 'running'
  result_description?: string
  created_at: DateTime
}

export interface Checkpoint {
  session_id: UUID
  task_id: UUID
  task: string
  task_level: 'simple' | 'complex'
  current_step: number
  total_steps: number
  execution_status: 'paused' | 'running'
  paused_reason: 'user_request' | 'error' | 'timeout'
  created_at: DateTime
  updated_at: DateTime
}

export interface Skill {
  skill_id: string
  name: string
  description: string
  version: string
  author: string
  status: 'available' | 'error' | 'installed'
  manifest: SkillManifest
  installed_at?: DateTime
  source?: SkillSourceType
  workspace_path?: string
}

export type SkillSourceType = 'global' | 'workspace'

export interface WorkspaceInfo {
  workspace: string | null
  lingxi_dir: string | null
  is_initialized: boolean
}

export interface WorkspaceSwitchResult {
  previous_workspace: string
  current_workspace: string
  lingxi_dir: string
  switched_at: DateTime
}

export interface WorkspaceInitResult {
  workspace: string
  lingxi_dir: string
}

export interface WorkspaceValidationResult {
  valid: boolean
  exists: boolean
  has_lingxi_dir: boolean
  message: string
}

export interface WorkspaceConfig {
  workspace?: {
    name?: string
    description?: string
  }
  skills?: {
    enabled?: string[]
  }
  database?: {
    assistant_db?: string
    memory_db?: string
  }
  security?: {
    safety_mode?: boolean
    max_file_size?: number
    allowed_commands?: string[]
  }
}

export interface SkillManifest {
  name: string
  version: string
  description: string
  author: string
  dependencies?: string[]
  entry_point: string
}

export interface DiagnosticResult {
  skill_id: string
  status: 'error' | 'healthy'
  diagnostic_result: {
    error_type: 'missing_dependency' | 'invalid_manifest' | 'runtime_error'
    error_message: string
    fix_suggestion: string
    can_auto_fix: boolean
    dependencies?: Dependency[]
  }
}

export interface Dependency {
  name: string
  required: string
  installed: boolean
}

export interface ResourceUsage {
  system: {
    cpu_percent: number
    memory_percent: number
    disk_percent: number
  }
  token_usage: {
    current: number
    limit: number
    percent: number
    daily_limit: number
    daily_used: number
  }
  tasks: {
    running: number
    queued: number
    completed_today: number
  }
  skills: {
    total: number
    available: number
    error: number
  }
}

export interface Config {
  llm: {
    model: string
    api_key: string
    base_url: string
    timeout: number
    max_retries: number
  }
  execution: {
    max_steps: number
    max_replan_count: number
    enable_streaming: boolean
  }
  storage: {
    db_path: string
    enable_checkpoint: boolean
  }
  logging: {
    level: string
    log_file: string
  }
}

export interface FileFilter {
  name: string
  extensions: string[]
}

export interface SkillCallData {
  skillId: string
  skillName: string
  status: 'calling' | 'success' | 'failed'
  startTime: number
  endTime?: number
  error?: string
}

export interface ThoughtChainData {
  taskId: string
  step: ThoughtStep
}

export interface StepStatusData {
  executionId: string
  stepIndex: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  error?: StepError
}

export interface ModelRouteData {
  taskId: string
  modelRoute: ModelRoute
}

export interface TaskCompletedData {
  executionId: string
  result: string
  duration: number
}

export interface TaskFailedData {
  executionId: string
  error: string
  stepIndex?: number
}

export type CommonErrorCode =
  | 'INVALID_PARAMETER'
  | 'RESOURCE_NOT_FOUND'
  | 'INTERNAL_ERROR'
  | 'UNAUTHORIZED'

export type TaskErrorCode =
  | 'LLM_RATE_LIMIT'
  | 'LLM_TIMEOUT'
  | 'SKILL_EXECUTION'
  | 'DATABASE_LOCKED'
  | 'TASK_CANCELLED'
  | 'UNKNOWN'

export type SkillErrorCode =
  | 'SKILL_NOT_FOUND'
  | 'SKILL_ALREADY_INSTALLED'
  | 'MISSING_DEPENDENCY'
  | 'INVALID_MANIFEST'

export type ErrorCode = CommonErrorCode | TaskErrorCode | SkillErrorCode

export interface FileChange {
  type: 'created' | 'modified' | 'deleted'
  path: string
  timestamp?: string
}

export interface WorkspaceFilesChangedEvent {
  source: 'task_end' | 'file_watcher'
  session_id?: string
  task_id?: string
  changes: FileChange[]
}
