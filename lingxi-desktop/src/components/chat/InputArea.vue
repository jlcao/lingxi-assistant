<template>
  <div class="input-area">
    <div class="input-area-toolbar">
      <el-button
        :icon="Upload"
        size="small"
        text
        @click="handleUpload"
      >
        上传文件
      </el-button>
      <el-button
        :icon="Microphone"
        size="small"
        text
        @click="handleVoice"
      >
        语音输入
      </el-button>
    </div>
    <div class="input-area-main">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="3"
        placeholder="输入您的任务或问题..."
        resize="none"
        @keydown.ctrl.enter="handleSend"
      />
      <el-button
        type="primary"
        :icon="Promotion"
        :loading="loading"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
    <div class="input-area-footer">
      <span class="input-area-hint">按 Ctrl + Enter 快速发送</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { storeToRefs } from 'pinia'
import { Upload, Microphone, Promotion } from '@element-plus/icons-vue'

const appStore = useAppStore()
const { loading, currentSessionId } = storeToRefs(appStore)

const inputText = ref('')

async function handleSend() {
  if (!inputText.value.trim() || loading.value) return

  if (!currentSessionId.value) {
    console.error('No active session')
    return
  }

  const userMessage = inputText.value.trim()
  const timestamp = Date.now()
  const executionId = `temp_${timestamp}`

  // 一次性添加用户消息和临时助手消息
  const currentTurns = appStore.getTurns(currentSessionId.value || '')
  const newTurns = [...currentTurns]
  
  // 添加用户消息
  newTurns.push({
    id: `user-${timestamp}`,
    role: 'user',
    content: userMessage,
    time: timestamp
  })

  // 立即创建一个助手消息并标记为流式处理中，以显示loading效果
  newTurns.push({
    id: `assistant-${executionId}`,
    role: 'assistant',
    content: '',
    time: timestamp,
    executionId: executionId,
    status: 'running',
    isStreaming: true,
    isThinking: false,
    thought: '',
    steps: [],
    plan: null
  })

  // 一次性更新状态
  appStore.setTurns(currentSessionId.value || '', newTurns)
  // 设置loading状态为true，禁用发送按钮
  appStore.setLoading(true)

  try {
    // 检查 Electron 环境是否可用
    if (!window.electronAPI || !window.electronAPI.api) {
      console.warn('Electron API is not available, running in browser mode')
      // 在浏览器模式下，模拟API调用成功
      setTimeout(() => {
        inputText.value = ''
        appStore.setLoading(false)
      }, 500)
      return
    }
    
    const result = await window.electronAPI.api.executeTask(
      userMessage,
      currentSessionId.value
    )
    console.log('Task executed:', result)
    inputText.value = ''
  } catch (error) {
    console.error('Failed to execute task:', error)
    // 即使API调用失败，也清空输入框
    inputText.value = ''
  } finally {
    // 无论成功还是失败，都设置loading状态为false
    appStore.setLoading(false)
  }
}

function handleUpload() {
  window.electronAPI.file.selectFiles()
}

function handleVoice() {
  console.log('Voice input')
}
</script>

<style scoped lang="scss">
.input-area {
  width: 100%;
  padding: 12px 16px;
  background-color: $bg-color;
  border-top: 1px solid $border-lighter;
}

.input-area-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.input-area-main {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;

  .el-textarea {
    flex: 1;
  }

  .el-button {
    align-self: flex-end;
  }
}

.input-area-footer {
  display: flex;
  justify-content: flex-end;
}

.input-area-hint {
  font-size: $font-size-small;
  color: $text-secondary;
}
</style>
