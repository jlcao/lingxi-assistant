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
import { computed, onMounted, onUnmounted, ref } from 'vue'
import EdgeWidget from './components/EdgeWidget.vue'
import LayoutContainer from './components/LayoutContainer.vue'
import ResumeBanner from './components/ResumeBanner.vue'
import TitleBar from './components/TitleBar.vue'
import WorkspaceInitializer from './components/WorkspaceInitializer.vue'
import WorkspaceSwitchDialog from './components/WorkspaceSwitchDialog.vue'
import { useAppStore } from './stores/app'
import { useWorkspaceStore } from './stores/workspace'
import { useWsStore } from './stores/wsStore'
import { apiService } from './api/apiService'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const wsStore = useWsStore()

const isEdgeHidden = ref(false)

const activeCheckpoints = computed(() => {
  return appStore.activeCheckpoints
})

onMounted(async () => {
  if (window.electronAPI?.window?.edgeCheck) {
    try {
      isEdgeHidden.value = await window.electronAPI.window.edgeCheck()
    } catch (error) {
      console.error('Failed to check edge:', error)
    }
  }
  await initializeApp()
  setupWebSocketListeners()
})

onUnmounted(() => {
  wsStore.removeAllListeners()
})

async function initializeApp() {
  console.log('[App] initializeApp called')
  appStore.setLoading(true)

  try {
    // 初始化API服务
    await apiService.init()

    // 首先加载工作区信息
    if (window.electronAPI?.workspace) {
      console.log('[App] Loading current workspace...')
      await workspaceStore.loadCurrentWorkspace()
      console.log('[App] Current workspace loaded:', workspaceStore.currentWorkspace)
    }

    console.log('[App] Loading checkpoints and resource usage...')
    const [checkpoints, resourceUsage] = await Promise.all([
      apiService.client.getCheckpoints(),
      apiService.client.getResourceUsage()
    ])

    // 根据工作目录加载会话列表
    let sessions
    const currentWorkspace = workspaceStore.currentWorkspace
    if (currentWorkspace?.workspace) {
      console.log('[App] Loading sessions for workspace:', currentWorkspace.workspace)
      const result = await apiService.client.getWorkspaceSessions(currentWorkspace.workspace)
      sessions = result.data.sessions || []
      console.log('[App] Loaded sessions:', sessions)
    } else {
      console.log('[App] No workspace initialized, loading all sessions')
      const result = await apiService.client.getSessions()
      sessions = result.data?.sessions || []
      console.log('[App] Loaded sessions:', sessions)
    }

    if (sessions && sessions.length > 0) {
      appStore.setSessions(sessions)
      appStore.setCurrentSession(sessions[0].sessionId)
      
      // 建立 WebSocket 连接
      wsStore.connect(sessions[0].sessionId)
    } else {
      // 没有会话时，创建一个新会话
      try {
        const sessionData = await apiService.client.createSession()
        const sessionDataPayload = sessionData.data || sessionData
        if (sessionDataPayload && (sessionDataPayload.session_id || sessionDataPayload.sessionId)) {
          const session = {
            sessionId: sessionDataPayload.session_id || sessionDataPayload.sessionId,
            title: sessionDataPayload.first_message || sessionDataPayload.firstMessage || '新会话',
            tasks: [],
            totalTokens: 0,
            userName: sessionDataPayload.user_name || sessionDataPayload.userName || '新用户',
            createdAt: Date.now(),
            updatedAt: Date.now(),
            currentTaskId: null,
            isTaskRunning: false
          }
          appStore.setSessions([session])
          appStore.setCurrentSession(session.sessionId)
          
          // 建立 WebSocket 连接
          wsStore.connect(session.sessionId)
        }
      } catch (error) {
        console.error('Failed to create session:', error)
      }
    }
  } catch (error) {
    console.error('Failed to initialize app:', error)
  } finally {
    appStore.setLoading(false)
  }
}

function setupWebSocketListeners() {
  wsStore.onTaskStart((data) => {
    console.log('Task started:', data)
    appStore.setCurrentTask(data.sessionId, data.taskId)
    appStore.updateTaskStatus(data.sessionId, data.taskId, 'running')
    // 更新会话的isTaskRunning状态
    const session = appStore.sessions.find(s => s.sessionId === data.sessionId)
    if (session) {
      session.isTaskRunning = true
    }
    // 查找是否已存在临时助手消息
    if(data.taskInfo){
      // 确保task对象包含planThinking和planThinkingContent属性，并处理时间戳
      const taskData = {
        ...data.taskInfo,
        planThinking: false,
        planThinkingContent: '',
        steps: data.taskInfo.steps || [],
        status: 'running',
        // 确保时间戳是数字格式
        createdAt: typeof data.taskInfo.createdAt === 'number' ? data.taskInfo.createdAt : Date.now(),
        updatedAt: typeof data.taskInfo.updatedAt === 'number' ? data.taskInfo.updatedAt : Date.now()
      }
      appStore.addTask(data.sessionId,data.taskId,taskData)
    }
    
  })

  wsStore.onTaskEnd((data) => {
    console.log('Task ended:', data)
    appStore.setCurrentTask(data.sessionId, null)
    appStore.updateTaskStatus(data.sessionId, data.taskId, 'completed')
    // 更新会话的isTaskRunning状态
    const session = appStore.sessions.find(s => s.sessionId === data.sessionId)
    if (session) {
      session.isTaskRunning = false
    }
    // 更新助手消息的内容
    if (data.result && data.taskInfo) {
      // 确保时间戳是数字格式
      const taskData = {
        ...data.taskInfo,
        status: 'completed',
        createdAt: typeof data.taskInfo.createdAt === 'number' ? data.taskInfo.createdAt : Date.now(),
        updatedAt: typeof data.taskInfo.updatedAt === 'number' ? data.taskInfo.updatedAt : Date.now()
      }
      appStore.addTask(data.sessionId,data.taskId,taskData)
    }

    // 任务结束后刷新工作区目录
    workspaceStore.refreshDirectoryTree()

    // 任务结束后刷新历史会话列表，重新加载会话名称
    refreshSessionsList()
  })
  
  wsStore.onTaskStopped((data) => {
    console.log('Task stopped:', data)
    const sessionId = data.sessionId || data.payload?.sessionId
    const taskId = data.taskId || data.payload?.taskId
    
    if (sessionId && taskId) {
      appStore.setCurrentTask(sessionId, null)
      appStore.updateTaskStatus(sessionId, taskId, 'stopped')
      // 更新会话的isTaskRunning状态
      const session = appStore.sessions.find(s => s.sessionId === sessionId)
      if (session) {
        session.isTaskRunning = false
      }
      // 更新任务数据，设置 result 为终止信息
      const taskData = {
        taskId: taskId,
        status: 'stopped',
        result: '任务已被用户终止',
        updatedAt: Date.now(),
        ...(data.taskInfo || {})
      }
      appStore.addTask(sessionId, taskId, taskData)
    }

    // 任务结束后刷新工作区目录
    workspaceStore.refreshDirectoryTree()

    // 任务结束后刷新历史会话列表，重新加载会话名称
    refreshSessionsList()
  })

  wsStore.onThinkStart((data) => {
    console.log('Think started:', data)
    // 找到对应的助手消息，添加思考开始标记
    if(data.taskInfo){
      // 确保时间戳是数字格式
      const taskData = {
        ...data.taskInfo,
        planThinking: true,
        planThinkingContent: '',
        createdAt: typeof data.taskInfo.createdAt === 'number' ? data.taskInfo.createdAt : Date.now(),
        updatedAt: typeof data.taskInfo.updatedAt === 'number' ? data.taskInfo.updatedAt : Date.now()
      }
      appStore.addTask(data.sessionId,data.taskId,taskData)
    }
    if(data.stepIndex && data.stepInfo){
      appStore.addStep(data.sessionId,data.taskId,data.stepIndex,{...data.stepInfo,isThinking:true,thought:''})
    }
  })

  wsStore.onThinkStream((data) => {
    //console.log('Think stream:', data)
    if(data.content && data.stepIndex>0){
      appStore.addThought(data.sessionId,data.taskId,data.stepIndex,data.content)
    }else{
      appStore.addThinkThought(data.sessionId,data.taskId,data.content)
    }
  })

  wsStore.onThinkFinal((data) => {
    console.log('Think final:', data)
    // 找到对应的助手消息，完成思考标记并更新步骤的思考内容
    if(data.stepIndex>0){
      appStore.stepThinkFinal(data.sessionId,data.taskId,data.stepIndex,false)
      // 更新步骤的思考内容
      if (data.taskInfo){
        appStore.addTask(data.sessionId,data.taskId,{...data.taskInfo})
      }
      /*if(data.content){
        appStore.addThought(data.sessionId,data.taskId,data.stepIndex,data.content)
      }*/
    }else{
      appStore.planThinkFinal(data.sessionId,data.taskId,false)
      // 更新计划思考内容
      /*if(data.content){
        appStore.addThinkThought(data.sessionId,data.taskId,data.content)
      }*/
    }
    // 确保session有tasks属性
    
  })

  wsStore.onPlanStart((data) => {
    console.log('Plan started:', data)
    if(data.stepIndex>0){
      appStore.stepThinkFinal(data.sessionId,data.taskId,data.stepIndex,false)
    }else{
      appStore.planThinkFinal(data.sessionId,data.taskId,false)
    }
    appStore.updateSessionTitle(data.sessionId,data.title)
    // 确保session有tasks属性
    
  })

  wsStore.onPlanFinal((data) => {
    console.log('Plan final:', data)
    appStore.addTask(data.sessionId,data.taskId,{plan:data.plan,planThinking:false})
    // 确保session有tasks属性
  })

  wsStore.onStepStart((data) => {
    console.log('Step started:', data)
    if(data.stepInfo){
      appStore.addStep(data.sessionId,data.taskId,data.stepIndex,data.stepInfo)
    }
    // 确保session有tasks属性
  })

  wsStore.onStepEnd((data) => {
    console.log('Step ended:', data)
    // 找到对应的助手消息，更新步骤状态
    if(data.stepInfo){
      appStore.addStep(data.sessionId,data.taskId,data.stepIndex,data.stepInfo)
    }
  })

  wsStore.onTaskFailed((data) => {
    console.log('Task failed:', data)
    appStore.setCurrentTask(data.sessionId, null)
    appStore.updateTaskStatus(data.sessionId, data.taskId, 'failed')
    // 更新会话的isTaskRunning状态
    const session = appStore.sessions.find(s => s.sessionId === data.sessionId)
    if (session) {
      session.isTaskRunning = false
    }
    // 找到对应的助手消息，添加失败信息
    if(data.taskInfo){
      // 确保时间戳是数字格式
      const taskData = {
        ...data.taskInfo,
        status: 'failed',
        createdAt: typeof data.taskInfo.createdAt === 'number' ? data.taskInfo.createdAt : Date.now(),
        updatedAt: typeof data.taskInfo.updatedAt === 'number' ? data.taskInfo.updatedAt : Date.now()
      }
      appStore.addTask(data.sessionId,data.taskId,taskData)
    }
  })
}

async function refreshSessionsList() {
  console.log('[App] Refreshing sessions list...')
  try {
    const currentWorkspace = workspaceStore.currentWorkspace
    let newSessions = []
    
    if (currentWorkspace?.workspace) {
      console.log('[App] Loading sessions for workspace:', currentWorkspace.workspace)
      const result = await apiService.client.getWorkspaceSessions(currentWorkspace.workspace)
      newSessions = result.data.sessions || []
    } else {
      console.log('[App] No workspace initialized, loading all sessions')
      const result = await apiService.client.getSessions()
      newSessions = result.data?.sessions || []
    }
    
    // 保存所有会话的任务数据
    const existingSessions = appStore.sessions
    const sessionTasksMap = new Map()
    existingSessions.forEach(session => {
      sessionTasksMap.set(session.sessionId, session.tasks || [])
    })
    
    // 直接使用后端返回的会话数据格式（已经是驼峰命名）
    const formattedNewSessions = (newSessions || []).map((session: any) => ({
      sessionId: session.sessionId,
      title: session.title,
      taskCount: session.taskCount,
      firstMessage: session.firstMessage,
      createdAt: session.createdAt,
      updatedAt: session.updatedAt,
      hasCheckpoint: session.hasCheckpoint
    }))
    
    // 追加到原本的会话列表中，去重
    const existingSessionIds = new Set(existingSessions.map(s => s.sessionId))
    const uniqueNewSessions = formattedNewSessions.filter(session => !existingSessionIds.has(session.sessionId))
    const updatedSessions = [...existingSessions, ...uniqueNewSessions]
    
    // 保留原有会话的任务数据
    const finalSessions = updatedSessions.map(session => {
      if (sessionTasksMap.has(session.sessionId)) {
        return {
          ...session,
          tasks: sessionTasksMap.get(session.sessionId)
        }
      }
      return session
    })
    
    appStore.setSessions(finalSessions)
    console.log('[App] Sessions list refreshed:', finalSessions.length, 'sessions')
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
