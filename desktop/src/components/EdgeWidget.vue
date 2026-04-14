<template>
  <div
    class="edge-widget"
    @click="handleClick"
  >
    <div class="edge-widget-bubble">
      <el-icon class="edge-widget-icon">
        <ChatDotRound />
      </el-icon>
      <div
        v-if="resourceStatus !== 'normal'"
        class="edge-widget-indicator"
        :class="resourceStatus"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChatDotRound } from '@element-plus/icons-vue'
import { useAppStore } from '../stores/app'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'

const appStore = useAppStore()
const { resourceUsage } = storeToRefs(appStore)

const resourceStatus = computed(() => {
  if (!resourceUsage.value) return 'normal'
  if (resourceUsage.value.cpu > 80 || resourceUsage.value.memory > 80) return 'critical'
  if (resourceUsage.value.cpu > 60 || resourceUsage.value.memory > 60) return 'warning'
  return 'normal'
})

function handleClick() {
  window.electronAPI.window.toggle()
}
</script>

<style scoped lang="scss">
.edge-widget {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 9999;
  cursor: pointer;
}

.edge-widget-bubble {
  width: 30px;
  height: 30px;
  border-radius: 15px;
  background-color: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: $shadow-dark;
  transition: $transition-base;

  &:hover {
    transform: scale(1.1);
  }
}

.edge-widget-icon {
  color: $bg-color;
  font-size: 16px;
}

.edge-widget-indicator {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid $bg-color;

  &.warning {
    background-color: $warning-color;
  }

  &.critical {
    background-color: $danger-color;
  }
}
</style>
