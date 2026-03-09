<template>
  <el-dialog
    v-model="visible"
    title="切换工作目录"
    width="600px"
    :close-on-click-modal="false"
  >
    <div class="workspace-switch-dialog">
      <div class="current-workspace">
        <div class="label">当前工作目录：</div>
        <div class="path">{{ currentWorkspace?.workspace || '未初始化' }}</div>
        <el-tag v-if="currentWorkspace?.is_initialized" type="success" size="small">已初始化</el-tag>
        <el-tag v-else type="warning" size="small">未初始化</el-tag>
      </div>
      
      <div class="select-workspace">
        <div class="label">选择新工作目录：</div>
        <div class="input-group">
          <el-input
            v-model="newWorkspacePath"
            placeholder="请输入或选择工作目录路径"
            clearable
          />
          <el-button @click="selectDirectory">
            <el-icon><Folder /></el-icon>
            选择目录
          </el-button>
        </div>
      </div>
      
      <div class="validation-result" v-if="validationResult">
        <el-alert
          :title="validationResult.message"
          :type="validationResult.valid ? 'success' : 'error'"
          :closable="false"
          show-icon
        />
      </div>
    </div>
    
    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button 
        type="primary" 
        @click="handleSwitch"
        :loading="isSwitching"
        :disabled="!canSwitch"
      >
        {{ isSwitching ? '切换中...' : '切换' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Folder } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useWorkspaceStore } from '@/stores/workspace'

const workspaceStore = useWorkspaceStore()

const visible = ref(false)
const newWorkspacePath = ref('')
const validationResult = ref<any>(null)
const isSwitching = ref(false)

const currentWorkspace = computed(() => workspaceStore.currentWorkspace)
const canSwitch = computed(() => validationResult.value?.valid && !isSwitching.value)

watch(() => workspaceStore.switchDialogVisible, (val) => {
  visible.value = val
  if (val) {
    newWorkspacePath.value = ''
    validationResult.value = null
  }
})

watch(visible, (val) => {
  workspaceStore.switchDialogVisible = val
})

const selectDirectory = async () => {
  const path = await window.electronAPI.file.selectDirectory()
  if (path) {
    newWorkspacePath.value = path
    await validateWorkspace(path)
  }
}

const validateWorkspace = async (path: string) => {
  try {
    const result = await window.electronAPI.workspace.validate(path)
    validationResult.value = result.data
  } catch (error) {
    ElMessage.error('验证失败：' + (error as Error).message)
  }
}

const handleSwitch = async () => {
  if (!canSwitch.value) return
  
  isSwitching.value = true
  
  try {
    const result = await window.electronAPI.workspace.switch(newWorkspacePath.value, false)
    
    if (result.success) {
      ElMessage.success('工作目录切换成功')
      workspaceStore.loadCurrentWorkspace()
      visible.value = false
    } else {
      ElMessage.error('切换失败：' + result.error)
    }
  } catch (error) {
    ElMessage.error('切换异常：' + (error as Error).message)
  } finally {
    isSwitching.value = false
  }
}

const handleCancel = () => {
  visible.value = false
}
</script>

<style scoped lang="scss">
.workspace-switch-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
  
  .current-workspace,
  .select-workspace {
    .label {
      font-weight: bold;
      margin-bottom: 8px;
    }
    
    .path {
      font-family: 'Courier New', monospace;
      background: #f5f7fa;
      padding: 8px;
      border-radius: 4px;
      word-break: break-all;
      margin-bottom: 8px;
    }
  }
  
  .input-group {
    display: flex;
    gap: 8px;
  }
}
</style>
