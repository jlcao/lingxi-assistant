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

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()

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
          console.log('[App] Loaded sessions:', sessions)
          sessions = sessions.sessions || []
        } else {
          console.log('[App] No workspace initialized, loading all sessions')
          sessions = await window.electronAPI.api.getSessions()
          console.log('[App] Loaded sessions:', sessions)
          sessions = sessions || []
        }

        if (sessions && sessions.length > 0) {
          appStore.setSessions(sessions)
          appStore.setCurrentSession(sessions[0].sessionId)
          
          // 建立 WebSocket 连接
          if (window.electronAPI?.ws) {
            await window.electronAPI.ws.connect(sessions[0].sessionId)
          }
        } else {
          // 没有会话时，创建一个新会话
          try {
            const sessionData = await window.electronAPI.api.createSession()
            if (sessionData && (sessionData.session_id || sessionData.sessionId)) {
              const session = {
                sessionId: sessionData.session_id || sessionData.sessionId,
                title: sessionData.first_message || sessionData.firstMessage || '新会话',
                tasks: [],
                totalTokens: 0,
                userName: sessionData.user_name || sessionData.userName || '新用户',
                createdAt: Date.now(),
                updatedAt: Date.now()
              }
              appStore.setSessions([session])
              appStore.setCurrentSession(session.sessionId)
              
              // 建立 WebSocket 连接
              if (window.electronAPI?.ws) {
                await window.electronAPI.ws.connect(session.sessionId)
              }
            }
          } catch (error) {
            console.error('Failed to create session:', error)
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
      if(data.taskInfo){
        // 确保task对象包含planThinking和planThinkingContent属性
        const taskData = {
          ...data.taskInfo,
          planThinking: false,
          planThinkingContent: '',
          steps: data.taskInfo.steps || []
        }
        appStore.addTask(data.sessionId,data.taskId,taskData)
      }
      
    })

    window.electronAPI.ws.onTaskEnd((data) => {
      console.log('Task ended:', data)
      // 更新助手消息的内容
      if (data.result && data.taskInfo) {
        appStore.addTask(data.sessionId,data.taskId,data.taskInfo)
      }

      // 任务结束后刷新工作区目录
      workspaceStore.refreshDirectoryTree()

      // 任务结束后刷新历史会话列表，重新加载会话名称
      refreshSessionsList()
    })

    window.electronAPI.ws.onThinkStart((data) => {
      console.log('Think started:', data)
      // 找到对应的助手消息，添加思考开始标记
      if(data.taskInfo){
        appStore.addTask(data.sessionId,data.taskId,{...data.taskInfo,planThinking:true,planThinkingContent:''})
      }
      if(data.stepIndex && data.stepInfo){
        appStore.addStep(data.sessionId,data.taskId,data.stepIndex,{...data.stepInfo,isThinking:true,thought:''})
      }
    })

    window.electronAPI.ws.onThinkStream((data) => {
      //console.log('Think stream:', data)
      if(data.content && data.stepIndex>0){
        appStore.addThought(data.sessionId,data.taskId,data.stepIndex,data.content)
      }else{
        appStore.addThinkThought(data.sessionId,data.taskId,data.content)
      }
    })

    window.electronAPI.ws.onThinkFinal((data) => {
      console.log('Think final:', data)
      // 找到对应的助手消息，完成思考标记并更新步骤的思考内容
      if(data.stepIndex>0){
        appStore.stepThinkFinal(data.sessionId,data.taskId,data.stepIndex,false)
        // 更新步骤的思考内容
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

    window.electronAPI.ws.onPlanStart((data) => {
      console.log('Plan started:', data)
      if(data.stepIndex>0){
        appStore.stepThinkFinal(data.sessionId,data.taskId,data.stepIndex,false)
      }else{
        appStore.planThinkFinal(data.sessionId,data.taskId,false)
      }
      // 确保session有tasks属性
      
    })

    window.electronAPI.ws.onPlanFinal((data) => {
      console.log('Plan final:', data)
      appStore.addTask(data.sessionId,data.taskId,{plan:data.plan,planThinking:false})
      // 确保session有tasks属性
    })

    window.electronAPI.ws.onStepStart((data) => {
      console.log('Step started:', data)
      if(data.stepInfo){
        appStore.addStep(data.sessionId,data.taskId,data.stepIndex,data.stepInfo)
      }
      // 确保session有tasks属性
    })

    window.electronAPI.ws.onStepEnd((data) => {
      console.log('Step ended:', data)
      // 找到对应的助手消息，更新步骤状态
      if(data.stepInfo){
        appStore.addStep(data.sessionId,data.taskId,data.stepIndex,data.stepInfo)
      }
    })

    window.electronAPI.ws.onTaskFailed((data) => {
      console.log('Task failed:', data)
      // 找到对应的助手消息，添加失败信息
      if(data.taskInfo){
        appStore.addTask(data.sessionId,data.taskId,data.taskInfo)
      }
    })
  }
}

async function refreshSessionsList() {
  console.log('[App] Refreshing sessions list...')
  try {
    const currentWorkspace = workspaceStore.currentWorkspace
    let newSessions = []
    
    if (currentWorkspace?.workspace) {
      console.log('[App] Loading sessions for workspace:', currentWorkspace.workspace)
      const result = await window.electronAPI.api.getWorkspaceSessions(currentWorkspace.workspace)
      newSessions = result.sessions || []
    } else {
      console.log('[App] No workspace initialized, loading all sessions')
      newSessions = await window.electronAPI.api.getSessions()
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
