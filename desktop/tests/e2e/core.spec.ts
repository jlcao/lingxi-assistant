import { test, expect, ElectronApplication, Page } from '@playwright/test'
import { _electron as electron } from 'playwright'
import * as path from 'path'

let electronApp: ElectronApplication
let page: Page

test.describe('灵犀助手核心功能测试', () => {
  
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
    await page.waitForTimeout(2000)
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
  
  test('应用应该正确启动并显示窗口', async () => {
    const title = await page.title()
    expect(title).toBe('Lingxi Agent')
    
    const isVisible = await page.isVisible('body')
    expect(isVisible).toBe(true)
    
    await page.screenshot({ path: 'test-results/core/app-startup.png' })
  })
  
  test('应用应该显示标题栏', async () => {
    await page.waitForSelector('.title-bar', { timeout: 10000 })
    
    const titleBar = await page.locator('.title-bar')
    await expect(titleBar).toBeVisible()
  })
  
  test('应用应该显示聊天核心组件', async () => {
    await page.waitForSelector('.chat-core', { timeout: 10000 })
    
    const chatCore = await page.locator('.chat-core')
    await expect(chatCore).toBeVisible()
  })
  
  test('应用应该显示输入区域', async () => {
    await page.waitForSelector('.chat-core-input', { timeout: 10000 })
    
    const inputArea = await page.locator('.chat-core-input')
    await expect(inputArea).toBeVisible()
  })
  
  test('应用应该显示布局容器', async () => {
    await page.waitForSelector('.layout-container', { timeout: 10000 })
    
    const layoutContainer = await page.locator('.layout-container')
    await expect(layoutContainer).toBeVisible()
  })
  
  test('应用版本号应该正确', async () => {
    const version = await electronApp.evaluate(async ({ app }) => {
      return app.getVersion()
    })
    
    expect(version).toMatch(/^\d+\.\d+\.\d+$/)
    console.log('应用版本:', version)
  })
  
  test('应用应该能够输入文本', async () => {
    const textarea = await page.locator('.chat-input textarea')
    await textarea.waitFor({ timeout: 10000 })
    
    await expect(textarea).toBeVisible()
    
    await textarea.fill('这是一个测试消息')
    await page.waitForTimeout(2000)
    
    await page.screenshot({ path: 'test-results/core/input-test.png' })
    
    const hasContent = await textarea.evaluate((el: HTMLTextAreaElement) => {
      return (el as HTMLTextAreaElement).value.length > 0
    })
    expect(hasContent).toBe(true)
  })
})
