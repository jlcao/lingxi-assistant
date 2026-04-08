<template>
  <div class="chat-core">
    <div class="chat-core-header">
      <div class="chat-core-title">
        {{ currentSessionName }}
      </div>
      <div class="chat-core-actions">
        <el-dropdown @command="handleMoreCommand">
          <el-button
            size="small"
            text
          >
            ...
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">
                <el-icon class="mr-2">
                  <Edit />
                </el-icon>
                重命名会话
              </el-dropdown-item>
              <el-dropdown-item command="clear">
                <el-icon class="mr-2">
                  <Delete />
                </el-icon>
                清除历史
              </el-dropdown-item>
              <el-dropdown-item
                command="delete"
                type="danger"
              >
                <el-icon class="mr-2">
                  <Delete />
                </el-icon>
                删除会话
              </el-dropdown-item>
              <el-dropdown-item command="export">
                <el-icon class="mr-2">
                  <Download />
                </el-icon>
                导出会话
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    <div class="chat-core-content">
      <MessageList />
    </div>
    <div
      class="chat-core-input" 
      :class="{ 'dragging': isDragging }"
      @dragover.prevent="handleDragOver"
      @dragleave="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        placeholder="随便问点什么..."
        resize="none"
        class="chat-input"
        @keydown="handleKeyDown"
      />
      <div class="chat-core-input-actions">
        <el-dropdown @command="handleAddCommand">
          <el-button
            :icon="Plus"
            size="small"
            text
          />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="upload">
                <el-icon class="mr-2">
                  <Upload />
                </el-icon>
                上传文件
              </el-dropdown-item>
              <el-dropdown-item command="image">
                <el-icon class="mr-2">
                  <Picture />
                </el-icon>
                添加图片
              </el-dropdown-item>
              <el-dropdown-item command="code">
                <el-icon class="mr-2">
                  <View />
                </el-icon>
                代码块
              </el-dropdown-item>
              <el-dropdown-item command="emoji">
                表情 😊
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button
          :icon="Upload"
          size="small"
          text
          @click="handleUpload"
        />
        <div class="thinking-mode-switch">
          <span class="switch-label">思考模式</span>
          <el-switch
            v-model="thinkingMode"
            size="small"
          />
        </div>
        <el-button
          :type="isTaskRunning ? 'danger' : 'primary'"
          size="small"
          :loading="isStopping"
          :disabled="isStopping"
          @click="handleButtonClick"
        >
          {{ isTaskRunning ? '终止' : '发送' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppStore } from '../stores/app'
import { useWsStore } from '../stores/wsStore'
import { apiService } from '../api/apiService'
import { Plus, Upload, Edit, Delete, Download, Picture, View, Star } from '@element-plus/icons-vue'
import MessageList from './chat/MessageList.vue'
import { ElMessageBox, ElSwitch } from 'element-plus'


const appStore = useAppStore()
const wsStore = useWsStore()

const inputText = ref('')
const mode = ref('plan')
const model = ref('gim4.7')
const defaultOption = ref('default')
const isDragging = ref(false)
const thinkingMode = ref(false)
const isStopping = ref(false)

const currentSession = computed(() => {
  return appStore.sessions.find(s => s.sessionId === appStore.currentSessionId)
})

const isTaskRunning = computed(() => {
  return currentSession.value?.isTaskRunning || false
})

const currentTaskId = computed(() => {
  return currentSession.value?.currentTaskId || ''
})

const currentSessionName = computed(() => {
  const session = appStore.sessions.find(s => s.sessionId === appStore.currentSessionId)
  return session ? session.title : '新会话'
})

function handleMoreCommand(command: string) {
  switch (command) {
    case 'rename':
      handleRenameSession()
      break
    case 'clear':
      handleClearHistory()
      break
    case 'delete':
      handleDeleteSession()
      break
    case 'export':
      handleExportSession()
      break
  }
}

function handleAddCommand(command: string) {
  switch (command) {
    case 'upload':
      handleUpload()
      break
    case 'image':
      handleAddImage()
      break
    case 'code':
      handleAddCodeBlock()
      break
    case 'emoji':
      handleAddEmoji()
      break
  }
}

async function handleRenameSession() {
  if (!appStore.currentSessionId) return

  try {
    const { value } = await ElMessageBox.prompt('请输入新会话名称', '重命名会话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: currentSessionName.value
    })

    if (value) {
      // 调用后端 API 更新会话名称
      await apiService.client.updateSessionName(appStore.currentSessionId, value)
      // 更新前端会话列表
      const updatedSessions = appStore.sessions.map(s =>
        s.sessionId === appStore.currentSessionId ? { ...s, title: value } : s
      )
      appStore.setSessions(updatedSessions)
    }
  } catch {
    console.log('Rename cancelled')
  }
}

async function handleClearHistory() {
  if (!appStore.currentSessionId) return

  try {
    await ElMessageBox.confirm('确定要清除当前会话的历史记录吗？', '确认清除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    // 调用后端 API 清除会话历史
    await apiService.client.clearSessionHistory(appStore.currentSessionId)
    // 清空前端历史记录
    const updatedSessions = appStore.sessions.map(s =>
      s.sessionId === appStore.currentSessionId ? { ...s, tasks: [] } : s
    )
    appStore.setSessions(updatedSessions)
  } catch {
    console.log('Clear cancelled')
  }
}

async function handleDeleteSession() {
  if (!appStore.currentSessionId) return

  try {
    await ElMessageBox.confirm('确定要删除当前会话吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'danger'
    })

    // 调用后端 API 删除会话
    await apiService.client.deleteSession(appStore.currentSessionId)
    // 更新前端会话列表
    const updatedSessions = appStore.sessions.filter(
      s => s.sessionId !== appStore.currentSessionId
    )
    appStore.setSessions(updatedSessions)
    // 切换到第一个会话
    if (updatedSessions.length > 0) {
      appStore.setCurrentSession(updatedSessions[0].sessionId)
    }
  } catch {
    console.log('Delete cancelled')
  }
}

function handleExportSession() {
  console.log('Export session')
  // 实现会话导出功能
}

function handleAddImage() {
  console.log('Add image')
  // 实现添加图片功能
}

function handleAddCodeBlock() {
  // 在输入框中添加代码块标记
  inputText.value += '\n```\n\n```\n'
}

function handleAddEmoji() {
  console.log('Add emoji')
  // 实现添加表情功能
}

function handleUpload() {
  window.electronAPI.file.selectFiles()
}

function handleButtonClick() {
  if (isTaskRunning.value) {
    handleStopTask()
  } else {
    handleSend()
  }
}

async function handleStopTask() {
  if (currentTaskId.value && appStore.currentSessionId) {
    try {
      // 设置停止中状态，显示加载效果
      isStopping.value = true
      
      // 调用cancel接口
      const response = await apiService.client.cancelTask(currentTaskId.value)
      
      // 接口返回成功后，更新状态
      if (response.code === 0) {
        // 更新会话状态
        const session = appStore.sessions.find(s => s.sessionId === appStore.currentSessionId)
        if (session) {
          session.isTaskRunning = false
          session.currentTaskId = null
        }
        
        // 更新任务状态为stopped
        appStore.updateTaskStatus(appStore.currentSessionId, currentTaskId.value, 'stopped')
        
        // 查找并更新任务对象
        const task = session?.tasks?.find(t => t.taskId === currentTaskId.value)
        if (task) {
          task.status = 'stopped'
          task.result = '任务已被用户终止'
        }
      }
    } catch (error) {
      console.error('Failed to stop task:', error)
    } finally {
      // 无论成功失败，都关闭加载状态
      isStopping.value = false
    }
  }
}

async function handleSend() {
  if (inputText.value.trim()) {
    const userMessage = inputText.value.trim()

    // 如果没有当前会话，创建一个新会话
    if (!appStore.currentSessionId) {
          try {
            const result = await apiService.client.createSession({ user_name: '新会话' })
            if (result.data && result.data.session_id) {
              appStore.setCurrentSession(result.data.session_id)
              appStore.setSessions([...appStore.sessions, {
                sessionId: result.data.session_id,
                title: result.data.first_message || '新会话',
                userName: '',
                tasks: [],
                totalTokens: 0,
                createdAt: Date.now(),
                updatedAt: Date.now(),
                currentTaskId: null,
                isTaskRunning: false
              }])
            } else {
              throw new Error('创建会话失败')
            }
          } catch (error) {
            console.error('Failed to create session:', error)
            return
          }
        }

    inputText.value = ''

    // 通过 WebSocket 发送消息到后端
    if (appStore.currentSessionId) {
      try {
        wsStore.sendMessage(userMessage, appStore.currentSessionId)
      } catch (error) {
        console.error('Failed to send message:', error)
      }
    }
  }
}

function handleKeyDown(event: KeyboardEvent) {
  // 回车发送，Shift+回车换行
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function handleDragOver(event: DragEvent) {
  isDragging.value = true
}

function handleDragLeave(event: DragEvent) {
  isDragging.value = false
}

function handleDrop(event: DragEvent) {
  isDragging.value = false
  
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) {
    return
  }

  // 处理拖拽的文件
  handleFiles(Array.from(files))
}

function handleFiles(files: File[]) {
  files.forEach(file => {
    console.log('拖拽文件:', file.name, file.size, file.type)
    
    // 根据文件类型处理
    if (file.type.startsWith('image/')) {
      // 处理图片文件
      handleImageFile(file)
    } else if (file.type.startsWith('text/') || file.name.endsWith('.md') || file.name.endsWith('.txt')) {
      // 处理文本文件
      handleTextFile(file)
    } else {
      // 处理其他文件
      handleOtherFile(file)
    }
  })
}

function handleImageFile(file: File) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target?.result as string
    // 在输入框中插入图片标记
    inputText.value += `\n![${file.name}](${result})\n`
  }
  reader.readAsDataURL(file)
}

function handleTextFile(file: File) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target?.result as string
    // 在输入框中插入文件内容和文件名
    inputText.value += `\n\`\`\`\n文件: ${file.name}\n${result}\n\`\`\`\n`
  }
  reader.readAsText(file)
}

function handleOtherFile(file: File) {
  // 在输入框中插入文件名
  inputText.value += `\n📎 ${file.name} (${(file.size / 1024).toFixed(2)} KB)\n`
}

function handleMinimize() {
  window.electronAPI.window.minimize()
}

function handleSettings() {
  console.log('Open settings')
}
</script>

<style scoped lang="scss">
.chat-core {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
}

.chat-core-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
}

.chat-core-title {
  font-size: 14px;
  font-weight: 500;
  color: #333333;
}

.chat-core-actions {
  .el-button {
    padding: 0;
  }
}

.chat-core-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.chat-message {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;

  &.user {
    align-items: flex-end;
  }
}

.chat-message-content {
  max-width: 80%;
  padding: 12px;
  background-color: #f5f5f5;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  color: #333333;

  .chat-message.user & {
    background-color: #e6f7ff;
  }
}

.chat-message-button {
  margin-top: 8px;
  align-self: flex-start;
  border-radius: 16px;
}

.chat-core-input {
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
  position: relative;
  transition: all 0.3s ease;

  &.dragging {
    background-color: #e6f7ff;
    border-color: #1890ff;
    
    &::after {
      content: '释放以上传文件';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background-color: rgba(24, 144, 255, 0.9);
      color: white;
      padding: 16px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      z-index: 10;
      pointer-events: none;
    }
  }
}

.chat-input {
  margin-bottom: 8px;
  border-radius: 4px;
}

.chat-core-input-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.thinking-mode-switch {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: auto;
  
  .switch-label {
    font-size: 12px;
    color: #666666;
  }
}

.chat-core-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-top: 1px solid #e8e8e8;
  background-color: #fafafa;
}

.chat-core-footer-left {
  display: flex;
  gap: 8px;
}

.footer-select {
  width: 100px;
}

.chat-core-footer-right {
  display: flex;
  gap: 8px;

  .el-button {
    padding: 0;
    width: 24px;
    height: 24px;
  }
}
</style>
