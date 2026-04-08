<template>
  <div class="model-route-bar">
    <el-icon class="model-route-icon">
      <Promotion />
    </el-icon>
    <span class="model-route-text">{{ modelRoute.reason }}</span>
    <span class="model-route-model">{{ modelRoute.selectedModel }}</span>
    <span class="model-route-cost">预计 {{ modelRoute.estimatedTokens }} Token</span>
    <el-dropdown
      v-if="modelRoute.canOverride"
      trigger="click"
      @command="handleCommand"
    >
      <el-button
        size="small"
        link
      >
        更改模型
        <el-icon class="el-icon--right">
          <ArrowDown />
        </el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="gpt-4">
            GPT-4
          </el-dropdown-item>
          <el-dropdown-item command="gpt-3.5-turbo">
            GPT-3.5 Turbo
          </el-dropdown-item>
          <el-dropdown-item command="qwen-max">
            Qwen Max
          </el-dropdown-item>
          <el-dropdown-item command="qwen-turbo">
            Qwen Turbo
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { Promotion, ArrowDown } from '@element-plus/icons-vue'
import type { ModelRoute } from '../../types'

interface Props {
  modelRoute: ModelRoute
}

defineProps<Props>()

function handleCommand(command: string) {
  console.log('Override model:', command)
}
</script>

<style scoped lang="scss">
.model-route-bar {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background-color: #ecf5ff;
  border-bottom: 1px solid #d9ecff;
}

.model-route-icon {
  margin-right: 8px;
  color: $primary-color;
}

.model-route-text {
  flex: 1;
  font-size: $font-size-small;
  color: $text-primary;
}

.model-route-model {
  font-size: $font-size-small;
  font-weight: 500;
  color: $primary-color;
  margin-right: 8px;
}

.model-route-cost {
  font-size: $font-size-small;
  color: $text-secondary;
  margin-right: 16px;
}
</style>
