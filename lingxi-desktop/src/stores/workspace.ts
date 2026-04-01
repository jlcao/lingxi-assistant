import type { FileChange, WorkspaceFilesChangedEvent, WorkspaceInfo } from '@/types'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useWsStore } from './wsStore'

const DEBOUNCE_MS = 500
const MIN_REFRESH_INTERVAL = 1000

function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null
  return function (this: any, ...args: Parameters<T>) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
      timer = null
    }, delay)
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const currentWorkspace = ref<WorkspaceInfo | null>(null)
  const switchDialogVisible = ref(false)
  const initializerVisible = ref(false)
  const workspaceSkillsCount = ref(0)
  const fileWatcherEnabled = ref(false)
  const lastRefreshTime = ref(0)
  const directoryTreeRefreshCallback = ref<(() => void) | null>(null)

  const isInitialized = computed(() => currentWorkspace.value?.is_initialized || false)
  const workspacePath = computed(() => currentWorkspace.value?.workspace || null)
  const lingxiDir = computed(() => currentWorkspace.value?.lingxi_dir || null)

  async function loadCurrentWorkspace() {
    try {
      console.log('[WorkspaceStore] loadCurrentWorkspace called')
      const result = await window.electronAPI.workspace.getCurrent()
      console.log('[WorkspaceStore] loadCurrentWorkspace result:', result)
      currentWorkspace.value = result
      await loadWorkspaceSkills()
    } catch (error) {
      console.error('[WorkspaceStore] 加载工作目录失败:', error)
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
      await reloadSessions()
    }
    return result
  }

  async function reloadSessions() {
    try {
      // 使用工作目录特定的 API 获取会话列表
      const currentPath = currentWorkspace.value?.workspace
      const sessionsResult = currentPath 
        ? await window.electronAPI.api.getWorkspaceSessions(currentPath)
        : await window.electronAPI.api.getSessions()
      console.log('获取到的会话列表:', sessionsResult)
      // 处理返回结果
      const sessions = sessionsResult.sessions || (sessionsResult as any[])
      const formattedSessions = (sessions || []).map((session: any) => ({
        sessionId: session.sessionId || session.id,
        title: session.title || session.name || '新会话',
        userName: session.user_name || '用户',
        tasks: [],
        totalTokens: 0,
        createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
        updatedAt: session.updated_at ? new Date(session.updated_at).getTime() : Date.now()
      }))

      const { useAppStore } = await import('@/stores/app')
      const appStore = useAppStore()
      appStore.setSessions(formattedSessions)

      if (formattedSessions && formattedSessions.length > 0) {
        appStore.setCurrentSession(formattedSessions[0].id)
      } else {
        appStore.setCurrentSession(null)
        appStore.setTurns([])
      }

      console.log(`工作区切换完成，已加载 ${formattedSessions.length} 个会话`)
    } catch (error) {
      console.error('重新加载会话失败:', error)
    }
  }

  async function initializeWorkspace(path?: string) {
    const result = await window.electronAPI.workspace.initialize(path)
    await loadCurrentWorkspace()
    return result
  }

  function setDirectoryTreeRefreshCallback(callback: () => void) {
    directoryTreeRefreshCallback.value = callback
  }

  function shouldRefresh(changes: FileChange[]): boolean {
    if (fileWatcherEnabled.value) {
      return false
    }
    return changes.length > 0
  }

  async function refreshDirectoryTree(changes?: FileChange[]) {
    const now = Date.now()
    if (now - lastRefreshTime.value < MIN_REFRESH_INTERVAL) {
      console.log('[Workspace] 刷新节流，跳过本次刷新')
      return
    }

    if (directoryTreeRefreshCallback.value) {
      console.log('[Workspace] 触发目录树刷新，变动:', changes)
      directoryTreeRefreshCallback.value()
      lastRefreshTime.value = now
    }
  }

  const debouncedRefresh = debounce(async (changes: FileChange[]) => {
    await refreshDirectoryTree(changes)
  }, DEBOUNCE_MS)

  function handleWorkspaceFilesChanged(event: WorkspaceFilesChangedEvent) {
    const { source, changes } = event

    console.log('[Workspace] 收到文件变动事件:', { source, changes: changes?.length })

    if (source === 'file_watcher') {
      refreshDirectoryTree(changes)
    } else {
      if (shouldRefresh(changes)) {
        debouncedRefresh(changes)
      }
    }
  }

  function setupFileChangeListener() {
    const wsStore = useWsStore()
    wsStore.onWorkspaceFilesChanged((data: WorkspaceFilesChangedEvent) => {
      handleWorkspaceFilesChanged(data)
    })
    console.log('[Workspace] 文件变动监听器已设置')
  }

  return {
    currentWorkspace,
    switchDialogVisible,
    initializerVisible,
    workspaceSkillsCount,
    isInitialized,
    workspacePath,
    lingxiDir,
    fileWatcherEnabled,
    lastRefreshTime,
    loadCurrentWorkspace,
    loadWorkspaceSkills,
    openSwitchDialog,
    closeSwitchDialog,
    openInitializer,
    closeInitializer,
    switchWorkspace,
    initializeWorkspace,
    setDirectoryTreeRefreshCallback,
    refreshDirectoryTree,
    setupFileChangeListener,
    handleWorkspaceFilesChanged
  }
})
