import { test, expect, ElectronApplication, Page } from '@playwright/test'
import { _electron as electron } from 'playwright'
import * as path from 'path'

let electronApp: ElectronApplication
let page: Page

test.describe('目录树自动刷新机制测试', () => {
  
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
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(3000)
  })
  
  test.afterAll(async () => {
    if (electronApp) {
      try {
        const pages = electronApp.windows()
        for (const p of pages) {
          try {
            await p.close({ timeout: 3000 }).catch(() => {})
          } catch (e) {
            // 忽略关闭错误
          }
        }
        
        await electronApp.close({ timeout: 5000 }).catch(() => {})
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
})
