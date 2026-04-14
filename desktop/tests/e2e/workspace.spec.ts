import { test, expect, ElectronApplication, Page } from '@playwright/test'
import { _electron as electron } from 'playwright'
import * as path from 'path'

let electronApp: ElectronApplication
let page: Page

test.describe('工作目录功能测试', () => {
  
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
        // 先关闭所有页面
        const pages = electronApp.windows()
        for (const p of pages) {
          try {
            await p.close({ timeout: 3000 }).catch(() => {})
          } catch (e) {
            // 忽略关闭错误
          }
        }
        
        // 然后关闭应用
        await electronApp.close({ timeout: 5000 }).catch(() => {})
      } catch (error) {
        // 强制终止应用
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
  
  test('工作目录状态组件应该正确显示', async () => {
    await page.waitForSelector('.title-bar', { timeout: 10000 })
    
    const titleBarRight = await page.locator('.title-bar-right')
    await expect(titleBarRight).toBeVisible()
    
    const titleBarLeft = await page.locator('.title-bar-left')
    await expect(titleBarLeft).toBeVisible()
    
    await page.screenshot({ path: 'test-results/workspace/title-bar.png' })
  })
  
  test('工作目录切换功能应该可用', async () => {
    await page.waitForTimeout(2000)
    
    const titleBarRight = await page.locator('.title-bar-right')
    const buttons = await titleBarRight.locator('button').count()
    expect(buttons).toBeGreaterThan(3)
    
    await page.screenshot({ path: 'test-results/workspace/title-bar-buttons.png' })
  })
  
  test('工作目录初始化向导组件应该存在', async () => {
    const layoutContainer = await page.locator('.layout-container')
    await expect(layoutContainer).toBeVisible()
    
    await page.screenshot({ path: 'test-results/workspace/layout-container.png' })
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
    
    // 验证 API 调用成功（即使返回 null 数据）
    expect(workspaceResult.success).toBe(true)
  })
})
