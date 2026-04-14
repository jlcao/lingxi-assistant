<template>
  <el-dialog
    v-model="visible"
    title="工作目录初始化向导"
    width="700px"
    :close-on-click-modal="false"
  >
    <el-steps
      :active="currentStep"
      finish-status="success"
      align-center
    >
      <el-step title="选择目录" />
      <el-step title="创建.lingxi" />
      <el-step title="完成" />
    </el-steps>
    
    <div
      class="step-content"
      style="margin-top: 24px;"
    >
      <div
        v-show="currentStep === 0"
        class="step-1"
      >
        <el-result
          icon="info"
          title="选择工作目录"
          sub-title="工作目录将用于存储项目文件、配置和技能"
        >
          <template #extra>
            <div class="directory-selector">
              <el-input
                v-model="workspacePath"
                placeholder="请选择工作目录路径"
                readonly
              />
              <el-button @click="selectDirectory">
                <el-icon><Folder /></el-icon>
                选择目录
              </el-button>
            </div>
            
            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-top: 16px;"
            >
              <template #default>
                <ul>
                  <li>如果目录不存在，将自动创建</li>
                  <li>如果目录已存在，将保留原有文件</li>
                  <li>将在目录下创建.lingxi 子目录</li>
                </ul>
              </template>
            </el-alert>
          </template>
        </el-result>
      </div>
      
      <div
        v-show="currentStep === 1"
        class="step-2"
      >
        <el-result
          icon="success"
          title="正在初始化工作目录"
          :sub-title="`路径：${workspacePath}`"
        >
          <template #extra>
            <div class="initialization-progress">
              <el-progress
                :percentage="initializationProgress"
                :status="initializationStatus"
              />
              <div class="status-text">
                {{ statusText }}
              </div>
            </div>
          </template>
        </el-result>
      </div>
      
      <div
        v-show="currentStep === 2"
        class="step-3"
      >
        <el-result
          icon="success"
          title="工作目录初始化完成"
          :sub-title="`已创建：${lingxiDir}`"
        >
          <template #extra>
            <div class="created-directories">
              <h4>已创建的目录结构：</h4>
              <ul>
                <li><code>.lingxi/conf/</code> - 存放工作目录配置</li>
                <li><code>.lingxi/data/</code> - 存放数据库文件</li>
                <li><code>.lingxi/skills/</code> - 存放工作目录技能</li>
              </ul>
              
              <el-button
                type="primary"
                @click="openWorkspace"
              >
                打开工作目录
              </el-button>
            </div>
          </template>
        </el-result>
      </div>
    </div>
    
    <template
      v-if="currentStep < 2"
      #footer
    >
      <el-button
        v-if="currentStep === 0"
        @click="handleCancel"
      >
        取消
      </el-button>
      <el-button 
        type="primary" 
        :disabled="!canNext"
        @click="handleNext"
      >
        {{ currentStep === 0 ? '下一步' : '完成' }}
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
const currentStep = ref(0)
const workspacePath = ref('')
const initializationProgress = ref(0)
const initializationStatus = ref<'success' | 'exception'>('success')
const statusText = ref('')
const lingxiDir = ref('')

const canNext = computed(() => {
  if (currentStep.value === 0) {
    return workspacePath.value.length > 0
  }
  return initializationProgress.value === 100
})

watch(() => workspaceStore.initializerVisible, (val) => {
  visible.value = val
  if (val) {
    currentStep.value = 0
    workspacePath.value = ''
    initializationProgress.value = 0
  }
})

watch(visible, (val) => {
  workspaceStore.initializerVisible = val
})

const selectDirectory = async () => {
  const path = await window.electronAPI.file.selectDirectory()
  if (path) {
    workspacePath.value = path
  }
}

const handleNext = async () => {
  if (currentStep.value === 0) {
    currentStep.value = 1
    await initializeWorkspace()
  } else {
    visible.value = false
  }
}

const initializeWorkspace = async () => {
  try {
    statusText.value = '创建目录结构...'
    initializationProgress.value = 30
    
    const result = await window.electronAPI.workspace.initialize(workspacePath.value)
    
    initializationProgress.value = 100
    initializationStatus.value = 'success'
    statusText.value = '初始化完成'
    lingxiDir.value = result.data.lingxi_dir
    
    setTimeout(() => {
      currentStep.value = 2
    }, 500)
    
    ElMessage.success('工作目录初始化成功')
  } catch (error) {
    initializationStatus.value = 'exception'
    statusText.value = '初始化失败'
    ElMessage.error('初始化失败：' + (error as Error).message)
  }
}

const openWorkspace = () => {
  window.electronAPI.file.openExplorer(workspacePath.value)
}

const handleCancel = () => {
  visible.value = false
}
</script>

<style scoped lang="scss">
.directory-selector {
  display: flex;
  gap: 8px;
}

.initialization-progress {
  width: 80%;
  margin: 0 auto;
  
  .status-text {
    text-align: center;
    margin-top: 8px;
    color: #909399;
  }
}

.created-directories {
  h4 {
    margin-bottom: 8px;
  }
  
  ul {
    list-style: none;
    padding: 0;
    
    li {
      margin: 4px 0;
      
      code {
        background: #f5f7fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
      }
    }
  }
}
</style>
