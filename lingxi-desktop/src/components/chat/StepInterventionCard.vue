<template>
  <div class="step-intervention-card">
    <div class="intervention-header">
      <el-icon class="intervention-icon"><WarningFilled /></el-icon>
      <span class="intervention-title">步骤执行失败，需要人工干预</span>
    </div>
    <div class="intervention-body">
      <div v-for="step in failedSteps" :key="step.stepIndex" class="intervention-step">
        <div class="intervention-step-name">
          步骤 {{ step.stepIndex }}: {{ step.name }}
          <span class="intervention-step-retry">重试次数: {{ step.retryCount }}/{{ step.maxRetries }}</span>
        </div>
        <div v-if="step.error" class="intervention-error">
          <strong>错误信息:</strong> {{ step.error.message }}
        </div>
        <div v-if="step.error?.type" class="intervention-error-type">
          <strong>错误类型:</strong> {{ step.error.type }}
        </div>
        <div v-if="step.error?.suggestions && step.error.suggestions.length > 0" class="intervention-suggestions">
          <strong>修正建议:</strong>
          <ul>
            <li v-for="(suggestion, index) in step.error.suggestions" :key="index">
              {{ suggestion }}
            </li>
          </ul>
        </div>
      </div>
      <div class="intervention-actions">
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="3"
          placeholder="请输入修正内容或继续指令..."
          class="intervention-input"
        />
        <div class="intervention-buttons">
          <el-button size="small" @click="handleSkip">跳过</el-button>
          <el-button size="small" @click="handleRetry">重试</el-button>
          <el-button size="small" @click="handleBatchRetry">批量重试</el-button>
          <el-button type="primary" size="small" @click="handleSubmit">提交修正</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import type { Step } from '../../types'

interface Props {
  steps: Step[]
}

const props = defineProps<Props>()

const userInput = ref('')

const failedSteps = computed(() => {
  return props.steps.filter(s => s.status === 'failed')
})

const emit = defineEmits<{
  (e: 'skip', stepIndex: number): void
  (e: 'retry', stepIndex: number, userInput?: string): void
  (e: 'batchRetry'): void
  (e: 'submit', userInput: string): void
}>()

function handleSkip() {
  if (failedSteps.value.length > 0) {
    emit('skip', failedSteps.value[0].stepIndex)
    ElMessage.success('已跳过当前步骤')
  }
}

function handleRetry() {
  if (failedSteps.value.length > 0) {
    emit('retry', failedSteps.value[0].stepIndex, userInput.value)
    ElMessage.info('正在重试当前步骤...')
  }
}

function handleBatchRetry() {
  emit('batchRetry')
  ElMessage.info('已启动批量重试，后续类似错误将自动重试3次')
}

function handleSubmit() {
  if (userInput.value.trim()) {
    emit('submit', userInput.value)
    ElMessage.success('已提交修正内容')
    userInput.value = ''
  } else {
    ElMessage.warning('请输入修正内容')
  }
}
</script>

<style scoped lang="scss">
.step-intervention-card {
  margin-top: 12px;
  padding: 12px;
  background-color: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: $border-radius-base;
}

.intervention-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.intervention-icon {
  margin-right: 8px;
  color: $warning-color;
  font-size: 18px;
}

.intervention-title {
  font-size: $font-size-base;
  font-weight: 500;
  color: $text-primary;
}

.intervention-body {
  background-color: $bg-color;
  border-radius: $border-radius-small;
  padding: 12px;
}

.intervention-step {
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }
}

.intervention-step-name {
  font-size: $font-size-small;
  font-weight: 500;
  color: $text-primary;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.intervention-step-retry {
  font-size: $font-size-small;
  color: $text-secondary;
  font-weight: normal;
}

.intervention-error {
  font-size: $font-size-small;
  color: $danger-color;
  margin-bottom: 8px;
  padding: 8px;
  background-color: #fef0f0;
  border-radius: $border-radius-small;
}

.intervention-error-type {
  font-size: $font-size-small;
  color: $warning-color;
  margin-bottom: 8px;
}

.intervention-suggestions {
  font-size: $font-size-small;
  color: $text-regular;
  margin-bottom: 8px;

  ul {
    margin-left: 20px;
    margin-top: 4px;
  }
}

.intervention-actions {
  margin-top: 12px;
}

.intervention-input {
  margin-bottom: 12px;
}

.intervention-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
