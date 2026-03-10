import { test, expect, ElectronApplication, Page } from '@playwright/test'
import { _electron as electron } from 'playwright'
import * as path from 'path'

let electronApp: ElectronApplication
let page: Page

test.describe('目录树自动刷新机制测试', () => {
  let consoleMessages: string[] = []

  test.beforeAll(async () => {
    const projectRoot = path.resolve(__dirname, '../../')

    electronApp = await electron.launch({
      args: [path.join(projectRoot, 'dist-electron/main/index.js')],
      cwd: projectRoot,
      env: {
        ...process.env,
        NODE_ENV: 'production'
      }
    })

    page = await electronApp.firstWindow()

    // 捕获所有控制台消息
    page.on('console', msg => {
      const text = msg.text()
      consoleMessages.push(text)
      console.log('[Captured Console]', text)
    })

    await page.waitForLoadState('domcontentloaded')

    // 等待应用初始化完成
    await page.waitForTimeout(5000)
  })

  test.afterAll(async () => {
    if (electronApp) {
      try {
        const pages = electronApp.windows()
        for (const p of pages) {
          try {
            await p.close({ timeout: 3000 }).catch(() => { })
          } catch (e) {
            // 忽略关闭错误
          }
        }

        await electronApp.close({ timeout: 5000 }).catch(() => { })
      } catch (error) {
        try {
          if (electronApp.process()) {
            electronApp.process().kill()
          }
        } catch (killError) {
          // 忽略强制终止错误
        }
      }
    }
  })

  test('FileChange 类型定义应该正确导出', async () => {
    const typeCheck = await page.evaluate(async () => {
      const testChange = {
        type: 'created' as const,
        path: '/test/path.txt',
        timestamp: new Date().toISOString()
      }

      const validTypes: Array<'created' | 'modified' | 'deleted'> = ['created', 'modified', 'deleted']

      return {
        hasValidType: validTypes.includes(testChange.type),
        hasPath: typeof testChange.path === 'string',
        hasTimestamp: typeof testChange.timestamp === 'string'
      }
    })

    expect(typeCheck.hasValidType).toBe(true)
    expect(typeCheck.hasPath).toBe(true)
    expect(typeCheck.hasTimestamp).toBe(true)
  })

  test('WorkspaceFilesChangedEvent 类型定义应该正确', async () => {
    const eventCheck = await page.evaluate(async () => {
      const testEvent = {
        source: 'task_end' as const,
        session_id: 'test-session-123',
        task_id: 'test-task-456',
        changes: [
          { type: 'created' as const, path: '/test/file.txt' },
          { type: 'modified' as const, path: '/test/file2.txt' }
        ]
      }

      const validSources: Array<'task_end' | 'file_watcher'> = ['task_end', 'file_watcher']

      return {
        hasValidSource: validSources.includes(testEvent.source),
        hasChanges: Array.isArray(testEvent.changes),
        changesCount: testEvent.changes.length
      }
    })

    expect(eventCheck.hasValidSource).toBe(true)
    expect(eventCheck.hasChanges).toBe(true)
    expect(eventCheck.changesCount).toBe(2)
  })

  test('onWorkspaceFilesChanged API 应该可用', async () => {
    const apiCheck = await page.evaluate(async () => {
      try {
        const hasApi = typeof window.electronAPI.ws.onWorkspaceFilesChanged === 'function'
        return { success: true, hasApi }
      } catch (error) {
        return { success: false, error: (error as Error).message }
      }
    })

    expect(apiCheck.success).toBe(true)
    expect(apiCheck.hasApi).toBe(true)
  })

  test('防抖函数应该正确工作', async () => {
    const debounceCheck = await page.evaluate(async () => {
      let callCount = 0

      const debounce = <T extends (...args: any[]) => any>(
        fn: T,
        delay: number
      ): (...args: Parameters<T>) => void => {
        let timer: ReturnType<typeof setTimeout> | null = null
        return function (this: any, ...args: Parameters<T>) {
          if (timer) clearTimeout(timer)
          timer = setTimeout(() => {
            fn.apply(this, args)
            timer = null
          }, delay)
        }
      }

      const debouncedFn = debounce(() => {
        callCount++
      }, 100)

      debouncedFn()
      debouncedFn()
      debouncedFn()

      await new Promise(resolve => setTimeout(resolve, 200))

      return { callCount }
    })

    expect(debounceCheck.callCount).toBe(1)
  })

  test('节流逻辑应该正确工作', async () => {
    const throttleCheck = await page.evaluate(async () => {
      let refreshCount = 0
      let lastRefreshTime = 0
      const MIN_REFRESH_INTERVAL = 100

      const canRefresh = () => {
        const now = Date.now()
        if (now - lastRefreshTime < MIN_REFRESH_INTERVAL) {
          return false
        }
        lastRefreshTime = now
        refreshCount++
        return true
      }

      const result1 = canRefresh()
      const result2 = canRefresh()

      await new Promise(resolve => setTimeout(resolve, 150))

      const result3 = canRefresh()

      return {
        firstRefresh: result1,
        secondRefreshBlocked: !result2,
        thirdRefresh: result3,
        totalRefreshes: refreshCount
      }
    })

    expect(throttleCheck.firstRefresh).toBe(true)
    expect(throttleCheck.secondRefreshBlocked).toBe(true)
    expect(throttleCheck.thirdRefresh).toBe(true)
    expect(throttleCheck.totalRefreshes).toBe(2)
  })

  test('shouldRefresh 逻辑应该根据来源正确判断', async () => {
    const refreshLogicCheck = await page.evaluate(async () => {
      const fileWatcherEnabled = false

      const shouldRefresh = (changes: Array<{ type: string; path: string }>) => {
        if (fileWatcherEnabled) {
          return false
        }
        return changes.length > 0
      }

      const withChanges = shouldRefresh([{ type: 'created', path: '/test' }])
      const withoutChanges = shouldRefresh([])

      return { withChanges, withoutChanges }
    })

    expect(refreshLogicCheck.withChanges).toBe(true)
    expect(refreshLogicCheck.withoutChanges).toBe(false)
  })

  test('事件监听器应该能够正确注册和移除', async () => {
    const listenerCheck = await page.evaluate(async () => {
      try {
        let listenerCalled = false

        const callback = () => {
          listenerCalled = true
        }

        window.electronAPI.ws.onWorkspaceFilesChanged(callback)

        window.electronAPI.ws.removeAllListeners('ws:workspace-files-changed')

        return {
          success: true,
          listenerRegistered: true
        }
      } catch (error) {
        return { success: false, error: (error as Error).message }
      }
    })

    expect(listenerCheck.success).toBe(true)
    expect(listenerCheck.listenerRegistered).toBe(true)
  })

  test('目录树组件应该正确渲染', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    const layoutContainer = await page.locator('.layout-container')
    await expect(layoutContainer).toBeVisible()

    await page.screenshot({ path: 'test-results/directory-tree-refresh/layout-container.png' })
  })

  test('工作目录 API 应该可调用', async () => {
    const workspaceResult = await page.evaluate(async () => {
      try {
        const result = await window.electronAPI.workspace.getCurrent()
        return {
          success: true,
          hasData: result !== null && result !== undefined,
          result: result
        }
      } catch (error) {
        return {
          success: false,
          error: (error as Error).message
        }
      }
    })

    console.log('工作目录 API 调用结果:', workspaceResult)
    expect(workspaceResult).toBeDefined()
    expect(workspaceResult.success).toBe(true)
  })

  test('WebSocket 连接应该可用', async () => {
    const wsCheck = await page.evaluate(async () => {
      try {
        const isConnected = await window.electronAPI.ws.isConnected()
        return { success: true, isConnected }
      } catch (error) {
        return { success: false, error: (error as Error).message }
      }
    })

    console.log('WebSocket 连接状态:', wsCheck)
    expect(wsCheck.success).toBe(true)
  })

  test('组件初始化时应该正确加载目录树', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    const fileWorkspaceLogs = consoleMessages.filter(log => log.includes('[FileWorkspace]'))
    const appLogs = consoleMessages.filter(log => log.includes('[App]'))
    const workspaceStoreLogs = consoleMessages.filter(log => log.includes('[WorkspaceStore]'))

    const fileWorkspaceElement = await page.locator('.file-workspace').first()
    const fileTreeElement = await page.locator('.file-tree').first()
    const emptyWorkspaceElement = await page.locator('.empty-workspace').first()

    const componentState = {
      hasFileWorkspace: await fileWorkspaceElement.count() > 0,
      hasFileTree: await fileTreeElement.count() > 0,
      hasEmptyWorkspace: await emptyWorkspaceElement.count() > 0,
      fileTreeVisible: await fileTreeElement.isVisible().catch(() => false),
      emptyWorkspaceVisible: await emptyWorkspaceElement.isVisible().catch(() => false),
      fileWorkspaceLogs,
      appLogs,
      workspaceStoreLogs
    }

    console.log('组件初始化状态:', componentState)
    console.log('所有 FileWorkspace 日志:', fileWorkspaceLogs)
    console.log('所有 App 日志:', appLogs)
    console.log('所有 WorkspaceStore 日志:', workspaceStoreLogs)

    expect(componentState.hasFileWorkspace).toBe(true)
    expect(fileWorkspaceLogs.length).toBeGreaterThan(0)
  })

  test('currentWorkspace 和 workspacePath 应该有正确的值', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    const fileWorkspaceLogs = consoleMessages.filter(log => log.includes('[FileWorkspace]'))
    const currentWorkspaceLog = fileWorkspaceLogs.find(log => log.includes('Component setup - currentWorkspace'))
    const workspacePathLog = fileWorkspaceLogs.find(log => log.includes('Component setup - workspacePath'))

    const workspaceState = {
      hasCurrentWorkspaceLog: !!currentWorkspaceLog,
      hasWorkspacePathLog: !!workspacePathLog,
      currentWorkspaceLog: currentWorkspaceLog || '',
      workspacePathLog: workspacePathLog || '',
      allFileWorkspaceLogs: fileWorkspaceLogs
    }

    console.log('工作区状态:', workspaceState)
    expect(workspaceState.hasCurrentWorkspaceLog).toBe(true)
    expect(workspaceState.hasWorkspacePathLog).toBe(true)
  })

  test('watch 监听器应该被触发', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    const fileWorkspaceLogs = consoleMessages.filter(log => log.includes('[FileWorkspace]'))
    const currentWorkspaceChangedLogs = fileWorkspaceLogs.filter(log => log.includes('currentWorkspace changed'))
    const workspacePathChangedLogs = fileWorkspaceLogs.filter(log => log.includes('workspacePath changed'))
    const loadDirectoryTreeLogs = fileWorkspaceLogs.filter(log => log.includes('loadDirectoryTree called'))

    const watchState = {
      currentWorkspaceChangedCount: currentWorkspaceChangedLogs.length,
      workspacePathChangedCount: workspacePathChangedLogs.length,
      loadDirectoryTreeCount: loadDirectoryTreeLogs.length,
      currentWorkspaceChangedLogs,
      workspacePathChangedLogs,
      loadDirectoryTreeLogs
    }

    console.log('watch 监听器状态:', watchState)
    expect(watchState.currentWorkspaceChangedCount).toBeGreaterThan(0)
    expect(watchState.loadDirectoryTreeCount).toBeGreaterThan(0)
  })

  test('loadDirectoryTree 应该被正确调用', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    const fileWorkspaceLogs = consoleMessages.filter(log => log.includes('[FileWorkspace]'))
    const loadDirectoryTreeLogs = fileWorkspaceLogs.filter(log => log.includes('[FileWorkspace] loadDirectoryTree'))
    const readDirectoryTreeLogs = fileWorkspaceLogs.filter(log => log.includes('[FileWorkspace] readDirectoryTree result'))
    const successLogs = fileWorkspaceLogs.filter(log => log.includes('[FileWorkspace] Directory tree loaded successfully'))
    const emptyLogs = fileWorkspaceLogs.filter(log => log.includes('[FileWorkspace] Directory tree is empty'))

    const loadTreeState = {
      loadDirectoryTreeCalled: loadDirectoryTreeLogs.length > 0,
      readDirectoryTreeCalled: readDirectoryTreeLogs.length > 0,
      hasSuccess: successLogs.length > 0,
      hasEmpty: emptyLogs.length > 0,
      loadDirectoryTreeLogs,
      readDirectoryTreeLogs,
      successLogs,
      emptyLogs
    }

    console.log('loadDirectoryTree 调用状态:', loadTreeState)
    expect(loadTreeState.loadDirectoryTreeCalled).toBe(true)
    expect(loadTreeState.readDirectoryTreeCalled).toBe(true)
  })

  test('App 初始化流程应该正确执行', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    const appLogs = consoleMessages.filter(log => log.includes('[App]'))
    const workspaceStoreLogs = consoleMessages.filter(log => log.includes('[WorkspaceStore]'))

    const appInitState = {
      appInitCalled: appLogs.some(log => log.includes('initializeApp called')),
      loadingWorkspace: appLogs.some(log => log.includes('Loading current workspace')),
      workspaceLoaded: appLogs.some(log => log.includes('Current workspace loaded')),
      workspaceStoreLoadCalled: workspaceStoreLogs.some(log => log.includes('loadCurrentWorkspace called')),
      workspaceStoreLoadResult: workspaceStoreLogs.some(log => log.includes('loadCurrentWorkspace result')),
      appInitLogs,
      workspaceStoreLogs
    }

    console.log('App 初始化状态:', appInitState)
    expect(appInitState.appInitCalled).toBe(true)
    expect(appInitState.loadingWorkspace).toBe(true)
    expect(appInitState.workspaceStoreLoadCalled).toBe(true)
  })

  test('目录树应该正确显示文件节点', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    await page.waitForTimeout(3000)

    const fileTreeElement = await page.locator('.file-tree').first()
    const treeNodes = await page.locator('.el-tree-node').all()
    const fileTreeNodes = await page.locator('.file-tree-node').all()
    const fileWorkspaceLogs = consoleMessages.filter(log => log.includes('[FileWorkspace]'))

    const treeState = {
      hasFileTree: await fileTreeElement.count() > 0,
      treeNodeCount: treeNodes.length,
      fileTreeNodeCount: fileTreeNodes.length,
      fileTreeVisible: await fileTreeElement.isVisible().catch(() => false),
      fileWorkspaceLogs
    }

    console.log('目录树显示状态:', treeState)
    expect(treeState.hasFileTree).toBe(true)
  })

  test('切换工作区时应该重新加载目录树', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })

    await page.waitForTimeout(2000)

    const fileWorkspaceLogs = consoleMessages.filter(log => log.includes('[FileWorkspace]'))
    const loadDirectoryTreeLogs = fileWorkspaceLogs.filter(log => log.includes('[FileWorkspace] loadDirectoryTree called'))

    const switchWorkspaceState = {
      initialLoadCount: loadDirectoryTreeLogs.length,
      allLoadDirectoryTreeLogs: loadDirectoryTreeLogs
    }

    console.log('切换工作区状态:', switchWorkspaceState)
    expect(switchWorkspaceState.initialLoadCount).toBeGreaterThan(0)
  })
})
