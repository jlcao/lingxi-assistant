<template>
  <div class="settings">
    <div class="settings-header">
      <h2>设置</h2>
    </div>
    <div class="settings-content">
      <el-form
        :model="config"
        label-width="120px"
      >
        <el-form-item label="API 地址">
          <el-input
            v-model="config.apiUrl"
            placeholder="http://localhost:8000"
          />
        </el-form-item>
        <el-form-item label="WebSocket 地址">
          <el-input
            v-model="config.wsUrl"
            placeholder="ws://localhost:8000/ws"
          />
        </el-form-item>
        <el-form-item label="默认模型">
          <el-select
            v-model="config.model"
            placeholder="选择模型"
          >
            <el-option
              label="GPT-4"
              value="gpt-4"
            />
            <el-option
              label="GPT-3.5 Turbo"
              value="gpt-3.5-turbo"
            />
            <el-option
              label="Qwen Max"
              value="qwen-max"
            />
            <el-option
              label="Qwen Turbo"
              value="qwen-turbo"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="最大 Token">
          <el-input-number
            v-model="config.maxTokens"
            :min="1000"
            :max="128000"
          />
        </el-form-item>
        <el-form-item label="超时时间（秒）">
          <el-input-number
            v-model="config.timeout"
            :min="10"
            :max="300"
          />
        </el-form-item>
        <el-form-item label="主题">
          <el-radio-group v-model="config.theme">
            <el-radio label="light">
              浅色
            </el-radio>
            <el-radio label="dark">
              深色
            </el-radio>
            <el-radio label="auto">
              自动
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="语言">
          <el-select
            v-model="config.language"
            placeholder="选择语言"
          >
            <el-option
              label="简体中文"
              value="zh-CN"
            />
            <el-option
              label="English"
              value="en-US"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="自动保存">
          <el-switch v-model="config.autoSave" />
        </el-form-item>
        <el-form-item label="断点有效期（天）">
          <el-input-number
            v-model="config.checkpointExpiry"
            :min="1"
            :max="30"
          />
        </el-form-item>
      </el-form>
      <div class="settings-footer">
        <el-button @click="handleCancel">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSave"
        >
          保存
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { Config } from '../../types'
import { ElMessage } from 'element-plus'
import { apiService } from '../api/apiService'

const router = useRouter()

const config = ref<Config>({
  apiUrl: 'http://localhost:8000',
  wsUrl: 'ws://localhost:8000/ws',
  model: 'gpt-4',
  maxTokens: 4000,
  timeout: 30,
  theme: 'auto',
  language: 'zh-CN',
  autoSave: true,
  checkpointExpiry: 7
})

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  try {
    const data = await apiService.client.getConfig()
    config.value = { ...config.value, ...data.data }
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

async function handleSave() {
  try {
    await apiService.client.updateConfig(config.value)
    ElMessage.success('设置已保存')
    router.back()
  } catch (error) {
    console.error('Failed to save config:', error)
    ElMessage.error('保存失败')
  }
}

function handleCancel() {
  router.back()
}
</script>

<style scoped lang="scss">
.settings {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: $bg-color;
}

.settings-header {
  padding: 20px 24px;
  border-bottom: 1px solid $border-lighter;

  h2 {
    font-size: 20px;
    font-weight: 500;
    color: $text-primary;
    margin: 0;
  }
}

.settings-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid $border-lighter;
}
</style>
