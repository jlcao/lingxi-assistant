<template>
  <div id="app" class="app-container">
    <TitleBar />
    <ResumeBanner v-if="activeCheckpoints.length > 0" />
    <EdgeWidget v-if="isEdgeHidden" />
    <LayoutContainer />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed } from 'vue'
import { useAppStore } from './stores/app'
import TitleBar from './components/TitleBar.vue'
import ResumeBanner from './components/ResumeBanner.vue'
import EdgeWidget from './components/EdgeWidget.vue'
import LayoutContainer from './components/LayoutContainer.vue'

const appStore = useAppStore()

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
    window.electronAPI.ws.removeAllListeners('ws:connected')
    window.electronAPI.ws.removeAllListeners('ws:disconnected')
    window.electronAPI.ws.removeAllListeners('ws:thought-chain')
    window.electronAPI.ws.removeAllListeners('ws:step-start')
    window.electronAPI.ws.removeAllListeners('ws:step-end')
    window.electronAPI.ws.removeAllListeners('ws:task-start')
    window.electronAPI.ws.removeAllListeners('ws:task-end')
    window.electronAPI.ws.removeAllListeners('ws:think-start')
    window.electronAPI.ws.removeAllListeners('ws:think-stream')
    window.electronAPI.ws.removeAllListeners('ws:think-final')
    window.electronAPI.ws.removeAllListeners('ws:plan-start')
    window.electronAPI.ws.removeAllListeners('ws:plan-final')
  }
})

async function initializeApp() {
  appStore.setLoading(true)

  try {
    if (window.electronAPI?.api && window.electronAPI?.ws) {
      const [sessions, checkpoints, resourceUsage] = await Promise.all([
        window.electronAPI.api.getSessions(),
        window.electronAPI.api.getCheckpoints(),
        window.electronAPI.api.getResourceUsage()
      ])

      appStore.setSessions(sessions)
      appStore.setCheckpoints(checkpoints)
      appStore.setResourceUsage(resourceUsage)

      if (sessions.length > 0) {
        appStore.setCurrentSession(sessions[0].id)
        const history = await window.electronAPI.api.getSessionHistory(sessions[0].id)
        // 转换后端返回的历史记录格式为前端期望的格式
        const turns = history.history.map((item: any, index: number) => ({
          id: `${sessions[0].id}_${index}`,
          role: item.role,
          content: item.content,
          timestamp: item.time || Date.now(),
          // 保留原始数据中的步骤、思考等信息
          steps: item.steps || [],
          thought: item.thought || '',
          thought_chain: item.thought_chain || null,
          plan: item.plan || null,
          executionId: item.executionId || null,
          status: item.status || null,
          isThinking: item.isThinking || false
        }))
        appStore.setTurns(turns)
      } else {
        // 没有会话时，创建一个新会话
        const sessionData = await window.electronAPI.api.createSession()
        const session = {
          id: sessionData.session_id,
          name: sessionData.user_name || '新会话'
        }
        appStore.setSessions([session])
        appStore.setCurrentSession(session.id)
        appStore.setTurns([])
      }

      await window.electronAPI.ws.connect(appStore.currentSessionId || undefined)
    }
  } catch (error) {
    console.error('Failed to initialize app:', error)
  } finally {
    appStore.setLoading(false)
  }
}

function setupWebSocketListeners() {
  if (window.electronAPI?.ws) {
    window.electronAPI.ws.onConnected(() => {
      appStore.setWsConnected(true)
    })

    window.electronAPI.ws.onDisconnected(() => {
      appStore.setWsConnected(false)
    })

    window.electronAPI.ws.onThoughtChain((data) => {
      console.log('Thought chain:', data)
      // 找到最近的用户消息或助手消息
      const latestTurn = appStore.turns[appStore.turns.length - 1]
      if (latestTurn) {
        // 将思考链信息添加到消息中
        const updatedTurns = [...appStore.turns]
        updatedTurns[updatedTurns.length - 1] = {
          ...latestTurn,
          thought_chain: {
            taskId: data.taskId || Date.now(),
            steps: data.thoughts || [data.step],
            status: 'running'
          }
        }
        appStore.setTurns(updatedTurns)
      }
      
      // 同时更新全局思考链
      if (appStore.thoughtChain) {
        appStore.thoughtChain.steps.push(data.step)
      } else {
        appStore.setThoughtChain({
          taskId: data.taskId || Date.now(),
          steps: [data.step],
          status: 'running'
        })
      }
    })

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
        // 更新临时助手消息的执行ID和状态
        updatedTurns[tempIndex] = {
          ...updatedTurns[tempIndex],
          executionId: data.executionId,
          status: 'running',
          isStreaming: true
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
          plan: null
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
        appStore.setTurns(updatedTurns)
      }
    })

    window.electronAPI.ws.onThinkStream((data) => {
      console.log('[Renderer] Think stream received:', data)
      // 找到对应的助手消息，将思考内容添加到具体的step对象上
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.execution_id)
      if (targetIndex !== -1) {
        const turn = updatedTurns[targetIndex]
        if (!turn.steps) {
          turn.steps = []
        }

        // 获取当前步骤索引，默认为最后一个步骤
        const stepIndex = data.step_index || turn.steps.length - 1

        // 确保步骤对象存在
        if (!turn.steps[stepIndex]) {
          turn.steps[stepIndex] = {
            step_id: stepIndex,
            description: `步骤 ${stepIndex + 1}`,
            status: 'running',
            thought: ''
          }
        }

        // 添加思考内容到步骤对象
        const content = data.body?.reasoning_content || data.content || ''
        if (!turn.steps[stepIndex].thought) {
          turn.steps[stepIndex].thought = ''
        }
        turn.steps[stepIndex].thought += content

        console.log(`[Renderer] Updated step ${stepIndex} thought, length: ${turn.steps[stepIndex].thought.length}`)
        appStore.setTurns(updatedTurns)
      } else {
        console.log('[Renderer] No turn found for executionId:', data.execution_id)
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
        
        // 将最终思考内容添加到具体的step对象上
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
    })

    window.electronAPI.ws.onPlanFinal((data) => {
      console.log('Plan final:', data)
      // 找到对应的助手消息，添加计划信息
      const updatedTurns = [...appStore.turns]
      const targetIndex = updatedTurns.findIndex(turn => turn.executionId === data.executionId)
      if (targetIndex !== -1) {
        updatedTurns[targetIndex] = {
          ...updatedTurns[targetIndex],
          plan: {
            steps: data.plan || [],
            status: 'completed'
          }
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
        
        const stepIndex = data.step_index || 0
        const existingStepIndex = updatedTurns[targetIndex].steps.findIndex(step => step.stepIndex === stepIndex)
        
        if (existingStepIndex !== -1) {
          // 更新已存在的步骤
          updatedTurns[targetIndex].steps[existingStepIndex] = {
            ...updatedTurns[targetIndex].steps[existingStepIndex],
            status: 'running'
          }
        } else {
          // 添加新步骤
          updatedTurns[targetIndex].steps.push({
            stepIndex: stepIndex,
            description: `步骤 ${stepIndex + 1}`,
            status: 'running'
          })
          
          // 按照stepIndex排序步骤
          updatedTurns[targetIndex].steps.sort((a, b) => a.stepIndex - b.stepIndex)
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
        const stepIndex = data.step_index || updatedTurns[targetIndex].steps.length - 1
        if (updatedTurns[targetIndex].steps[stepIndex]) {
          updatedTurns[targetIndex].steps[stepIndex] = {
            ...updatedTurns[targetIndex].steps[stepIndex],
            description: data.description || updatedTurns[targetIndex].steps[stepIndex].description,
            status: data.status || 'completed',
            step_id: data.step_id || stepIndex,
            result: data.result
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
