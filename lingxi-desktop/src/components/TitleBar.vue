<template>
  <div class="title-bar">
    <div class="title-bar-left">
      <el-icon class="title-bar-logo"><Star /></el-icon>
      <span class="title-bar-text">Lingxi 助手</span>
    </div>
    <div class="title-bar-center">
      <el-input
        v-model="searchText"
        placeholder="搜索"
        :prefix-icon="Search"
        size="small"
        class="title-bar-search"
      />
    </div>
    <div class="title-bar-right">
      <WorkspaceStatus />
      <div class="title-bar-status">
        <span class="status-dot online"></span>
        <span class="status-text">状态</span>
      </div>
      <el-button
        :icon="Folder"
        size="small"
        circle
        text
        @click="handleFolder"
      />
      <el-button
        :icon="Setting"
        size="small"
        circle
        text
        @click="handleSettings"
      />
      <el-button
        :icon="Minus"
        size="small"
        circle
        text
        @click="handleMinimize"
      />
      <el-button
        size="small"
        circle
        text
        @click="handleMaximize"
      >
        <el-icon v-if="isMaximized"><FullScreen /></el-icon>
        <el-icon v-else><ZoomIn /></el-icon>
      </el-button>
      <el-button
        :icon="Close"
        size="small"
        circle
        text
        @click="handleClose"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Star, Search, Folder, Setting, Minus, Close, FullScreen, ZoomIn } from '@element-plus/icons-vue'
import WorkspaceStatus from './WorkspaceStatus.vue'

const searchText = ref('')
const isMaximized = ref(false)

function handleMinimize() {
  window.electronAPI.window.minimize()
}

function handleMaximize() {
  window.electronAPI.window.maximize()
  updateMaximizedState()
}

function handleClose() {
  window.electronAPI.window.minimize()
}

function handleSettings() {
  console.log('Open settings')
}

function handleFolder() {
  console.log('Open folder')
}

async function updateMaximizedState() {
  if (window.electronAPI?.window?.isMaximized) {
    isMaximized.value = await window.electronAPI.window.isMaximized()
  }
}

onMounted(async () => {
  await updateMaximizedState()
})
</script>

<style scoped lang="scss">
.title-bar {
  width: 100%;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #ffffff;
  border-bottom: 1px solid #e8e8e8;
  padding: 0 16px;
  user-select: none;
  -webkit-app-region: drag;
}

.title-bar-left {
  display: flex;
  align-items: center;
  -webkit-app-region: drag;
}

.title-bar-logo {
  font-size: 20px;
  color: #1890ff;
  margin-right: 8px;
}

.title-bar-text {
  font-size: 16px;
  font-weight: 600;
  color: #333333;
}

.title-bar-center {
  flex: 1;
  max-width: 300px;
  margin: 0 24px;
  -webkit-app-region: no-drag;
}

.title-bar-search {
  .el-input__wrapper {
    border-radius: 16px;
  }
}

.title-bar-right {
  display: flex;
  align-items: center;
  -webkit-app-region: no-drag;
}

.title-bar-status {
  display: flex;
  align-items: center;
  margin-right: 16px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;

  &.online {
    background-color: #52c41a;
  }
}

.status-text {
  font-size: 12px;
  color: #666666;
}

.title-bar-right .el-button {
  margin-left: 8px;
  color: #666666;

  &:hover {
    color: #1890ff;
  }
}

.title-bar-right .el-button .el-icon {
  color: inherit;
}
</style>
