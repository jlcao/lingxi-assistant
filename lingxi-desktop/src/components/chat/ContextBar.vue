<template>
  <div class="context-bar" @click="handleClick">
    <div class="context-bar-progress">
      <div
        class="context-bar-fill"
        :class="tokenStatus"
        :style="{ width: `${tokenPercentage}%` }"
      />
    </div>
    <div class="context-bar-info">
      <span class="context-bar-text">
        Token: {{ currentTokens }} / {{ maxTokens }}
      </span>
      <el-button
        v-if="tokenStatus === 'critical'"
        type="danger"
        size="small"
        link
        @click.stop="handleCompress"
      >
        立即压缩
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { storeToRefs } from 'pinia'

const appStore = useAppStore()
const { resourceUsage, tokenStatus, tokenPercentage } = storeToRefs(appStore)

const currentTokens = computed(() => {
  return resourceUsage.value?.tokens.current || 0
})

const maxTokens = computed(() => {
  return resourceUsage.value?.tokens.limit || 0
})

function handleClick() {
  console.log('Show token analysis dialog')
}

function handleCompress() {
  console.log('Show compress preview dialog')
}
</script>

<style scoped lang="scss">
.context-bar {
  width: 100%;
  height: 32px;
  display: flex;
  flex-direction: column;
  padding: 4px 16px;
  background-color: $bg-color;
  border-bottom: 1px solid $border-lighter;
  cursor: pointer;
}

.context-bar-progress {
  width: 100%;
  height: 4px;
  background-color: $border-lighter;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}

.context-bar-fill {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;

  &.normal {
    background-color: $success-color;
  }

  &.warning {
    background-color: $warning-color;
  }

  &.critical {
    background-color: $danger-color;
  }
}

.context-bar-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.context-bar-text {
  font-size: $font-size-small;
  color: $text-regular;
}
</style>
