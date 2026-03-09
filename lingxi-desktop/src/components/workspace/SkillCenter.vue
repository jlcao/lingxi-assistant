<template>
  <div class="skill-center">
    <div class="skill-center-header">
      <span class="skill-center-title">技能中心</span>
      <el-button
        :icon="Upload"
        size="small"
        @click="handleInstallSkill"
      >
        安装技能
      </el-button>
    </div>
    <div class="skill-center-grid">
      <div
        v-for="skill in skills"
        :key="skill.id"
        class="skill-card"
        :class="skill.status"
        @click="handleSkillClick(skill)"
      >
        <div class="skill-card-icon">
          <el-icon v-if="skill.icon" :size="32">
            <component :is="skill.icon" />
          </el-icon>
          <el-icon v-else :size="32"><Grid /></el-icon>
        </div>
        <div class="skill-card-info">
          <div class="skill-card-name">{{ skill.name }}</div>
          <div class="skill-card-description">{{ skill.description }}</div>
          <div class="skill-card-meta">
            <span class="skill-card-version">v{{ skill.version }}</span>
            <span class="skill-card-author">{{ skill.author }}</span>
          </div>
          <div class="skill-card-source" v-if="skill.source">
            <el-tag v-if="skill.source === 'workspace'" type="warning" size="small">工作目录</el-tag>
            <el-tag v-else type="info" size="small">全局</el-tag>
          </div>
        </div>
        <div class="skill-card-status">
          <el-icon v-if="skill.status === 'available'" color="#67c23a"><CircleCheck /></el-icon>
          <el-icon v-else-if="skill.status === 'error'" color="#f56c6c"><CircleClose /></el-icon>
          <el-icon v-else color="#409eff"><Loading /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Upload, Grid, CircleCheck, CircleClose, Loading } from '@element-plus/icons-vue'
import type { Skill } from '../../types'

const skills = ref<Skill[]>([])

onMounted(async () => {
  await loadSkills()
})

async function loadSkills() {
  try {
    const data = await window.electronAPI.api.getSkills()
    skills.value = data
  } catch (error) {
    console.error('Failed to load skills:', error)
  }
}

function handleInstallSkill() {
  console.log('Install skill')
}

function handleSkillClick(skill: Skill) {
  console.log('Skill clicked:', skill)
}
</script>

<style scoped lang="scss">
.skill-center {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.skill-center-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.skill-center-title {
  font-size: $font-size-base;
  font-weight: 500;
  color: $text-primary;
}

.skill-center-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  overflow-y: auto;
}

.skill-card {
  position: relative;
  padding: 16px;
  background-color: $bg-color;
  border: 1px solid $border-lighter;
  border-radius: $border-radius-base;
  cursor: pointer;
  transition: $transition-base;

  &:hover {
    border-color: $primary-color;
    box-shadow: $shadow-base;
  }

  &.error {
    border-color: $danger-color;
  }
}

.skill-card-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: $bg-page;
  border-radius: $border-radius-base;
  margin-bottom: 12px;
  color: $primary-color;
}

.skill-card-info {
  flex: 1;
}

.skill-card-name {
  font-size: $font-size-base;
  font-weight: 500;
  color: $text-primary;
  margin-bottom: 4px;
}

.skill-card-description {
  font-size: $font-size-small;
  color: $text-secondary;
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.skill-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.skill-card-version {
  font-size: $font-size-small;
  color: $text-secondary;
  background-color: $bg-page;
  padding: 2px 6px;
  border-radius: 2px;
}

.skill-card-author {
  font-size: $font-size-small;
  color: $text-secondary;
}

.skill-card-source {
  margin-top: 8px;
}

.skill-card-status {
  position: absolute;
  top: 8px;
  right: 8px;
}
</style>
