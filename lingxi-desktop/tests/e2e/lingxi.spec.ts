import { test, expect, ElectronApplication, Page } from '@playwright/test'
import { _electron as electron } from 'playwright'
import * as path from 'path'

let electronApp: ElectronApplication
let page: Page

test.describe('灵犀助手 Electron 应用测试', () => {
  
  test.beforeAll(async () => {
    // 项目根目录
    const projectRoot = path.resolve(__dirname, '../../')
    
    // 启动 Electron 应用
    electronApp = await electron.launch({
      // 指向编译后的主进程入口
      args: [path.join(projectRoot, 'dist-electron/main/index.js')],
      cwd: projectRoot,
      env: {
        ...process.env,
        NODE_ENV: 'production'
      }
    })
    
    // 等待窗口出现
    page = await electronApp.firstWindow()
    
    // 等待页面加载完成
    await page.waitForLoadState('domcontentloaded')
    
    // 等待 Vue 应用挂载
    await page.waitForTimeout(2000)
  })
  
  test.afterAll(async () => {
    // 关闭应用 - 添加超时和错误处理
    if (electronApp) {
      try {
        // 先关闭所有页面
        const pages = electronApp.windows()
        for (const p of pages) {
          try {
            await p.close({ timeout: 5000 })
          } catch (e) {
            console.log('关闭页面时出错:', e)
          }
        }
        
        // 然后关闭应用
        await electronApp.close({ timeout: 10000 })
      } catch (error) {
        console.log('关闭应用时出错:', error)
        // 强制终止应用
        try {
          await electronApp.process().kill()
        } catch (killError) {
          console.log('强制终止应用时出错:', killError)
        }
      }
    }
  })
  
  test('应用应该正确启动并显示窗口', async () => {
    // 验证窗口标题
    const title = await page.title()
    expect(title).toBe('Lingxi Agent')
    
    // 還�窗口可见
    const isVisible = await page.isVisible('body')
    expect(isVisible).toBe(true)
    
    // 截图保存
    await page.screenshot({ path: 'test-results/app-startup.png' })
  })
  
  test('应用应该显示标题栏', async () => {
    // 等待标题栏组件加载
    await page.waitForSelector('.title-bar', { timeout: 10000 })
    
    // 验证标题栏存在
    const titleBar = await page.locator('.title-bar')
    await expect(titleBar).toBeVisible()
  })
  
  test('应用应该显示聊天核心组件', async () => {
    // 等待聊天核心组件加载
    await page.waitForSelector('.chat-core', { timeout: 10000 })
    
    // 验证聊天核心组件存在
    const chatCore = await page.locator('.chat-core')
    await expect(chatCore).toBeVisible()
  })
  
  test('应用应该显示输入区域', async () => {
    // 等待输入区域加载
    await page.waitForSelector('.chat-core-input', { timeout: 10000 })
    
    // 验证输入区域存在
    const inputArea = await page.locator('.chat-core-input')
    await expect(inputArea).toBeVisible()
  })
  
  test('应用应该显示布局容器', async () => {
    // 等待布局容器加载
    await page.waitForSelector('.layout-container', { timeout: 10000 })
    
    // 验证布局容器存在
    // 验证布局容器存在
    const layoutContainer = await page.locator('.layout-container')
    await expect(layoutContainer).toBeVisible()
  })
  
  test('应用版本号应该正确', async () => {
    // 获取应用版本
    const version = await electronApp.evaluate(async ({ app }) => {
      return app.getVersion()
    })
    
    // 验证版本号格式
    expect(version).toMatch(/^\d+\.\d+\.\d+$/)
    console.log('应用版本:', version)
  })
  
  test('应用应该能够输入文本', async () => {
    // 等待输入框加载
    const textarea = await page.locator('.chat-input textarea')
    await textarea.waitFor({ timeout: 10000 })
    
    // 验证输入框可见
    await expect(textarea).toBeVisible()
    
    // 输入测试文本
    await textarea.fill('这是一个测试消息')
    
    // 等待 Vue 响应式更新
    await page.waitForTimeout(2000)
    
    // 截图保存输入状态
    await page.screenshot({ path: 'test-results/input-test.png' })
    
    // 验证输入框有内容（不验证具体值）
    const hasContent = await textarea.evaluate((el: HTMLTextAreaElement) => {
      return (el as HTMLTextAreaElement).value.length > 0
    })
    expect(hasContent).toBe(true)
  })
})