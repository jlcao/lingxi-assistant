<template>
  <div id="app" class="app-container">
    <TitleBar />
    <ResumeBanner v-if="activeCheckpoints.length > 0" />
    <EdgeWidget v-if="isEdgeHidden" />
    <LayoutContainer />
    <WorkspaceSwitchDialog />
    <WorkspaceInitializer />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import EdgeWidget from './components/EdgeWidget.vue'
import LayoutContainer from './components/LayoutContainer.vue'
import ResumeBanner from './components/ResumeBanner.vue'
import TitleBar from './components/TitleBar.vue'
import WorkspaceInitializer from './components/WorkspaceInitializer.vue'
import WorkspaceSwitchDialog from './components/WorkspaceSwitchDialog.vue'
import { useAppStore } from './stores/app'
import { useWorkspaceStore } from './stores/workspace'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()

const isEdgeHidden = computed(() => {
  return window.electronAPI?.window?.edgeCheck?.() || false
})

const activeCheckpoints = computed(() => {
  return appStore.activeCheckpoints
})

onMounted(async () => {
  await initializeApp()
  setupWebSocketListeners()
})

onUnmounted(() => {
  if (window.electronAPI?.ws) {
    window.electronAPI.ws.removeAllListeners('ws:task-start')
    window.electronAPI.ws.removeAllListeners('ws:task-end')
    window.electronAPI.ws.removeAllListeners('ws:think-start')
    window.electronAPI.ws.removeAllListeners('ws:think-stream')
    window.electronAPI.ws.removeAllListeners('ws:think-final')
    window.electronAPI.ws.removeAllListeners('ws:plan-start')
    window.electronAPI.ws.removeAllListeners('ws:plan-final')
    window.electronAPI.ws.removeAllListeners('ws:step-start')
    window.electronAPI.ws.removeAllListeners('ws:step-end')
    window.electronAPI.ws.removeAllListeners('ws:task-failed')
    window.electronAPI.ws.removeAllListeners('ws:error')
  }
})

async function initializeApp() {
  console.log('[App] initializeApp called')
  appStore.setLoading(true)

  try {
    // 首先加载工作区信息
    if (window.electronAPI?.workspace) {
      console.log('[App] Loading current workspace...')
      await workspaceStore.loadCurrentWorkspace()
      console.log('[App] Current workspace loaded:', workspaceStore.currentWorkspace)
    }

    if (window.electronAPI?.api) {
      console.log('[App] Loading checkpoints and resource usage...')
      const [checkpoints, resourceUsage] = await Promise.all([
        window.electronAPI.api.getCheckpoints(),
        window.electronAPI.api.getResourceUsage()
      ])

      // 根据工作目录加载会话列表
      let sessions
      const currentWorkspace = workspaceStore.currentWorkspace
      if (currentWorkspace?.workspace) {
        console.log('[App] Loading sessions for workspace:', currentWorkspace.workspace)
        sessions = await window.electronAPI.api.getWorkspaceSessions(currentWorkspace.workspace)
        sessions = sessions.sessions || []
      } else {
        console.log('[App] No workspace initialized, loading all sessions')
        sessions = await window.electronAPI.api.getSessions()
      }

      // 转换后端返回的会话数据格式为前端期望的格式
      const formattedSessions = (sessions || []).map((session: any) => ({
        id: session.session_id || session.id,
        name: session.title || session.name || '新会话',
        createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
        updatedAt: session.updated_at ? new Date(session.updated_at).getTime() : Date.now(),
        tasks: []
      }))

      appStore.setSessions(formattedSessions)
      
      // 转换后端返回的 checkpoint 数据格式为前端期望的格式
      const formattedCheckpoints = (checkpoints || []).map((checkpoint: any) => ({
        id: checkpoint.session_id,
        sessionId: checkpoint.session_id,
        name: checkpoint.state?.task || '未命名任务',
        timestamp: checkpoint.updated_at || Date.now()
      }))
      appStore.setCheckpoints(formattedCheckpoints)
      
      appStore.setResourceUsage(resourceUsage)

      if (formattedSessions && formattedSessions.length > 0) {
        appStore.setCurrentSession(formattedSessions[0].id)
        const history = await window.electronAPI.api.getSessionHistory(formattedSessions[0].id)
        
        // 转换后端返回的历史记录格式为前端期望的格式
        // 后端返回的是任务列表（按created_at DESC排序），每个任务需要转换成用户消息和助手消息两条记录
        const tasks: any[] = []
        const historyList = (history || []).reverse() // 反转顺序，使最早的消息在前
        
        historyList.forEach((task: any) => {
          tasks.push({
            task_id: task.task_id || task.session_id,
            user_input: task.user_input || '',
            result: task.result || '',
            status: task.status || 'completed',
            task_level: task.task_level || 'simple',
            created_at: task.created_at ? new Date(task.created_at).getTime() : Date.now(),
            updated_at: task.updated_at ? new Date(task.updated_at).getTime() : Date.now(),
            steps: task.steps || [],
            thought: task.thought || '',
            thought_chain: task.thought_chain || null,
            plan: task.plan || null
          })
        })
        
        appStore.setSessionTasks(formattedSessions[0].id, tasks)
        
        // 建立 WebSocket 连接
        if (window.electronAPI?.ws) {
          await window.electronAPI.ws.connect(formattedSessions[0].id)
        }
      } else {
        // 没有会话时，创建一个新会话
        const sessionData = await window.electronAPI.api.createSession()
        const session = {
          id: sessionData.session_id,
          name: sessionData.first_message || '新会话',
          createdAt: Date.now(),
          updatedAt: Date.now(),
          tasks: []
        }
        appStore.addSession(session)
        appStore.setCurrentSession(session.id)
        
        // 建立 WebSocket 连接
        if (window.electronAPI?.ws) {
          await window.electronAPI.ws.connect(session.id)
        }
      }
    }
  } catch (error) {
    console.error('Failed to initialize app:', error)
  } finally {
    appStore.setLoading(false)
  }
}

function setupWebSocketListeners() {
  if (window.electronAPI?.ws) {
    window.electronAPI.ws.onTaskStart((data) => {
      console.log('Task started:', data)
      // 创建一个新的任务
      const newTask = {
        task_id: data.executionId,
        user_input: '',
        result: '',
        status: 'running' as const,
        task_level: data.task_level || 'simple',
        created_at: Date.now(),
        updated_at: Date.now(),
        steps: [],
        thought: '',
        thought_chain: null,
        plan: null
      }
      appStore.addTaskToSession(appStore.currentSessionId || '', newTask)
    })

    window.electronAPI.ws.onTaskEnd((data) => {
      console.log('Task ended:', data)
      // 更新任务的内容
      if (data.result) {
        appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
          result: data.result,
          status: 'completed',
          updated_at: Date.now()
        })
      }
      
      // 任务结束后刷新工作区目录
      workspaceStore.refreshDirectoryTree()
      
      // 任务结束后刷新历史会话列表，重新加载会话名称
      refreshSessionsList()
    })

    window.electronAPI.ws.onThinkStart((data) => {
      console.log('Think started:', data)
      // 找到对应的任务，添加思考开始标记
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task) {
        appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
          planThinking: true
        })
      }
    })

    window.electronAPI.ws.onThinkStream((data) => {
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task) {
        const content = data.body?.reasoning_content || data.content || ''
        const stepIndex = data.step_index ?? data.stepId
        
        if (stepIndex === -1) {
          // 计划思考
          appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
            planThinkingContent: (task.planThinkingContent || '') + content,
            planThinking: true
          })
        } else {
          // 步骤思考
          const updatedSteps = task.steps ? [...task.steps] : []
          const actualStepIndex = stepIndex ?? updatedSteps.length - 1

          if (!updatedSteps[actualStepIndex]) {
            updatedSteps[actualStepIndex] = {
              step_index: actualStepIndex,
              description: `步骤 ${actualStepIndex + 1}`,
              status: 'running',
              thought: ''
            }
          }

          if (!updatedSteps[actualStepIndex].thought) {
            updatedSteps[actualStepIndex].thought = ''
          }
          updatedSteps[actualStepIndex].thought += content

          appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
            steps: updatedSteps
          })
        }
      }
    })

    window.electronAPI.ws.onThinkFinal((data) => {
      console.log('Think final:', data)
      // 找到对应的任务，完成思考标记并更新步骤的思考内容
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task) {
        // 将最终思考内容添加到具体的 step 对象上
        if (task.steps) {
          // 获取当前步骤索引，默认为最后一个步骤
          const stepIndex = data.step_index || task.steps.length - 1
          
          // 确保步骤对象存在
          if (task.steps[stepIndex]) {
            const updatedSteps = [...task.steps]
            updatedSteps[stepIndex] = {
              ...updatedSteps[stepIndex],
              thought: data.content || updatedSteps[stepIndex].thought
            }
            appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
              steps: updatedSteps
            })
          }
        }
      }
    })

    window.electronAPI.ws.onPlanStart((data) => {
      console.log('Plan started:', data)
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task) {
        appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
          planThinking: true,
          planThinkingContent: ''
        })
      }
    })

    window.electronAPI.ws.onPlanFinal((data) => {
      console.log('Plan final:', data)
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task) {
        appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
          planThinking: false,
          plan: data.plan || []
        })
      }
    })

    window.electronAPI.ws.onStepStart((data) => {
      console.log('Step started:', data)
      // 找到对应的任务，添加步骤开始信息
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task) {
        const updatedSteps = task.steps ? [...task.steps] : []
        
        const stepIndex = data.step_index ?? 0
        const existingStepIndex = updatedSteps.findIndex(step => step.step_index === stepIndex)
        
        if (existingStepIndex !== -1) {
          // 更新已存在的步骤
          updatedSteps[existingStepIndex] = {
            ...updatedSteps[existingStepIndex],
            status: 'running'
          }
        } else {
          // 添加新步骤
          updatedSteps.push({
            step_id: '',
            step_index: stepIndex,
            step_type: 'thinking' as const,
            description: `步骤 ${stepIndex + 1}`,
            thought: '',
            result: '',
            skill_call: null,
            status: 'running',
            created_at: new Date().toISOString()
          })
          
          // 按照 step_index 排序步骤
          updatedSteps.sort((a, b) => (a.step_index ?? 0) - (b.step_index ?? 0))
        }
        
        appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
          steps: updatedSteps
        })
      }
    })

    window.electronAPI.ws.onStepEnd((data) => {
      console.log('Step ended:', data)
      // 找到对应的任务，更新步骤状态
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task && task.steps) {
        const stepIndex = data.step_index ?? task.steps.length - 1
        if (task.steps[stepIndex] !== undefined) {
          // 如果后端返回了纯文本 thought，使用它替换流式累积的 JSON
          const thought = data.thought || ''
          
          const updatedSteps = [...task.steps]
          updatedSteps[stepIndex] = {
            ...updatedSteps[stepIndex],
            step_index: stepIndex,
            description: data.description || updatedSteps[stepIndex].description,
            result_description: data.result_description || '',
            status: data.status || 'completed',
            result: data.result,
            thought: thought
          }
          
          appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
            steps: updatedSteps
          })
        }
      }
    })

    window.electronAPI.ws.onTaskFailed((data) => {
      console.log('Task failed:', data)
      // 找到对应的任务，添加失败信息
      const task = appStore.getTaskFromSession(appStore.currentSessionId || '', data.executionId)
      if (task) {
        appStore.updateTaskInSession(appStore.currentSessionId || '', data.executionId, {
          status: 'failed',
          error: data.error || '任务执行失败'
        })
      }
    })
  }
}

async function refreshSessionsList() {
  console.log('[App] Refreshing sessions list...')
  try {
    let sessions
    const currentWorkspace = workspaceStore.currentWorkspace
    if (currentWorkspace?.workspace) {
      console.log('[App] Loading sessions for workspace:', currentWorkspace.workspace)
      const result = await window.electronAPI.api.getWorkspaceSessions(currentWorkspace.workspace)
      sessions = result.sessions || []
    } else {
      console.log('[App] No workspace initialized, loading all sessions')
      sessions = await window.electronAPI.api.getSessions()
    }

    // 转换后端返回的会话数据格式为前端期望的格式
    const formattedSessions = (sessions || []).map((session: any) => {
      // 保留现有会话的任务数据
      const existingSession = appStore.sessions.get(session.session_id || session.id)
      return {
        id: session.session_id || session.id,
        name: session.title || session.name || '新会话',
        createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
        updatedAt: session.updated_at ? new Date(session.updated_at).getTime() : Date.now(),
        tasks: existingSession?.tasks || []
      }
    })

    appStore.setSessions(formattedSessions)
    console.log('[App] Sessions list refreshed:', formattedSessions.length, 'sessions')
  } catch (error) {
    console.error('[App] Failed to refresh sessions list:', error)
  }
}
</script>

<style scoped lang="scss">
.app-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: $bg-page;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  box-sizing: border-box;
}
</style>
