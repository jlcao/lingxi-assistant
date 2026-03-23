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
        <span class="header-count">{{ filteredSessions.length }}</span>
      </div>
      <div v-if="filteredSessions.length === 0" class="empty-state">
        <el-icon class="empty-icon"><Document /></el-icon>
        <div class="empty-text">暂无会话历史</div>
        <div class="empty-hint">点击上方"新建会话"开始对话</div>
      </div>
      <div
        v-else
        v-for="session in filteredSessions"
        :key="session.id"
        class="history-chat-item"
        :class="{ active: session.id === currentSessionId }"
        @click="session.id && handleSelectSession(session.id)"
      >
        <div class="session-avatar">
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <div class="session-content">
          <div class="session-name" :title="session.name">
            {{ session.name }}
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

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const { sessions, currentSessionId } = storeToRefs(appStore)

const filteredSessions = computed(() => {
  return sessions.value.filter(session => session && session.id)
})

async function handleSelectWorkspace() {
  try {
    const selectedPath = await window.electronAPI.file.selectDirectory()
    if (selectedPath) {
      // 验证工作目录
      const validationResult = await window.electronAPI.workspace.validate(selectedPath)
      
      // 检查验证结果
      if (!validationResult) {
        throw new Error('验证返回数据为空')
      }
      
      if (validationResult.valid) {
        // 调用后台切换工作区接口
        const switchResult = await window.electronAPI.workspace.switch(selectedPath, false)
        
        if (switchResult && switchResult.success) {
          // 重新加载工作区信息
          await workspaceStore.loadCurrentWorkspace()
          
          // 重新加载会话列表（使用工作目录特定的 API）
          const sessionsResult = await window.electronAPI.api.getWorkspaceSessions(selectedPath)
          const sessions = sessionsResult.sessions || []
          const formattedSessions = (sessions || []).map((session: any) => ({
            id: session.session_id || session.id,
            name: session.title || session.name || '新会话',
            createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
            updatedAt: session.updated_at ? new Date(session.updated_at).getTime() : (session.created_at ? new Date(session.created_at).getTime() : Date.now())
          }))
          
          appStore.setSessions(formattedSessions)
          
          // 如果有会话，选择第一个；否则清空当前会话
          if (formattedSessions && formattedSessions.length > 0) {
            appStore.setCurrentSession(formattedSessions[0].id)
          } else {
            appStore.setCurrentSession(null)
            appStore.setTurns([])
          }
          
          alert('工作区切换成功！')
        } else {
          throw new Error(switchResult?.error || '切换失败')
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
    let sessionId: string
    
    // 检查 Electron 环境是否可用
    if (!window.electronAPI || !window.electronAPI.api) {
      console.warn('Electron API is not available, running in browser mode')
      // 在浏览器模式下，生成一个本地会话ID
      sessionId = `local_${Date.now()}`
    } else {
      const sessionData = await window.electronAPI.api.createSession()
      sessionId = sessionData.session_id
      // 重新加载会话列表以获取后端生成的正确会话名称和时间戳
      const currentWorkspace = workspaceStore.currentWorkspace
      let sessionsResult
      if (currentWorkspace?.workspace) {
        sessionsResult = await window.electronAPI.api.getWorkspaceSessions(currentWorkspace.workspace)
      } else {
        sessionsResult = await window.electronAPI.api.getSessions()
      }
      const allSessions = sessionsResult.sessions || []
      const newSession = allSessions.find(s => s.session_id === sessionId)
      if (newSession) {
        const session = {
          id: newSession.session_id,
          name: newSession.title || newSession.name || '新会话',
          createdAt: newSession.created_at ? new Date(newSession.created_at).getTime() : Date.now(),
          updatedAt: newSession.updated_at ? new Date(newSession.updated_at).getTime() : Date.now()
        }
        appStore.setSessions([...sessions.value, session])
        await handleSelectSession(session.id)
        return
      }
    }
    
    // 生成有意义的会话名称，比如会话1、会话2等
    const sessionCount = sessions.value.length + 1
    const session = {
      id: sessionId,
      name: `会话${sessionCount}`,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    appStore.setSessions([...sessions.value, session])
    await handleSelectSession(session.id)
  } catch (error) {
    console.error('Failed to create session:', error)
    // 在浏览器模式下，即使API调用失败也创建本地会话
    if (!window.electronAPI || !window.electronAPI.api) {
      const sessionId = `local_${Date.now()}`
      const sessionCount = sessions.value.length + 1
      const session = {
        id: sessionId,
        name: `会话${sessionCount}`,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }
      appStore.setSessions([...sessions.value, session])
      await handleSelectSession(session.id)
    } else {
      alert('创建会话失败：' + (error as Error).message)
    }
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
    // 检查 Electron 环境是否可用
    if (!window.electronAPI || !window.electronAPI.api) {
      console.warn('Electron API is not available, running in browser mode')
      // 在浏览器模式下，使用空的消息列表
      appStore.setTurns(sessionId, [])
      return
    }
    
    console.log('Calling getSessionInfo for sessionId:', sessionId)
    const sessionInfo = await window.electronAPI.api.getSessionInfo(sessionId)
    console.log('Received sessionInfo:', sessionInfo)
    
    const turns: any[] = []
    if (sessionInfo.task_list && Array.isArray(sessionInfo.task_list)) {
      sessionInfo.task_list.forEach((task: any, taskIndex: number) => {
        // 添加用户消息
        if (task.user_input) {
          const userTime = task.created_at ? new Date(task.created_at).getTime() : Date.now()
          turns.push({
            id: `${sessionId}_${taskIndex}_user`,
            role: 'user',
            content: task.user_input,
            time: userTime,
            timestamp: userTime
          })
        }
        
        // 添加助手消息
        const assistantTime = task.updated_at ? new Date(task.updated_at).getTime() : Date.now()
        turns.push({
          id: `${sessionId}_${taskIndex}_assistant`,
          role: 'assistant',
          content: task.result || '',
          time: assistantTime,
          timestamp: assistantTime,
          steps: task.steps || [],
          plan: task.plan || null,
          executionId: task.task_id || null,
          status: task.status || null,
          isStreaming: false
        })
      })
    }
    
    appStore.setTurns(sessionId, turns)
  } catch (error: any) {
    console.error('Failed to load session info:', error)
    // 在浏览器模式下，即使API调用失败也设置空的消息列表
    if (!window.electronAPI || !window.electronAPI.api) {
      appStore.setTurns(sessionId, [])
    } else if (error?.response?.status === 404 || error?.message?.includes('不存在')) {
      console.log('Session does not exist, removing from list')
      const updatedSessions = sessions.value.filter(s => s.id !== sessionId)
      appStore.setSessions(updatedSessions)
      
      if (updatedSessions.length > 0) {
        appStore.setCurrentSession(updatedSessions[0].id)
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
        inputValue: session.name,
        inputPattern: /^.{1,50}$/,
        inputErrorMessage: '名称长度为 1-50 个字符'
      })
      
      if (value) {
        if (window.electronAPI.api.updateSessionName) {
          await window.electronAPI.api.updateSessionName(session.id, value)
        }
        const updatedSessions = sessions.value.map(s =>
          s.id === session.id ? { ...s, name: value, updatedAt: Date.now() } : s
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
      
      if (window.electronAPI.api.deleteSession) {
        await window.electronAPI.api.deleteSession(session.id)
      }
      const updatedSessions = sessions.value.filter(s => s.id !== session.id)
      appStore.setSessions(updatedSessions)
      
      if (currentSessionId.value === session.id) {
        appStore.setCurrentSession(updatedSessions[0]?.id || null)
        appStore.setTurns([])
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
