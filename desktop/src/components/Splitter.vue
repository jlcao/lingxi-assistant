<template>
  <div class="splitter">
    <div
      class="splitter-pane left"
      :style="{ width: leftWidth }"
    >
      <slot name="left" />
    </div>
    <div
      class="splitter-handle"
      @mousedown="handleMouseDown($event, 'left')"
    >
      <div class="splitter-handle-bar" />
    </div>
    <div
      class="splitter-pane center"
      :style="{ flex: 1 }"
    >
      <slot name="center" />
    </div>
    <div
      class="splitter-handle"
      @mousedown="handleMouseDown($event, 'right')"
    >
      <div class="splitter-handle-bar" />
    </div>
    <div
      class="splitter-pane right"
      :style="{ width: rightWidth }"
    >
      <slot name="right" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const leftWidth = ref('200px')
const rightWidth = ref('250px')
const isResizing = ref(false)
const currentHandle = ref<'left' | 'right' | null>(null)

function handleMouseDown(event: MouseEvent, handle: 'left' | 'right') {
  isResizing.value = true
  currentHandle.value = handle
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

function handleMouseMove(event: MouseEvent) {
  if (!isResizing.value) return

  const container = document.querySelector('.splitter') as HTMLElement
  if (!container) return

  const containerRect = container.getBoundingClientRect()
  const x = event.clientX - containerRect.left

  if (currentHandle.value === 'left') {
    leftWidth.value = `${Math.max(150, Math.min(300, x))}px`
  } else if (currentHandle.value === 'right') {
    const rightX = containerRect.width - x
    rightWidth.value = `${Math.max(200, Math.min(400, rightX))}px`
  }
}

function handleMouseUp() {
  isResizing.value = false
  currentHandle.value = null
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
}

onUnmounted(() => {
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})
</script>

<style scoped lang="scss">
.splitter {
  width: 100%;
  height: 100%;
  display: flex;
  background-color: #ffffff;
}

.splitter-pane {
  height: 100%;
  overflow: hidden;

  &.left {
    border-right: 1px solid #e8e8e8;
  }

  &.right {
    border-left: 1px solid #e8e8e8;
  }
}

.splitter-handle {
  width: 4px;
  height: 100%;
  background-color: #f0f0f0;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;

  &:hover {
    background-color: #d9d9d9;
  }
}

.splitter-handle-bar {
  width: 2px;
  height: 20px;
  background-color: #bfbfbf;
  border-radius: 1px;
}
</style>
