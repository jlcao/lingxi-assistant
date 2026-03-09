<template>
  <div class="workspace-status" @click="handleClick">
    <div class="workspace-path" :title="workspacePath">
      <el-icon><Folder /></el-icon>
      <span class="path-text">{{ shortPath }}</span>
    </div>
    
    <div class="lingxi-status" :class="{ 'initialized': isInitialized }">
      <el-tooltip :content="lingxiStatusText" placement="bottom">
        <el-icon v-if="isInitialized"><Check /></el-icon>
        <el-icon v-else><Warning /></el-icon>
      </el-tooltip>
    </div>
    
    <div class="workspace-skills" v-if="workspaceSkillsCount > 0">
      <el-badge :value="workspaceSkillsCount" :max="99">
        <el-icon><Star /></el-icon>
      </el-badge>
    </div>
    
    <el-button size="small" circle @click="openSwitchDialog">
      <el-icon><Switch /></el-icon>
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Folder, Check, Warning, Star, Switch } from '@element-plus/icons-vue'
import { useWorkspaceStore } from '@/stores/workspace'

const workspaceStore = useWorkspaceStore()

const workspacePath = computed(() => workspaceStore.currentWorkspace?.workspace || '未初始化')
const shortPath = computed(() => {
  const path = workspacePath.value
  if (path.length > 30) {
    return `...${path.slice(-27)}`
  }
  return path
})

const isInitialized = computed(() => workspaceStore.currentWorkspace?.is_initialized || false)
const lingxiStatusText = computed(() => isInitialized.value ? '.lingxi 已初始化' : '.lingxi 未初始化')
const workspaceSkillsCount = computed(() => workspaceStore.workspaceSkillsCount)

const openSwitchDialog = () => {
  workspaceStore.openSwitchDialog()
}

const handleClick = () => {
  // 点击工作区状态时打开切换对话框
  openSwitchDialog()
}

onMounted(() => {
  workspaceStore.loadCurrentWorkspace()
})
</script>

<style scoped lang="scss">
.workspace-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  cursor: pointer;
  
  &:hover {
    background: rgba(255, 255, 255, 0.2);
  }
  
  .workspace-path {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #fff;
    
    .path-text {
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  
  .lingxi-status {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #f56c6c;
    
    &.initialized {
      color: #67c23a;
    }
  }
  
  .workspace-skills {
    color: #e6a23c;
  }
}
</style>
