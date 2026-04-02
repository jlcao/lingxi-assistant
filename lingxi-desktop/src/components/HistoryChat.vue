<template>
  <div class="history-chat">
    <div class="history-chat-workspace">
      <div class="workspace-info">
        <el-icon class="workspace-icon" @click="handleSelectWorkspace"><FolderOpened /></el-icon>
        <div class="workspace-details">
          <div class="workspace-label">当前工作区</div>
          <div class="workspace-path" :title="workspaceStore.workspacePath || '未设置'">
            {{ workspaceStore.workspacePath || '未设置工作区路径' }}
          </div>
        </div>
      </div>
      <el-button
        type="primary"
        size="small"
        class="new-session-btn"
        @click="handleNewSession"
      >
        <el-icon class="btn-icon"><Plus /></el-icon>
        新建会话
      </el-button>
    </div>
    <div class="history-chat-list">
      <div class="history-chat-list-header">
        <span class="header-title">会话历史</span>
        <span class="header-count">{{ sessions.length }}</span>
      </div>
      <div v-if="sessions.length === 0" class="empty-state">
        <el-icon class="empty-icon"><Document /></el-icon>
        <div class="empty-text">暂无会话历史</div>
        <div class="empty-hint">点击上方"新建会话"开始对话</div>
      </div>
      <div
        v-else
        v-for="session in sessions"
        :key="session.sessionId"
        class="history-chat-item"
        :class="{ active: session.sessionId === currentSessionId }"
        @click="session.sessionId && handleSelectSession(session.sessionId)"  
      >
        <div class="session-avatar">
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <div class="session-content">
          <div class="session-name" :title="session.title">
            {{ session.title }}
          </div>
          <div class="session-meta">
            <span class="session-time">{{ formatSessionTime(session.updatedAt || session.createdAt) }}</span>
          </div>
        </div>
        <div class="session-actions">
          <el-dropdown @command="(command) => handleCommand(command, session)" trigger="click">
            <el-button link size="small" class="action-button">
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename">
                  <el-icon class="menu-icon"><Edit /></el-icon>
                  <span>重命名</span>
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <el-icon class="menu-icon danger-icon"><Delete /></el-icon>
                  <span class="danger-text">删除会话</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { useWorkspaceStore } from '@/stores/workspace'
import { ChatDotRound, Delete, Document, Edit, FolderOpened, MoreFilled, Plus } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { apiService } from '@/api/apiService'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const { sessions, currentSessionId } = storeToRefs(appStore)

const filteredSessions = computed(() => {
  return sessions.value.filter(session => session && session.sessionId)
})

async function handleSelectWorkspace() {
  try {
    const selectedPath = await window.electronAPI.file.selectDirectory()
    if (selectedPath) {
      // 验证工作目录
      const validationResult = await apiService.client.validateWorkspace(selectedPath)
      
      // 检查验证结果
      if (!validationResult) {
        throw new Error('验证返回数据为空')
      }
      
      if (validationResult.code === 0) {
        // 调用后台切换工作区接口
        const switchResult = await apiService.client.switchWorkspace(selectedPath, false)
        
        if (switchResult.code === 0) {
          // 重新加载工作区信息
          await workspaceStore.loadCurrentWorkspace()
          
          // 重新加载会话列表（使用工作目录特定的 API）
          const sessionsResult = await apiService.client.getWorkspaceSessions(selectedPath)
          console.log('获取到的会话列表:', sessionsResult)
          
          const sessions = sessionsResult.data?.sessions || []
          const formattedSessions = (sessions || []).map((session: any) => ({
            sessionId: session.sessionId || session.id,
            title: session.title || session.name || '新会话',
            userName: session.user_name || '用户',
            tasks: [],
            totalTokens: 0,
            createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
            updatedAt: session.updated_at ? new Date(session.updated_at).getTime() : Date.now()
          }))
          
          appStore.setSessions(formattedSessions)
          
          // 如果有会话，选择第一个；否则清空当前会话
          if (formattedSessions && formattedSessions.length > 0) {
            appStore.setCurrentSession(formattedSessions[0].sessionId)
          } else {
            appStore.setCurrentSession(null)
            appStore.setSessions([])
          }
          
          alert('工作区切换成功！')
        } else {
          throw new Error(switchResult.message || '切换失败')
        }
      } else {
        throw new Error(validationResult.message || '工作目录无效')
      }
    }
  } catch (error) {
    console.error('Failed to select workspace:', error)
    alert('切换工作区失败：' + (error as Error).message)
  }
}

function formatSessionTime(timestamp?: number): string {
  if (!timestamp) return '刚刚'
  const now = new Date()
  const sessionTime = new Date(timestamp)
  const diff = now.getTime() - sessionTime.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  return sessionTime.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

async function handleNewSession() {
  try {
    const sessionData = await apiService.client.createSession()
    const sessionDataPayload = sessionData.data || sessionData
    
    const sessionId = sessionDataPayload.session_id || sessionDataPayload.sessionId
    if (!sessionDataPayload || !sessionId) {
      console.error('Invalid session data received:', sessionData)
      return
    }
    
    const session = {
      sessionId: sessionId,
      title: sessionDataPayload.first_message || sessionDataPayload.firstMessage || '新会话',
      userName: sessionDataPayload.user_name || sessionDataPayload.userName || '用户',
      tasks: [],
      totalTokens: 0,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    appStore.setSessions([...sessions.value, session])
    await handleSelectSession(session.sessionId)
  } catch (error) {
    console.error('Failed to create session:', error)
  }
}

async function handleSelectSession(sessionId: string) {
  console.log('handleSelectSession called with sessionId:', sessionId)  
  if (!sessionId) {
    console.error('Invalid sessionId')
    return
  }
  
  appStore.setCurrentSession(sessionId)  
  try {
    console.log('Calling getSessionInfo for sessionId:', sessionId)
    const sessionInfo = await apiService.client.getSession(sessionId)
    const sessionInfoPayload = sessionInfo.data || sessionInfo
    console.log('Received sessionInfo:', sessionInfo)
    
    // 更新会话列表中的对应会话，保留前端已有的任务数据（特别是正在处理中的任务状态）
    const updatedSessions = sessions.value.map(session => {
      debugger
      if (session.sessionId === sessionId) {
        // 如果前端已经有任务数据，保留它（包含实时状态）
        // 只有当前端没有任务数据时，才使用后端返回的任务数据
        const existingTasks = session.tasks || []
        const backendTasks = sessionInfoPayload.tasks || []
        return { 
          ...session, 
          tasks: existingTasks.length > 0 ? existingTasks : backendTasks 
        }
      }
      return session
    })
    
    appStore.setSessions(updatedSessions)
  } catch (error: any) {
    console.error('Failed to load session info:', error)
    if (error?.response?.status === 404 || error?.message?.includes('不存在')) {
      console.log('Session does not exist, removing from list')
      const updatedSessions = sessions.value.filter(s => s.sessionId !== sessionId)
      appStore.setSessions(updatedSessions)
      
      if (updatedSessions.length > 0) {
        appStore.setCurrentSession(updatedSessions[0].sessionId)
      } else {
        appStore.setCurrentSession(null)
      }
    }
  }
}

async function handleCommand(command: string, session: any) {
  if (command === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt('请输入新名称', '重命名会话', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: session.title,
        inputPattern: /^.{1,50}$/,
        inputErrorMessage: '名称长度为 1-50 个字符'
      })
      
      if (value) {
        await apiService.client.updateSessionName(session.sessionId, value)
        const updatedSessions = sessions.value.map(s =>
          s.sessionId === session.sessionId ? { ...s, title: value, updatedAt: Date.now() } : s
        )
        appStore.setSessions(updatedSessions)
      }
    } catch {
      console.log('Rename cancelled')
    }
  } else if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        '确定要删除此会话吗？删除后将无法恢复。',
        '确认删除',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        }
      )
      
      await apiService.client.deleteSession(session.sessionId)
      const updatedSessions = sessions.value.filter(s => s.sessionId !== session.sessionId)
      appStore.setSessions(updatedSessions)
      
      if (currentSessionId.value === session.sessionId) {
        appStore.setCurrentSession(updatedSessions[0]?.sessionId || null)
      }
    } catch {
      console.log('Delete cancelled')
    }
  }
}
</script>

<style scoped lang="scss">
.history-chat {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border-right: 1px solid #e8e8e8;
}

.history-chat-workspace {
  padding: 16px;
  border-bottom: 1px solid #e8e8e8;
}

.workspace-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.workspace-icon {
  font-size: 18px;
  color: #1890ff;
  cursor: pointer;
  transition: color 0.2s;

  &:hover {
    color: #40a9ff;
  }
}

.workspace-details {
  flex: 1;
  min-width: 0;
}

.workspace-label {
  font-size: 11px;
  color: #999999;
  margin-bottom: 2px;
}

.workspace-path {
  font-size: 12px;
  color: #666666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.new-session-btn {
  width: 100%;
  height: 32px;
  border-radius: 4px;
  font-size: 13px;
}

.btn-icon {
  margin-right: 4px;
}

.history-chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 3px;

    &:hover {
      background: #b8c2cc;
    }
  }
}

.history-chat-list-header {
  padding: 12px 12px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-size: 13px;
  font-weight: 500;
  color: #333333;
}

.header-count {
  font-size: 12px;
  color: #999999;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #999999;
}

.empty-icon {
  font-size: 48px;
  color: #d1d5db;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
  color: #666666;
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 12px;
  color: #999999;
}

.history-chat-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s;

  &:hover {
    background-color: #f5f5f5;
  }

  &.active {
    background-color: #e6f7ff;

    .session-name {
      color: #1890ff;
      font-weight: 500;
    }
  }
}

.session-avatar {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  background-color: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  flex-shrink: 0;

  .el-icon {
    font-size: 16px;
    color: #1890ff;
  }
}

.session-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-name {
  font-size: 13px;
  color: #333333;
  line-height: 18px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.2s;
}

.session-meta {
  display: flex;
  align-items: center;
}

.session-time {
  font-size: 11px;
  color: #999999;
}

.session-actions {
  margin-left: 8px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.history-chat-item:hover .session-actions {
  opacity: 1;
}

.action-button {
  padding: 2px;
  width: 24px;
  height: 24px;

  .el-icon {
    font-size: 14px;
    color: #666666;
  }
}

.menu-icon {
  margin-right: 6px;
  font-size: 14px;
  color: #666666;

  &.danger-icon {
    color: #f56c6c;
  }
}

.danger-text {
  color: #f56c6c;
}
</style>
