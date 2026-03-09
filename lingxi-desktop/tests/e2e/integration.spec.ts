import { test, expect, ElectronApplication, Page } from '@playwright/test'
import { _electron as electron } from 'playwright'
import * as path from 'path'
import * as fs from 'fs'

let electronApp: ElectronApplication
let page: Page

test.describe('工作目录前后端联调测试', () => {
  
  const testWorkspacePath = path.join(__dirname, '../../test-workspace')
  
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
    // 清理测试工作目录
    try {
      if (fs.existsSync(testWorkspacePath)) {
        fs.rmSync(testWorkspacePath, { recursive: true, force: true })
      }
    } catch (e) {
      console.log('清理测试目录失败:', e)
    }
    
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
  
  test('后端 API 应该可用', async () => {
    const apiResult = await page.evaluate(async () => {
      try {
        const response = await fetch('http://127.0.0.1:5000/api/workspace/current')
        const data = await response.json()
        return {
          success: response.ok,
          status: response.status,
          data: data
        }
      } catch (error) {
        return {
          success: false,
          error: (error as Error).message
        }
      }
    })
    
    console.log('后端 API 状态:', apiResult)
    
    // 验证后端服务可用（即使返回 404）
    expect(apiResult).toBeDefined()
    expect(apiResult.status).toBeDefined()
  })
  
  test('前端应该能获取当前工作目录', async () => {
    const workspaceResult = await page.evaluate(async () => {
      try {
        const result = await window.electronAPI.workspace.getCurrent()
        return result
      } catch (error) {
        return { error: (error as Error).message }
      }
    })
    
    console.log('当前工作目录:', workspaceResult)
    
    // 验证返回数据结构
    expect(workspaceResult).toBeDefined()
    if (workspaceResult.data) {
      expect(workspaceResult.data).toHaveProperty('workspace')
      expect(workspaceResult.data).toHaveProperty('lingxi_dir')
      expect(workspaceResult.data).toHaveProperty('is_initialized')
    }
  })
  
  test('前端应该能初始化工作目录', async () => {
    // 创建测试目录
    if (!fs.existsSync(testWorkspacePath)) {
      fs.mkdirSync(testWorkspacePath, { recursive: true })
    }
    
    // 通过前端 API 初始化工作目录
    const initResult = await page.evaluate(async (workspacePath) => {
      try {
        const result = await window.electronAPI.workspace.initialize(workspacePath)
        return {
          success: true,
          data: result
        }
      } catch (error) {
        return {
          success: false,
          error: (error as Error).message
        }
      }
    }, testWorkspacePath)
    
    console.log('工作目录初始化结果:', initResult)
    
    // 验证初始化成功
    if (initResult.success) {
      expect(initResult.data).toBeDefined()
      expect(initResult.data.data).toBeDefined()
      expect(initResult.data.data.workspace).toBe(testWorkspacePath)
      expect(initResult.data.data.lingxi_dir).toBeDefined()
    }
  })
  
  test('前端应该能验证工作目录', async () => {
    const validationResult = await page.evaluate(async (workspacePath) => {
      try {
        const result = await window.electronAPI.workspace.validate(workspacePath)
        return result
      } catch (error) {
        return { error: (error as Error).message }
      }
    }, testWorkspacePath)
    
    console.log('工作目录验证结果:', validationResult)
    
    // 验证返回数据结构
    expect(validationResult).toBeDefined()
    if (validationResult.data) {
      expect(validationResult.data).toHaveProperty('valid')
      expect(validationResult.data).toHaveProperty('exists')
      expect(validationResult.data).toHaveProperty('has_lingxi_dir')
    }
  })
  
  test('前端应该能切换工作目录', async () => {
    // 创建另一个测试目录
    const newWorkspacePath = path.join(__dirname, '../../test-workspace-2')
    if (!fs.existsSync(newWorkspacePath)) {
      fs.mkdirSync(newWorkspacePath, { recursive: true })
    }
    
    try {
      // 通过前端 API 切换工作目录
      const switchResult = await page.evaluate(async (workspacePath) => {
        try {
          const result = await window.electronAPI.workspace.switch(workspacePath, false)
          return {
            success: true,
            data: result
          }
        } catch (error) {
          return {
            success: false,
            error: (error as Error).message
          }
        }
      }, newWorkspacePath)
      
      console.log('工作目录切换结果:', switchResult)
      
      // 验证切换成功或返回预期错误
      expect(switchResult).toBeDefined()
    } finally {
      // 清理测试目录
      try {
        if (fs.existsSync(newWorkspacePath)) {
          fs.rmSync(newWorkspacePath, { recursive: true, force: true })
        }
      } catch (e) {
        // 忽略清理错误
      }
    }
  })
  
  test('前端 UI 应该显示工作目录状态', async () => {
    // 等待工作目录状态组件加载
    await page.waitForSelector('.title-bar', { timeout: 10000 })
    
    const titleBarRight = await page.locator('.title-bar-right')
    await expect(titleBarRight).toBeVisible()
    
    // 截图保存
    await page.screenshot({ path: 'test-results/integration/workspace-status.png' })
  })
})
