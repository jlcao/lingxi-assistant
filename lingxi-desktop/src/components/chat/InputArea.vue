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
  
  // 设置loading状态为true，禁用发送按钮
  appStore.setLoading(true)

  try {
    const result = await window.electronAPI.api.executeTask(
      userMessage,
      currentSessionId.value
    )
    console.log('Task executed:', result)
    inputText.value = ''
  } catch (error) {
    console.error('Failed to execute task:', error)
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
