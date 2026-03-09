import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WorkspaceInfo, WorkspaceSwitchResult, WorkspaceInitResult } from '@/types'

export const useWorkspaceStore = defineStore('workspace', () => {
  const currentWorkspace = ref<WorkspaceInfo | null>(null)
  const switchDialogVisible = ref(false)
  const initializerVisible = ref(false)
  const workspaceSkillsCount = ref(0)

  const isInitialized = computed(() => currentWorkspace.value?.is_initialized || false)
  const workspacePath = computed(() => currentWorkspace.value?.workspace || null)
  const lingxiDir = computed(() => currentWorkspace.value?.lingxi_dir || null)

  async function loadCurrentWorkspace() {
    try {
      const result = await window.electronAPI.workspace.getCurrent()
      currentWorkspace.value = result.data
      await loadWorkspaceSkills()
    } catch (error) {
      console.error('加载工作目录失败:', error)
    }
  }

  async function loadWorkspaceSkills() {
    try {
      const skills = await window.electronAPI.api.getSkills()
      workspaceSkillsCount.value = (skills || []).filter(
        skill => skill.source === 'workspace'
      ).length
    } catch (error) {
      console.error('加载工作目录技能失败:', error)
      workspaceSkillsCount.value = 0
    }
  }

  function openSwitchDialog() {
    switchDialogVisible.value = true
  }

  function closeSwitchDialog() {
    switchDialogVisible.value = false
  }

  function openInitializer() {
    initializerVisible.value = true
  }

  function closeInitializer() {
    initializerVisible.value = false
  }

  async function switchWorkspace(path: string, force = false) {
    const result = await window.electronAPI.workspace.switch(path, force)
    if (result.success) {
      await loadCurrentWorkspace()
    }
    return result
  }

  async function initializeWorkspace(path?: string) {
    const result = await window.electronAPI.workspace.initialize(path)
    await loadCurrentWorkspace()
    return result
  }

  return {
    currentWorkspace,
    switchDialogVisible,
    initializerVisible,
    workspaceSkillsCount,
    isInitialized,
    workspacePath,
    lingxiDir,
    loadCurrentWorkspace,
    loadWorkspaceSkills,
    openSwitchDialog,
    closeSwitchDialog,
    openInitializer,
    closeInitializer,
    switchWorkspace,
    initializeWorkspace
  }
})
