<template>
  <div class="message-list" ref="scrollContainer">
    <div v-if="session">
      <div v-for="task in session.tasks" :key="task.taskId || task.createdAt">
        <div class="message-item" :class="'user'">
          <div class="message-avatar">
            <el-icon>
              <User />
            </el-icon>
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="message-role">{{ '用户' }}</span>
              <span class="message-time">{{ formatTime(task.createdAt) }}</span>
            </div>
            <div class="message-text-container">
              <div class="message-text-user" v-html="renderMarkdown(task.userInput)" />
            </div>
          </div>
        </div>

        <div class="message-item" :class="'assistant'">
          <div class="message-avatar">
            <el-icon>
              <ChatDotRound />
            </el-icon>
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="message-role">{{ '助手' }}</span>
              <span class="message-time">{{ formatTime(task.createdAt) }}</span>
              <span v-if="task.status" class="message-status" :class="task.status">
                {{ task.status === 'running' ? '执行中' : task.status === 'completed' ? '已完成' : '失败' }}
              </span>
            </div>

            <div v-if="task.planThinking === true && task.steps && task.steps.length === 0" class="message-plan-thinking">
              <div class="plan-thinking-header">
                <el-icon class="is-loading">
                  <Loading />
                </el-icon>
                <span class="plan-thinking-label">正在思考...</span>
              </div>
              <div v-if="task.planThinkingContent" class="plan-thinking-content">
                {{ task.planThinkingContent }}
              </div>
            </div>

            <div v-if="getPlanSteps(task.plan).length > 0" class="message-plan">
              <div class="plan-header" @click="togglePlanExpand(task.taskId)">
                <span class="plan-label">执行计划：</span>
                <span class="plan-expand-icon">{{ isPlanExpanded(task.taskId) ? '▼' : '▶' }}</span>
              </div>
              <transition name="plan-collapse">
                <div v-if="isPlanExpanded(task.taskId)" class="plan-steps">
                  <div v-for="(step, index) in getPlanSteps(task.plan)" :key="index" class="plan-step">
                    {{ index + 1 }}. {{ step }}
                  </div>
                </div>
              </transition>
            </div>
            <div v-if="task.steps && task.steps.length > 0" class="message-steps">
              <div class="steps-label">执行步骤：</div>
              <div class="steps-list">
                <div v-for="(step, index) in task.steps" :key="index" class="step-item" :class="step?.status">
                  <div class="step-header" @click="toggleStepExpand(task.taskId, index)">
                    <span class="step-index">{{ ((step?.stepIndex) ?? index) }}.</span>
                    <span class="step-description">{{ step?.description }}</span>
                    <span class="step-status">{{ step?.status === 'running' ? '执行中' : step?.status === 'completed' ? '已完成'
                      : '失败' }}</span>
                    <span class="step-expand-icon">{{ isStepExpanded(task.taskId, index) ? '▼' : '▶' }}</span>
                  </div>

                  <transition name="step-collapse" mode="out-in">
                    <div v-if="isStepExpanded(task.taskId, index)" class="step-content">
                      <div v-if="step?.thought" class="step-thought">
                        <div class="thought-label">思考过程：</div>
                        <div class="thought-content">{{ step?.thought }}</div>
                      </div>
                      <div v-if="step?.result" class="step-result">{{ step?.resultDescription || step?.result }}</div>
                    </div>
                  </transition>
                </div>
              </div>
            </div>
            <div v-if="task.result != '' && task.result !== undefined" class="message-text-container">
              <div class="message-text-wrapper">
                <div class="message-text" v-html="renderMarkdown(task.result)" />
              </div>
            </div>
            <div v-else class="message-text-container streaming">
              <div class="streaming-indicator">
                <el-icon class="is-loading">
                  <Loading />
                </el-icon>
                <span>正在生成回复...</span>
              </div>
            </div>
          </div>
          <StepInterventionCard v-if="hasFailedSteps(task)" :steps="task.steps || []" @skip="handleSkip"
            @retry="handleRetry" @batch-retry="handleBatchRetry" @submit="handleSubmit" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChatDotRound, Loading, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { storeToRefs } from 'pinia'
import { nextTick, ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import StepInterventionCard from './StepInterventionCard.vue'
// 配置marked库
marked.setOptions({
  breaks: true,
  gfm: true
})

const appStore = useAppStore()
const { sessions, currentSessionId } = storeToRefs(appStore)


const session = computed(() => sessions.value.find(s => s.sessionId === currentSessionId.value))

const scrollContainer = ref<HTMLElement>()

watch(session.value?.tasks || [], () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

function scrollToBottom() {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
  }
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function getPlanSteps(plan: any): string[] {
  if (!plan) return []

  try {
    let parsed: any[] = []

    // 如果已经是数组，直接使用
    if (Array.isArray(plan)) {
      parsed = plan
    }
    // 如果是字符串，尝试解析JSON
    else if (typeof plan === 'string') {
      parsed = JSON.parse(plan)
      if (!Array.isArray(parsed)) {
        return []
      }
    }
    else {
      return []
    }

    // 处理数组元素，提取描述文本
    return parsed.map((item: any) => {
      if (typeof item === 'string') {
        return item
      }
      if (typeof item === 'object' && item !== null) {
        // 尝试提取 description 字段
        if (item.description) {
          return item.description
        }
        // 如果没有 description，尝试其他常见字段
        if (item.content) {
          return item.content
        }
        if (item.text) {
          return item.text
        }
        // 如果都没有，返回整个对象的字符串表示
        return JSON.stringify(item)
      }
      return String(item)
    })
  } catch (e) {
    console.error('解析执行计划失败:', e)
    return []
  }
}

function renderMarkdown(content: any): string {
  if (!content) return ''

  // 检查是否为JSON格式的内容
  if (typeof content === 'object' && content !== null) {
    // 提取最终结果部分
    if (content.final_result) {
      return marked.parse(content.final_result)
    } else if (content.result) {
      return marked.parse(content.result)
    } else if (content.content) {
      // 如果JSON中包含content字段，递归处理
      return renderMarkdown(content.content)
    } else {
      // 如果没有找到最终结果，显示提示信息
      return marked.parse('*暂无最终结果*')
    }
  }

  // 处理字符串格式的内容（Markdown）
  const contentStr = typeof content === 'string' ? content : JSON.stringify(content)

  // 提取最终结果部分，只显示最终结果
  if (contentStr.includes('# 最终结果')) {
    const parts = contentStr.split('# 最终结果')
    if (parts.length > 1) {
      const finalResult = parts[1].trim()
      // 如果最终结果部分为空，显示提示信息
      if (!finalResult) {
        return marked.parse('*暂无最终结果*')
      }
      return marked.parse(finalResult)
    }
  }

  return marked.parse(contentStr)
}


function hasFailedSteps(task: any): boolean {
  if (task.status === 'failed') {
    return true
  }
  if (task.errorInfo) {
    return true
  }
  if (task.steps && task.steps.some((s: any) => s && s.status === 'failed')) {
    return true
  }
  return false
}

function hasRunningSteps(task: any): boolean {
  if (task.status === 'running') {
    return true
  }
  if (task.planThinking) {
    return true
  }
  if (task.steps && task.steps.some((s: any) => s && (s.status === 'running' || s.isThinking))) {
    return true
  }
  return false
}



function handleSkip(stepIndex: number) {
  console.log('Skip step:', stepIndex)
  ElMessage.success(`已跳过步骤 ${stepIndex + 1}`)
}

function handleRetry(stepIndex: number, userInput?: string) {
  console.log('Retry step:', stepIndex, userInput)
  ElMessage.info(`正在重试步骤 ${stepIndex + 1}...`)
}

function handleBatchRetry() {
  console.log('Batch retry')
  ElMessage.info('已启动批量重试')
}

function handleSubmit(userInput: string) {
  console.log('Submit correction:', userInput)
  ElMessage.success('已提交修正内容')
}

// 步骤展开状态管理
const expandedSteps = ref<Record<string, Record<number, boolean>>>({})

function toggleStepExpand(turnId: string, stepIndex: number) {
  if (!expandedSteps.value[turnId]) {
    expandedSteps.value[turnId] = {}
  }
  expandedSteps.value[turnId][stepIndex] = !expandedSteps.value[turnId][stepIndex]
}

// 计算步骤的展开状态
function isStepExpanded(turnId: string, stepIndex: number): boolean {
  // 如果步骤正在执行，默认展开
  const task = session.value?.tasks.find(t => t.taskId === turnId)
  if (task && task.steps && task.steps[stepIndex] && task.steps[stepIndex].status === 'running') {
    return true
  }
  return expandedSteps.value[turnId]?.[stepIndex] || false
}

// 执行计划展开状态管理
const expandedPlans = ref<Record<string, boolean>>({})

function togglePlanExpand(turnId: string) {
  expandedPlans.value[turnId] = !expandedPlans.value[turnId]
}

function isPlanExpanded(turnId: string): boolean {
  if (expandedPlans.value[turnId] !== undefined) {
    return expandedPlans.value[turnId]
  }
  return true
}

</script>

<style scoped lang="scss">
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message-item {
  display: flex;
  margin-bottom: 20px;

  &.user {
    flex-direction: row-reverse;
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $bg-color;
  flex-shrink: 0;

  .user & {
    background-color: $success-color;
  }
}

.message-content {
  flex: 1;
  margin: 0 12px;
  max-width: calc(100% - 60px);
}

.message-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;

  .user & {
    flex-direction: row-reverse;
  }
}

.message-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;

  .user & {
    margin-left: 0;
    margin-right: 8px;
  }

  &.running {
    background-color: #e6f7ff;
    color: #1890ff;
  }

  &.completed {
    background-color: #f6ffed;
    color: #52c41a;
  }

  &.failed {
    background-color: #fff2f0;
    color: #ff4d4f;
  }
}

.message-thought {
  background-color: #f5f5f5;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;

  .thought-label {
    font-weight: 600;
    margin-bottom: 8px;
    color: #666;
  }

  .thought-content {
    line-height: 1.5;
    color: #333;
  }
}

.step-thought {
  background-color: rgba(245, 245, 245, 0.8);
  border-radius: 6px;
  padding: 8px 10px;
  margin: 8px 0;

  .thought-label {
    font-weight: 600;
    margin-bottom: 6px;
    color: #666;
    font-size: 13px;
  }

  .thought-content {
    line-height: 1.4;
    color: #333;
    font-size: 13px;
  }
}

.message-plan-thinking {
  background-color: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;

  .plan-thinking-header {
    display: flex;
    align-items: center;
    color: #fa8c16;

    .is-loading {
      margin-right: 8px;
      animation: rotate 1s linear infinite;
    }

    .plan-thinking-label {
      font-weight: 600;
    }
  }

  .plan-thinking-content {
    margin-top: 10px;
    padding: 10px;
    background-color: rgba(250, 140, 22, 0.1);
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.5;
    color: #666;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
  }
}

.message-plan {
  background-color: #f0f5ff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;

  .plan-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    user-select: none;

    &:hover {
      background-color: #e6f0ff;
      margin: -12px;
      padding: 12px;
      border-radius: 8px;
    }
  }

  .plan-label {
    font-weight: 600;
    color: #1890ff;
  }

  .plan-expand-icon {
    font-size: 12px;
    color: #1890ff;
    transition: transform 0.2s;
  }

  .plan-steps {
    margin-left: 20px;
    margin-top: 8px;
    max-height: 1000px;
    overflow: hidden;

    .plan-step {
      margin-bottom: 4px;
      line-height: 1.4;
    }
  }
}

.message-steps {
  background-color: #f9f0ff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;

  .steps-label {
    font-weight: 600;
    margin-bottom: 8px;
    color: #722ed1;
  }

  .steps-list {
    .step-item {
      margin-bottom: 12px;
      padding: 8px;
      border-radius: 6px;

      &.running {
        background-color: #e6f7ff;
      }

      &.completed {
        background-color: #f6ffed;
      }

      &.failed {
        background-color: #fff2f0;
      }

      .step-header {
        display: flex;
        align-items: center;
        margin-bottom: 4px;
        cursor: pointer;

        .step-index {
          font-weight: 600;
          margin-right: 8px;
        }

        .step-description {
          flex: 1;
        }

        .step-status {
          font-size: 12px;
          padding: 2px 6px;
          border-radius: 8px;
          margin-right: 8px;

          &.running {
            background-color: #1890ff;
            color: white;
          }

          &.completed {
            background-color: #52c41a;
            color: white;
          }

          &.failed {
            background-color: #ff4d4f;
            color: white;
          }
        }

        .step-expand-icon {
          font-size: 12px;
          color: #999;
          transition: transform 0.2s;
        }
      }

      .step-content {
        margin-top: 8px;
        padding-left: 24px;
        overflow: hidden;
      }

      .step-collapse-enter-active,
      .step-collapse-leave-active {
        transition: opacity 0.3s ease, max-height 0.3s ease, margin-top 0.3s ease;
      }

      .step-collapse-enter-from {
        opacity: 0;
        max-height: 0;
        margin-top: 0;
      }

      .step-collapse-leave-to {
        opacity: 0;
        max-height: 0;
        margin-top: 0;
      }

      .plan-collapse-enter-active,
      .plan-collapse-leave-active {
        transition: opacity 0.3s ease, max-height 0.3s ease, margin-top 0.3s ease;
      }

      .plan-collapse-enter-from {
        opacity: 0;
        max-height: 0;
        margin-top: 0;
      }

      .plan-collapse-leave-to {
        opacity: 0;
        max-height: 0;
        margin-top: 0;
      }

      .step-result {
        margin-top: 4px;
        font-size: 14px;
        line-height: 1.4;
      }
    }
  }
}

.message-role {
  font-size: $font-size-small;
  font-weight: 500;
  color: $text-regular;
}

.message-time {
  font-size: $font-size-small;
  color: $text-secondary;
  margin-left: 8px;

  .user & {
    margin-left: 0;
    margin-right: 8px;
  }
}

.message-text-container {
  .user & {
    text-align: right;
  }

  &.streaming {
    min-height: 40px;
    display: flex;
    align-items: center;
    justify-content: flex-start;

    .user & {
      justify-content: flex-end;
    }
  }
}

.message-text-wrapper {
  background-color: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-top: 8px;
  display: block;
  max-width: 100%;

  .user & {
    background-color: #f0f7ff;
    border-color: #d6e4ff;
  }

  .message-text-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #333;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 8px;

    .user & {
      color: #1890ff;
      border-bottom-color: #d6e4ff;
    }
  }
}

.message-text-user {
  background-color: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 8px;
  display: inline-block;
  max-width: 100%;
  text-align: left;

  ::v-deep(p) {
    margin: 0;
    line-height: 1.6;
    color: #333;
  }
}

.streaming-indicator {
  display: flex;
  align-items: center;
  color: #999;
  font-size: 14px;

  .is-loading {
    margin-right: 8px;
    animation: rotate 1s linear infinite;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.message-text {
  font-size: $font-size-base;
  line-height: 1.6;
  color: $text-primary;
  word-wrap: break-word;
  display: block;
  text-align: left;

  ul,
  ol {
    margin: 8px 0;
    padding-left: 32px;
    text-indent: 0;
  }

  li {
    margin: 4px 0;
    padding-left: 4px;
    text-indent: 0;
  }

  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    margin: 16px 0 8px 0;
    font-weight: 600;
  }

  h1 {
    font-size: 1.5em;
  }

  h2 {
    font-size: 1.3em;
  }

  h3 {
    font-size: 1.1em;
  }

  p {
    margin: 8px 0;
  }

  code {
    background-color: rgba(110, 118, 129, 0.1);
    border-radius: 3px;
    padding: 0.2em 0.4em;
    font-size: 0.9em;
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  }

  pre {
    background-color: rgba(110, 118, 129, 0.1);
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    margin: 12px 0;

    code {
      background-color: transparent;
      padding: 0;
    }
  }

  blockquote {
    border-left: 4px solid #dfe2e5;
    color: #6a737d;
    padding: 0 16px;
    margin: 12px 0;
  }

  a {
    color: #0366d6;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  table {
    border-collapse: collapse;
    margin: 12px 0;
    width: 100%;

    th,
    td {
      border: 1px solid #dfe2e5;
      padding: 6px 13px;
    }

    th {
      background-color: #f6f8fa;
      font-weight: 600;
    }
  }
}

// 全局样式 - 用于 v-html 渲染的 Markdown 内容
:deep(.message-text) {

  ul,
  ol {
    margin: 8px 0;
    padding-left: 32px !important;
    text-indent: 0 !important;

    li {
      margin: 4px 0;
      padding-left: 4px !important;
      text-indent: 0 !important;
      list-style-position: outside !important;

      // 确保列表项内容正确缩进
      >* {
        text-indent: 0;
      }
    }
  }

  // 有序列表特殊处理
  ol {
    li {
      list-style-type: decimal;
      position: relative;

      &::marker {
        display: inline-block;
        min-width: 20px;
        text-align: right;
        padding-right: 8px;
      }
    }
  }

  // 无序列表特殊处理
  ul {
    li {
      list-style-type: disc;
      position: relative;
    }
  }
}
</style>