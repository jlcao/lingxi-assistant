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
import WorkspaceSwitchDialog from './components/WorkspaceSwitchDialog.vue'
import WorkspaceInitializer from './components/WorkspaceInitializer.vue'
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
  appStore.setLoading(true)

  try {
    // 首先加载工作区信息
    if (window.electronAPI?.workspace) {
      await workspaceStore.loadCurrentWorkspace()
    }

    if (window.electronAPI?.api) {
      const [sessions, checkpoints, resourceUsage] = await Promise.all([
        window.electronAPI.api.getSessions(),
        window.electronAPI.api.getCheckpoints(),
        window.electronAPI.api.getResourceUsage()
      ])

      // 转换后端返回的会话数据格式为前端期望的格式
      const formattedSessions = (sessions || []).map((session: any) => ({
        id: session.session_id || session.id,
        name: session.title || session.name || '新会话',
        createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
        updatedAt: session.updated_at ? new Date(session.updated_at).getTime() : Date.now()
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
        const turns: any[] = []
        const historyList = (history || []).reverse() // 反转顺序，使最早的消息在前
        
        historyList.forEach((task: any, taskIndex: number) => {
          // 添加用户消息
          if (task.user_input) {
            turns.push({
              id: `${formattedSessions[0].id}_user_${taskIndex}`,
              role: 'user',
              content: task.user_input,
              timestamp: task.created_at ? new Date(task.created_at).getTime() : Date.now(),
              time: task.created_at ? new Date(task.created_at).getTime() : Date.now()
            })
          }
          
          // 添加助手消息
          turns.push({
            id: `${formattedSessions[0].id}_assistant_${taskIndex}`,
            role: 'assistant',
            content: task.result || '',
            timestamp: task.updated_at ? new Date(task.updated_at).getTime() : Date.now(),
            time: task.updated_at ? new Date(task.updated_at).getTime() : Date.now(),
            steps: task.steps || [],
            thought: task.thought || '',
            thought_chain: task.thought_chain || null,
            plan: task.plan || null,
            executionId: task.task_id || null,
            status: task.status || null,
            isThinking: false,
            taskLevel: task.task_level || 'simple'
          })
        })
        
        appStore.setTurns(turns)
        
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
          updatedAt: Date.now()
        }
        appStore.setSessions([session])
        appStore.setCurrentSession(session.id)
        appStore.setTurns([])
        
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
      // 查找是否已存在临时助手消息
      const updatedTurns = [...appStore.turns]
      const tempIndex = updatedTurns.findIndex(turn => 
        turn.role === 'assistant' && 
        turn.executionId && 
        turn.executionId.startsWith('temp_') &&
        turn.isStreaming
      )
      
      if (tempIndex !== -1) {
        // 更新临时助手消息的执行 ID 和状态
        updatedTurns[tempIndex] = {
          ...updatedTurns[tempIndex],
          executionId: data.executionId,
          status: 'running',
          isStreaming: true,
          taskLevel: data.task_level || 'simple'
        }
        appStore.setTurns(updatedTurns)
      } else {
        // 创建一个新的助手消息，用于关联后续的任务执行
        const assistantMessage = {
          id: `assistant-${data.executionId || Date.now()}`,
          role: 'assistant',
          content: '',
          time: Date.now(),
          executionId: data.executionId,
          status: 'running',
          isThinking: false,
          thought: '',
          steps: [],
          plan: null,
          taskLevel: data.task_level || 'simple'
        }
        appStore.setTurns([...appStore.turns, assistantMessage])
      }
    })

    window.electronAPI.ws.onTaskEnd((data) => {
      console.log('Task ended:', data)
      // 更新助手消息的内容
      if (data.result) {
        const updatedTurns = [...appStore.turns]
        const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
        if (targetIndex !== -1) {
          const turn = updatedTurns[targetIndex]
          
          // 确保所有步骤都被标记为已完成
          if (turn.steps) {
            turn.steps = turn.steps.map(step => ({
              ...step,
              status: 'completed'
            }))
          }
          
          updatedTurns[targetIndex] = {
            ...turn,
            content: data.result,
            status: 'completed',
            isStreaming: false,
            isThinking: false
          }
          appStore.setTurns(updatedTurns)
        }
      }
      
      // 任务结束后刷新工作区目录
      workspaceStore.refreshDirectoryTree()
    })

    window.electronAPI.ws.onThinkStart((data) => {
      console.log('Think started:', data)
      // 找到对应的助手消息，添加思考开始标记
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        updatedTurns[targetIndex] = {
          ...updatedTurns[targetIndex],
          isThinking: true
          
        }
        if (data.step_index === -1) {
          updatedTurns[targetIndex].planThinking = true
        } else {
          updatedTurns[targetIndex].planThinking = false
        }

        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onThinkStream((data) => {
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        const turn = updatedTurns[targetIndex]
        const content = data.body?.reasoning_content || data.content || ''
        const stepIndex = data.step_index ?? data.stepId
        
        if (stepIndex === -1) {
          if (!turn.planThinkingContent) {
            turn.planThinkingContent = ''
          }
          turn.planThinkingContent += content
          turn.planThinking = true
        } else {
          if (!turn.steps) {
            turn.steps = []
          }

          const actualStepIndex = stepIndex ?? turn.steps.length - 1

          if (!turn.steps[actualStepIndex]) {
            turn.steps[actualStepIndex] = {
              step_index: actualStepIndex,
              description: `步骤 ${actualStepIndex + 1}`,
              status: 'running',
              thought: ''
            }
          }

          if (!turn.steps[actualStepIndex].thought) {
            turn.steps[actualStepIndex].thought = ''
          }
          turn.steps[actualStepIndex].thought += content
        }

        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onThinkFinal((data) => {
      console.log('Think final:', data)
      // 找到对应的助手消息，完成思考标记并更新步骤的思考内容
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        const turn = updatedTurns[targetIndex]
        turn.isThinking = false
        
        // 将最终思考内容添加到具体的 step 对象上
        if (turn.steps) {
          // 获取当前步骤索引，默认为最后一个步骤
          const stepIndex = data.step_index || turn.steps.length - 1
          
          // 确保步骤对象存在
          if (turn.steps[stepIndex]) {
            turn.steps[stepIndex].thought = data.content || turn.steps[stepIndex].thought
          }
        }
        
        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onPlanStart((data) => {
      console.log('Plan started:', data)
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        updatedTurns[targetIndex] = {
          ...updatedTurns[targetIndex],
          planThinking: true,
          planThinkingContent: ''
        }
        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onPlanFinal((data) => {
      console.log('Plan final:', data)
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        updatedTurns[targetIndex] = {
          ...updatedTurns[targetIndex],
          planThinking: false,
          plan: data.plan || []
        }
        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onStepStart((data) => {
      console.log('Step started:', data)
      // 找到对应的助手消息，添加步骤开始信息
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        if (!updatedTurns[targetIndex].steps) {
          updatedTurns[targetIndex].steps = []
        }
        
        const stepIndex = data.step_index ?? 0
        const existingStepIndex = updatedTurns[targetIndex].steps.findIndex(step => step.step_index === stepIndex)
        
        if (existingStepIndex !== -1) {
          // 更新已存在的步骤
          updatedTurns[targetIndex].steps[existingStepIndex] = {
            ...updatedTurns[targetIndex].steps[existingStepIndex],
            status: 'running'
          }
        } else {
          // 添加新步骤
          updatedTurns[targetIndex].steps.push({
            step_index: stepIndex,  // 使用 step_index 字段
            description: `步骤 ${stepIndex + 1}`,
            status: 'running',
            thought: ''  // 初始化 thought 字段
          })
          
          // 按照 step_index 排序步骤
          updatedTurns[targetIndex].steps.sort((a, b) => (a.step_index ?? 0) - (b.step_index ?? 0))
        }
        
        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onStepEnd((data) => {
      console.log('Step ended:', data)
      // 找到对应的助手消息，更新步骤状态
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1 && updatedTurns[targetIndex].steps) {
        const stepIndex = data.step_index ?? updatedTurns[targetIndex].steps.length - 1
        if (updatedTurns[targetIndex].steps[stepIndex] !== undefined) {
          // 如果后端返回了纯文本 thought，使用它替换流式累积的 JSON
          const thought = data.thought || ''
          
          updatedTurns[targetIndex].steps[stepIndex] = {
            ...updatedTurns[targetIndex].steps[stepIndex],
            step_index: stepIndex,  // 确保 step_index 字段存在
            description: data.description || updatedTurns[targetIndex].steps[stepIndex].description,
            status: data.status || 'completed',
            result: data.result,
            thought: thought  // 使用后端返回的纯文本 thought
          }
        }
        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onTaskFailed((data) => {
      console.log('Task failed:', data)
      // 找到对应的助手消息，添加失败信息
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        updatedTurns[targetIndex] = {
          ...updatedTurns[targetIndex],
          status: 'failed',
          error: data.error || '任务执行失败',
          isThinking: false
        }
        appStore.setTurns(updatedTurns)
      }
    })
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
