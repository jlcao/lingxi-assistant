<template>
  <div class="resume-banner">
    <el-icon class="resume-banner-icon">
      <InfoFilled />
    </el-icon>
    <span class="resume-banner-text">
      您有 {{ activeCheckpoints.length }} 个未完成的任务，点击继续
    </span>
    <el-button
      type="primary"
      size="small"
      link
      @click="handleResume"
    >
      继续任务
    </el-button>
    <el-button
      size="small"
      link
      @click="handleDismiss"
    >
      忽略
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { storeToRefs } from 'pinia'
import { apiService } from '../api/apiService'

const appStore = useAppStore()
const { activeCheckpoints } = storeToRefs(appStore)

async function handleResume() {
  if (activeCheckpoints.value.length > 0) {
    const checkpoint = activeCheckpoints.value[0]
    try {
      await apiService.client.resumeCheckpoint(checkpoint.sessionId)
      ElMessage.success('任务已恢复')
      
      // 刷新 checkpoint 列表
      const checkpoints = await apiService.client.getCheckpoints()
      const formattedCheckpoints = (checkpoints.data.checkpoints || []).map((cp: any) => ({
        id: cp.session_id,
        sessionId: cp.session_id,
        name: cp.state?.task || '未命名任务',
        timestamp: cp.updated_at || Date.now()
      }))
      appStore.setCheckpoints(formattedCheckpoints)
    } catch (error) {
      console.error('Failed to resume checkpoint:', error)
      ElMessage.error('恢复任务失败')
    }
  }
}

async function handleDismiss() {
  if (activeCheckpoints.value.length > 0) {
    const checkpoint = activeCheckpoints.value[0]
    try {
      await apiService.client.deleteCheckpoint(checkpoint.sessionId)
      ElMessage.success('已忽略该任务')
      
      // 刷新 checkpoint 列表
      const checkpoints = await apiService.client.getCheckpoints()
      const formattedCheckpoints = (checkpoints.data.checkpoints || []).map((cp: any) => ({
        id: cp.session_id,
        sessionId: cp.session_id,
        name: cp.state?.task || '未命名任务',
        timestamp: cp.updated_at || Date.now()
      }))
      appStore.setCheckpoints(formattedCheckpoints)
    } catch (error) {
      console.error('Failed to delete checkpoint:', error)
      ElMessage.error('忽略任务失败')
    }
  }
}
</script>

<style scoped lang="scss">
.resume-banner {
  width: 100%;
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  background-color: #ecf5ff;
  border-bottom: 1px solid #d9ecff;
}

.resume-banner-icon {
  margin-right: 8px;
  color: $primary-color;
  font-size: 18px;
}

.resume-banner-text {
  flex: 1;
  font-size: $font-size-small;
  color: $text-primary;
}
</style>
