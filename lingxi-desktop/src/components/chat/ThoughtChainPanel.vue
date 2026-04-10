<template>
  <div class="thought-chain-panel">
    <div
      class="panel-header"
      @click="toggleExpand"
    >
      <span class="panel-title">思考过程 ({{ chain.steps.length }} 步)</span>
      <el-icon :class="{ 'rotate': isExpanded }">
        <ArrowDown />
      </el-icon>
    </div>
    <div
      v-if="isExpanded"
      class="panel-content"
    >
      <div 
        v-for="(step, index) in chain.steps" 
        :key="index"
        class="thought-step"
      >
        <div class="step-header">
          <span class="step-index">步骤 {{ index + 1 }}</span>
          <span class="step-type">{{ getStepTypeText(step.type) }}</span>
        </div>
        <div class="step-content">
          <div
            v-if="step.thought"
            class="step-thought"
          >
            {{ step.thought }}
          </div>
          <div
            v-if="step.action"
            class="step-action"
          >
            <strong>执行：</strong>{{ step.action }}
          </div>
          <div
            v-if="step.result"
            class="step-result"
          >
            <strong>结果：</strong>{{ step.result }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps<{
  chain: any
}>()

const isExpanded = ref(false) // 默认收起

// 确保默认收起
setTimeout(() => {
  isExpanded.value = false
}, 0)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

function getStepTypeText(type: string): string {
  const typeMap: Record<string, string> = {
    'execution': '执行',
    'observation': '观察',
    'skill_call': '技能调用',
    'finish': '完成'
  }
  return typeMap[type] || type
}
</script>

<style scoped>
.thought-chain-panel {
  margin-top: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background-color: #f5f5f5;
  cursor: pointer;
  transition: background-color 0.2s;
}

.panel-header:hover {
  background-color: #e8e8e8;
}

.panel-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.rotate {
  transform: rotate(180deg);
  transition: transform 0.3s;
}

.panel-content {
  padding: 16px;
  background-color: #fafafa;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}

.thought-step {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.thought-step:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.step-index {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  background-color: #e0e0e0;
  padding: 2px 8px;
  border-radius: 10px;
}

.step-type {
  font-size: 12px;
  color: #999;
}

.step-content {
  font-size: 14px;
  line-height: 1.5;
  color: #333;
}

.step-thought {
  margin-bottom: 8px;
}

.step-action {
  margin-bottom: 8px;
}

.step-result {
  margin-bottom: 8px;
}
</style>