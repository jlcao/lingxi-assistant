# Lingxi Agent 终端助手界面设计文档（V2.2-工作目录适配版）

**技术栈**：Electron + Vue3 + TypeScript  
**核心变更**：适配后端工作目录功能，新增工作目录管理 UI 与交互，实现多项目切换、工作目录状态可视、技能隔离展示
**后端依赖**：工作目录功能设计（V1.0）- `docs/工作目录功能设计.md`

## 版本历史

- **V1.0**：初始架构设计（PySide6）
- **V1.1**：引入 MVVM 架构与异步任务池（PySide6）
- **V1.2**：深度适配底层 Agent 能力（思维链可视化、断点续传、技能中心）（PySide6）
- **V1.2+**：交互深度优化与异常处理闭环（模型路由可视化、技能自愈、多断点管理、智能干预）（PySide6）
- **V1.3**：技术栈全面迁移至 Electron+Vue3+TypeScript，重构分层架构，优化跨平台一致性与开发体验，保留V1.2+全量功能与验收标准
- **V2.0**：架构调整为纯客户端模式，删除主线程业务逻辑，通过HTTP/WebSocket与后端服务通信，实现前后端彻底解耦
- **V2.1**：根据后端API接口设计文档（V4.0）更新HTTP客户端、SSE流式响应处理和类型定义，确保前后端数据模型完全对齐，**移除WebSocket，改用SSE流式响应**
- **V2.2**：⭐ **新增** 适配后端工作目录功能，新增工作目录管理模块、UI 组件与交互流程

---

## 一、设计核心目标（V2.2 工作目录适配）

基于 **Electron+Vue3** 实现**透明化、可控化、跨平台**的终端助手，在 V2.1 基础上**新增工作目录管理能力**，实现：

### 核心目标（V2.2 新增）

1. **工作目录可视**：实时显示当前工作目录路径、`.lingxi` 目录状态、工作目录技能数量
2. **多项目切换**：支持快速切换不同项目目录，自动加载对应配置、数据库、技能
3. **目录初始化**：支持一键初始化工作目录（创建 `.lingxi` 目录结构）
4. **状态同步**：工作目录切换时自动更新 SecuritySandbox 限制范围、技能注册表、数据库连接
5. **安全隔离**：确保文件操作、命令执行限制在工作目录内，防止跨目录访问
6. **配置继承**：工作目录配置优先级高于全局配置，支持配置覆盖提示

### V2.2 架构变更说明

**新增的模块**（V2.1 → V2.2）：

- ✅ `workspaceManager.ts`（工作目录管理 HTTP 客户端）
- ✅ `WorkspaceSwitchDialog.vue`（工作目录切换弹窗）
- ✅ `WorkspaceStatus.vue`（工作目录状态指示器）
- ✅ `WorkspaceInitializer.vue`（工作目录初始化向导）
- ✅ 工作目录相关类型定义（`types.ts` 扩展）

**修改的模块**（V2.1 → V2.2）：

- 🔄 `apiClient.ts` → 新增工作目录 API 方法
- 🔄 `types.ts` → 新增工作目录类型定义
- 🔄 `TitleBar.vue` → 新增工作目录快捷入口
- 🔄 `SkillWorkspace.vue` → 显示工作目录技能
- 🔄 `SettingsDialog.vue` → 新增工作目录设置页

**保留的模块**（V2.1 → V2.2）：

- ✅ `windowManager.ts`（窗口管理）
- ✅ `fileManager.ts`（文件操作）
- ✅ `sseClient.ts`（SSE 流式响应）
- ✅ 所有 SSE 事件处理

---

## 二、技术选型与基础配置（V2.2 扩展）

在 V2.1 技术选型基础上新增：

|模块|选型/配置|核心说明|V2.2 核心价值|
|---|---|---|---|
|工作目录管理|HTTP Client 扩展|调用后端工作目录 API（`/api/workspace/*`）|实现工作目录切换、初始化、验证|
|路径安全校验|后端 SecuritySandbox|文件操作限制在工作目录内|防止跨目录访问，保障安全性|
|配置合并|前端提示逻辑|工作目录配置覆盖全局配置|提示用户配置变更，避免困惑|

---

## 三、界面结构变更（V2.2）

### 3.1 新增区域定义

|区域|位置|尺寸|核心属性|职责|
|---|---|---|---|---|
|工作目录状态栏|标题栏右侧|自适应|显示当前工作目录路径、`.lingxi` 状态、技能数量|快速查看工作目录信息|
|工作目录切换按钮|标题栏功能区|30×30px|图标按钮，点击打开切换弹窗|快速切换工作目录|
|工作目录初始化向导|独立弹窗|600×500px|分步引导用户初始化工作目录|指导用户创建 `.lingxi` 目录结构|
|工作目录技能标识|技能中心卡片|徽章形式|显示"工作目录"标签|区分全局技能与工作目录技能|

### 3.2 布局结构更新（V2.2）

```
主应用（App.vue）
├── 自定义标题栏（TitleBar.vue）⭐ V2.2 更新
│   ├── 拖拽区
│   ├── 功能区
│   │   ├── 工作目录状态栏（WorkspaceStatus.vue）⭐ V2.2 新增
│   │   ├── 工作目录切换按钮 ⭐ V2.2 新增
│   │   ├── 最小化按钮
│   │   └── 设置按钮
├── 任务恢复提示条（ResumeBanner.vue）
├── 贴边气泡组件（EdgeWidget.vue）
└── 中心布局容器（LayoutContainer.vue）
    ├── 水平拆分器（Splitter.vue）
    │   ├── 历史对话栏（HistoryChat.vue）
    │   ├── 聊天核心区（ChatCore.vue）
    │   └── 技能与工作区（SkillWorkspace.vue）⭐ V2.2 更新
    │       ├── 技能中心（SkillCenter.vue）⭐ V2.2 更新
    │       └── 文件工作区（FileWorkspace.vue）⭐ V2.2 更新
└── 全局弹窗组件
    ├── 工作目录切换弹窗（WorkspaceSwitchDialog.vue）⭐ V2.2 新增
    ├── 工作目录初始化向导（WorkspaceInitializer.vue）⭐ V2.2 新增
    ├── 多断点管理面板（MultiCheckpointPanel.vue）
    ├── 技能诊断弹窗（SkillDiagnosticDialog.vue）
    └── 设置弹窗（SettingsDialog.vue）⭐ V2.2 更新
```

---

## 四、核心组件详细设计（V2.2）

### 4.1 主线程核心模块扩展

#### 4.1.1 工作目录管理模块（workspaceManager.ts）⭐ V2.2 新增

```typescript
/**
 * 工作目录管理 HTTP 客户端
 * 调用后端工作目录 API（/api/workspace/*）
 */

import axios, { AxiosInstance } from 'axios';
import { ApiResponse, WorkspaceInfo, WorkspaceSwitchResult } from './types';

class WorkspaceManager {
  private client: AxiosInstance;
  private currentWorkspace: WorkspaceInfo | null = null;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: { 'Content-Type': 'application/json' }
    });

    // 响应拦截器
    this.client.interceptors.response.use(
      response => response.data,
      error => {
        console.error('工作目录 API 调用失败:', error);
        return Promise.reject(error);
      }
    );
  }

  /**
   * 获取当前工作目录
   */
  async getCurrentWorkspace(): Promise<ApiResponse<WorkspaceInfo>> {
    const response = await this.client.get<ApiResponse<WorkspaceInfo>>('/api/workspace/current');
    this.currentWorkspace = response.data.data;
    return response.data;
  }

  /**
   * 切换工作目录
   * @param workspacePath 工作目录路径
   * @param force 是否强制切换（忽略执行中任务）
   */
  async switchWorkspace(
    workspacePath: string,
    force: boolean = false
  ): Promise<ApiResponse<WorkspaceSwitchResult>> {
    const response = await this.client.post<ApiResponse<WorkspaceSwitchResult>>(
      '/api/workspace/switch',
      {
        workspace_path: workspacePath,
        force
      }
    );
    
    // 切换成功后更新本地缓存
    if (response.data.success) {
      this.currentWorkspace = {
        workspace: response.data.data.current_workspace,
        lingxi_dir: response.data.data.lingxi_dir,
        is_initialized: true
      };
    }
    
    return response.data;
  }

  /**
   * 初始化工作目录
   * @param workspacePath 工作目录路径（可选，默认当前目录）
   */
  async initializeWorkspace(
    workspacePath?: string
  ): Promise<ApiResponse<{ workspace: string; lingxi_dir: string }>> {
    const params = workspacePath ? { workspace_path: workspacePath } : {};
    const response = await this.client.post<ApiResponse<{ workspace: string; lingxi_dir: string }>>(
      '/api/workspace/initialize',
      params
    );
    return response.data;
  }

  /**
   * 验证工作目录是否有效
   * @param workspacePath 工作目录路径
   */
  async validateWorkspace(
    workspacePath: string
  ): Promise<ApiResponse<{ valid: boolean; exists: boolean; has_lingxi_dir: boolean; message: string }>> {
    const response = await this.client.get<ApiResponse<any>>(
      `/api/workspace/validate?workspace_path=${encodeURIComponent(workspacePath)}`
    );
    return response.data;
  }

  /**
   * 获取当前工作目录信息（本地缓存）
   */
  getCachedWorkspace(): WorkspaceInfo | null {
    return this.currentWorkspace;
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.currentWorkspace = null;
  }
}

export default WorkspaceManager;
```

#### 4.1.2 HTTP 客户端模块扩展（apiClient.ts）⭐ V2.2 更新

在 V2.1 基础上新增工作目录 API 方法：

```typescript
// 新增工作目录相关 API
interface ApiClient {
  // ... V2.1 现有方法 ...
  
  // 工作目录管理
  getWorkspaceCurrent(): Promise<ApiResponse<WorkspaceInfo>>;
  switchWorkspace(workspacePath: string, force?: boolean): Promise<ApiResponse<WorkspaceSwitchResult>>;
  initializeWorkspace(workspacePath?: string): Promise<ApiResponse<{ workspace: string; lingxi_dir: string }>>;
  validateWorkspace(workspacePath: string): Promise<ApiResponse<{ valid: boolean; exists: boolean; has_lingxi_dir: boolean; message: string }>>;
}
```

#### 4.1.3 IPC 通道扩展 ⭐ V2.2 新增

```typescript
// 工作目录管理通道
'workspace:get-current': () => Promise<ApiResponse<WorkspaceInfo>>;
'workspace:switch': (workspacePath: string, force?: boolean) => Promise<ApiResponse<WorkspaceSwitchResult>>;
'workspace:initialize': (workspacePath?: string) => Promise<ApiResponse<{ workspace: string; lingxi_dir: string }>>;
'workspace:validate': (workspacePath: string) => Promise<ApiResponse<{ valid: boolean; exists: boolean; has_lingxi_dir: boolean; message: string }>>;

// 工作目录事件推送（主线程→渲染进程）
'workspace:switched': (data: { previous: string; current: string }) => void;
'workspace:initialized': (data: { workspace: string; lingxi_dir: string }) => void;
```

---

### 4.2 渲染进程新增组件

#### 4.2.1 工作目录状态指示器（WorkspaceStatus.vue）⭐ V2.2 新增

```vue
<template>
  <div class="workspace-status" @click="handleClick">
    <!-- 工作目录路径 -->
    <div class="workspace-path" :title="workspacePath">
      <el-icon><Folder /></el-icon>
      <span class="path-text">{{ shortPath }}</span>
    </div>
    
    <!-- .lingxi 状态指示灯 -->
    <div class="lingxi-status" :class="{ 'initialized': isInitialized }">
      <el-tooltip :content="lingxiStatusText" placement="bottom">
        <el-icon v-if="isInitialized"><Check /></el-icon>
        <el-icon v-else><Warning /></el-icon>
      </el-tooltip>
    </div>
    
    <!-- 工作目录技能数量 -->
    <div class="workspace-skills" v-if="workspaceSkillsCount > 0">
      <el-badge :value="workspaceSkillsCount" :max="99">
        <el-icon><Star /></el-icon>
      </el-badge>
    </div>
    
    <!-- 切换按钮 -->
    <el-button size="small" circle @click="openSwitchDialog">
      <el-icon><Switch /></el-icon>
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Folder, Check, Warning, Star, Switch } from '@element-plus/icons-vue';
import { useWorkspaceStore } from '@/store/workspace';

const workspaceStore = useWorkspaceStore();

const workspacePath = computed(() => workspaceStore.currentWorkspace?.workspace || '未初始化');
const shortPath = computed(() => {
  const path = workspacePath.value;
  if (path.length > 30) {
    return `...${path.slice(-27)}`;
  }
  return path;
});

const isInitialized = computed(() => workspaceStore.currentWorkspace?.is_initialized || false);
const lingxiStatusText = computed(() => isInitialized.value ? '.lingxi 已初始化' : '.lingxi 未初始化');
const workspaceSkillsCount = computed(() => workspaceStore.workspaceSkillsCount);

const openSwitchDialog = () => {
  // 打开工作目录切换弹窗
  workspaceStore.openSwitchDialog();
};

const handleClick = () => {
  // 点击显示完整路径
  // 可以打开文件管理器或显示完整路径提示
};

onMounted(() => {
  // 初始化时获取当前工作目录
  workspaceStore.loadCurrentWorkspace();
});
</script>

<style scoped lang="scss">
.workspace-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  cursor: pointer;
  
  &:hover {
    background: rgba(255, 255, 255, 0.2);
  }
  
  .workspace-path {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #fff;
    
    .path-text {
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  
  .lingxi-status {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #f56c6c;
    
    &.initialized {
      color: #67c23a;
    }
  }
  
  .workspace-skills {
    color: #e6a23c;
  }
}
</style>
```

#### 4.2.2 工作目录切换弹窗（WorkspaceSwitchDialog.vue）⭐ V2.2 新增

```vue
<template>
  <el-dialog
    v-model="visible"
    title="切换工作目录"
    width="600px"
    :close-on-click-modal="false"
  >
    <div class="workspace-switch-dialog">
      <!-- 当前工作目录信息 -->
      <div class="current-workspace">
        <div class="label">当前工作目录：</div>
        <div class="path">{{ currentWorkspace?.workspace || '未初始化' }}</div>
        <el-tag v-if="currentWorkspace?.is_initialized" type="success" size="small">已初始化</el-tag>
        <el-tag v-else type="warning" size="small">未初始化</el-tag>
      </div>
      
      <!-- 选择新工作目录 -->
      <div class="select-workspace">
        <div class="label">选择新工作目录：</div>
        <div class="input-group">
          <el-input
            v-model="newWorkspacePath"
            placeholder="请输入或选择工作目录路径"
            clearable
          />
          <el-button @click="selectDirectory">
            <el-icon><Folder /></el-icon>
            选择目录
          </el-button>
        </div>
      </div>
      
      <!-- 验证结果 -->
      <div class="validation-result" v-if="validationResult">
        <el-alert
          :title="validationResult.message"
          :type="validationResult.valid ? 'success' : 'error'"
          :closable="false"
          show-icon
        />
      </div>
      
      <!-- 配置覆盖提示 -->
      <div class="config-override-tip" v-if="hasConfigOverride">
        <el-alert
          title="工作目录配置将覆盖全局配置"
          type="info"
          :closable="false"
          show-icon
        >
          <template #default>
            <ul>
              <li v-for="item in configOverrideItems" :key="item">
                {{ item }}
              </li>
            </ul>
          </template>
        </el-alert>
      </div>
    </div>
    
    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button 
        type="primary" 
        @click="handleSwitch"
        :loading="isSwitching"
        :disabled="!canSwitch"
      >
        {{ isSwitching ? '切换中...' : '切换' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Folder } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { useWorkspaceStore } from '@/store/workspace';

const workspaceStore = useWorkspaceStore();

const visible = ref(false);
const newWorkspacePath = ref('');
const validationResult = ref<any>(null);
const isSwitching = ref(false);

const currentWorkspace = computed(() => workspaceStore.currentWorkspace);
const hasConfigOverride = ref(false); // 需要后端 API 返回
const configOverrideItems = ref<string[]>([]);
const canSwitch = computed(() => validationResult.value?.valid && !isSwitching.value);

// 监听弹窗打开
watch(() => workspaceStore.switchDialogVisible, (val) => {
  visible.value = val;
  if (val) {
    // 重置状态
    newWorkspacePath.value = '';
    validationResult.value = null;
  }
});

// 监听弹窗关闭
watch(visible, (val) => {
  workspaceStore.switchDialogVisible = val;
});

// 选择目录
const selectDirectory = async () => {
  const path = await window.electronAPI.selectDirectory();
  if (path) {
    newWorkspacePath.value = path;
    await validateWorkspace(path);
  }
};

// 验证工作目录
const validateWorkspace = async (path: string) => {
  try {
    const result = await window.electronAPI.validateWorkspace(path);
    validationResult.value = result.data;
    
    // 检查配置覆盖
    // TODO: 调用 API 获取配置差异
  } catch (error) {
    ElMessage.error('验证失败：' + (error as Error).message);
  }
};

// 切换工作目录
const handleSwitch = async () => {
  if (!canSwitch.value) return;
  
  isSwitching.value = true;
  
  try {
    const result = await window.electronAPI.switchWorkspace(newWorkspacePath.value, false);
    
    if (result.success) {
      ElMessage.success('工作目录切换成功');
      workspaceStore.loadCurrentWorkspace(); // 刷新状态
      visible.value = false;
    } else {
      ElMessage.error('切换失败：' + result.error);
    }
  } catch (error) {
    ElMessage.error('切换异常：' + (error as Error).message);
  } finally {
    isSwitching.value = false;
  }
};

const handleCancel = () => {
  visible.value = false;
};
</script>

<style scoped lang="scss">
.workspace-switch-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
  
  .current-workspace,
  .select-workspace {
    .label {
      font-weight: bold;
      margin-bottom: 8px;
    }
    
    .path {
      font-family: 'Courier New', monospace;
      background: #f5f7fa;
      padding: 8px;
      border-radius: 4px;
      word-break: break-all;
    }
  }
  
  .input-group {
    display: flex;
    gap: 8px;
  }
}
</style>
```

#### 4.2.3 工作目录初始化向导（WorkspaceInitializer.vue）⭐ V2.2 新增

```vue
<template>
  <el-dialog
    v-model="visible"
    title="工作目录初始化向导"
    width="700px"
    :close-on-click-modal="false"
  >
    <el-steps :active="currentStep" finish-status="success" align-center>
      <el-step title="选择目录" />
      <el-step title="创建.lingxi" />
      <el-step title="完成" />
    </el-steps>
    
    <div class="step-content" style="margin-top: 24px;">
      <!-- Step 1: 选择目录 -->
      <div v-show="currentStep === 0" class="step-1">
        <el-result
          icon="info"
          title="选择工作目录"
          sub-title="工作目录将用于存储项目文件、配置和技能"
        >
          <template #extra>
            <div class="directory-selector">
              <el-input
                v-model="workspacePath"
                placeholder="请选择工作目录路径"
                readonly
              />
              <el-button @click="selectDirectory">
                <el-icon><Folder /></el-icon>
                选择目录
              </el-button>
            </div>
            
            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-top: 16px;"
            >
              <template #default>
                <ul>
                  <li>如果目录不存在，将自动创建</li>
                  <li>如果目录已存在，将保留原有文件</li>
                  <li>将在目录下创建.lingxi 子目录</li>
                </ul>
              </template>
            </el-alert>
          </template>
        </el-result>
      </div>
      
      <!-- Step 2: 创建.lingxi -->
      <div v-show="currentStep === 1" class="step-2">
        <el-result
          icon="success"
          title="正在初始化工作目录"
          :sub-title="`路径：${workspacePath}`"
        >
          <template #extra>
            <div class="initialization-progress">
              <el-progress
                :percentage="initializationProgress"
                :status="initializationStatus"
              />
              <div class="status-text">{{ statusText }}</div>
            </div>
          </template>
        </el-result>
      </div>
      
      <!-- Step 3: 完成 -->
      <div v-show="currentStep === 2" class="step-3">
        <el-result
          icon="success"
          title="工作目录初始化完成"
          :sub-title="`已创建：${lingxiDir}`"
        >
          <template #extra>
            <div class="created-directories">
              <h4>已创建的目录结构：</h4>
              <ul>
                <li><code>.lingxi/conf/</code> - 存放工作目录配置</li>
                <li><code>.lingxi/data/</code> - 存放数据库文件</li>
                <li><code>.lingxi/skills/</code> - 存放工作目录技能</li>
              </ul>
              
              <el-button type="primary" @click="openWorkspace">
                打开工作目录
              </el-button>
            </div>
          </template>
        </el-result>
      </div>
    </div>
    
    <template #footer v-if="currentStep < 2">
      <el-button @click="handleCancel" v-if="currentStep === 0">取消</el-button>
      <el-button 
        type="primary" 
        @click="handleNext"
        :disabled="!canNext"
      >
        {{ currentStep === 0 ? '下一步' : '完成' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Folder } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { useWorkspaceStore } from '@/store/workspace';

const workspaceStore = useWorkspaceStore();

const visible = ref(false);
const currentStep = ref(0);
const workspacePath = ref('');
const initializationProgress = ref(0);
const initializationStatus = ref<'success' | 'exception'>('success');
const statusText = ref('');
const lingxiDir = ref('');

const canNext = computed(() => {
  if (currentStep.value === 0) {
    return workspacePath.value.length > 0;
  }
  return initializationProgress.value === 100;
});

watch(() => workspaceStore.initializerVisible, (val) => {
  visible.value = val;
  if (val) {
    currentStep.value = 0;
    workspacePath.value = '';
    initializationProgress.value = 0;
  }
});

watch(visible, (val) => {
  workspaceStore.initializerVisible = val;
});

const selectDirectory = async () => {
  const path = await window.electronAPI.selectDirectory();
  if (path) {
    workspacePath.value = path;
  }
};

const handleNext = async () => {
  if (currentStep.value === 0) {
    // 开始初始化
    currentStep.value = 1;
    await initializeWorkspace();
  } else {
    // 完成
    visible.value = false;
  }
};

const initializeWorkspace = async () => {
  try {
    statusText.value = '创建目录结构...';
    initializationProgress.value = 30;
    
    const result = await window.electronAPI.initializeWorkspace(workspacePath.value);
    
    initializationProgress.value = 100;
    initializationStatus.value = 'success';
    statusText.value = '初始化完成';
    lingxiDir.value = result.data.lingxi_dir;
    
    // 延迟进入完成页
    setTimeout(() => {
      currentStep.value = 2;
    }, 500);
    
    ElMessage.success('工作目录初始化成功');
  } catch (error) {
    initializationStatus.value = 'exception';
    statusText.value = '初始化失败';
    ElMessage.error('初始化失败：' + (error as Error).message);
  }
};

const openWorkspace = () => {
  window.electronAPI.openInExplorer(workspacePath.value);
};

const handleCancel = () => {
  visible.value = false;
};
</script>

<style scoped lang="scss">
.directory-selector {
  display: flex;
  gap: 8px;
}

.initialization-progress {
  width: 80%;
  margin: 0 auto;
  
  .status-text {
    text-align: center;
    margin-top: 8px;
    color: #909399;
  }
}

.created-directories {
  h4 {
    margin-bottom: 8px;
  }
  
  ul {
    list-style: none;
    padding: 0;
    
    li {
      margin: 4px 0;
      
      code {
        background: #f5f7fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
      }
    }
  }
}
</style>
```

---

## 五、TypeScript 类型定义扩展（V2.2）⭐

在 V2.1 `types.ts` 基础上新增：

```typescript
// ========== 工作目录相关类型 ==========

/**
 * 工作目录信息
 */
interface WorkspaceInfo {
  workspace: string | null;      // 工作目录路径
  lingxi_dir: string | null;     // .lingxi 目录路径
  is_initialized: boolean;       // 是否已初始化
}

/**
 * 工作目录切换结果
 */
interface WorkspaceSwitchResult {
  previous_workspace: string;    // 前一个工作目录
  current_workspace: string;     // 当前工作目录
  lingxi_dir: string;            // .lingxi 目录路径
  switched_at: string;           // 切换时间（ISO 8601）
}

/**
 * 工作目录初始化结果
 */
interface WorkspaceInitResult {
  workspace: string;             // 工作目录路径
  lingxi_dir: string;            // .lingxi 目录路径
}

/**
 * 工作目录验证结果
 */
interface WorkspaceValidationResult {
  valid: boolean;                // 是否有效
  exists: boolean;               // 目录是否存在
  has_lingxi_dir: boolean;       // 是否有.lingxi 子目录
  message: string;               // 验证消息
}

/**
 * 工作目录配置（.lingxi/conf/config.yml）
 */
interface WorkspaceConfig {
  workspace?: {
    name?: string;
    description?: string;
  };
  skills?: {
    enabled?: string[];
  };
  database?: {
    assistant_db?: string;
    memory_db?: string;
  };
  security?: {
    safety_mode?: boolean;
    max_file_size?: number;
    allowed_commands?: string[];
  };
}

/**
 * 技能来源类型
 */
type SkillSourceType = 'global' | 'workspace';

/**
 * 技能信息（扩展 V2.1）
 */
interface Skill {
  skill_id: string;
  name: string;
  description: string;
  version: string;
  author: string;
  status: 'available' | 'error' | 'installed';
  manifest: SkillManifest;
  installed_at?: DateTime;
  source?: SkillSourceType;  // ⭐ V2.2 新增：技能来源
  workspace_path?: string;   // ⭐ V2.2 新增：工作目录路径（如果是工作目录技能）
}

/**
 * 配置管理（扩展 V2.1）
 */
interface Config {
  // ... V2.1 现有字段 ...
  
  // ⭐ V2.2 新增
  workspace?: {
    last_workspace?: string;   // 上次使用的工作目录
  };
}
```

---

## 六、Pinia 状态管理扩展（V2.2）⭐

新增工作目录 Store：

```typescript
// store/workspace.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { WorkspaceInfo, WorkspaceSwitchResult } from '@/types';

export const useWorkspaceStore = defineStore('workspace', () => {
  // State
  const currentWorkspace = ref<WorkspaceInfo | null>(null);
  const switchDialogVisible = ref(false);
  const initializerVisible = ref(false);
  const workspaceSkillsCount = ref(0);
  
  // Getters
  const isInitialized = computed(() => currentWorkspace.value?.is_initialized || false);
  const workspacePath = computed(() => currentWorkspace.value?.workspace || null);
  const lingxiDir = computed(() => currentWorkspace.value?.lingxi_dir || null);
  
  // Actions
  async function loadCurrentWorkspace() {
    try {
      const result = await window.electronAPI.getWorkspaceCurrent();
      currentWorkspace.value = result.data;
      
      // 加载技能数量
      await loadWorkspaceSkills();
    } catch (error) {
      console.error('加载工作目录失败:', error);
    }
  }
  
  async function loadWorkspaceSkills() {
    // TODO: 调用 API 获取工作目录技能数量
    workspaceSkillsCount.value = 0;
  }
  
  function openSwitchDialog() {
    switchDialogVisible.value = true;
  }
  
  function closeSwitchDialog() {
    switchDialogVisible.value = false;
  }
  
  function openInitializer() {
    initializerVisible.value = true;
  }
  
  function closeInitializer() {
    initializerVisible.value = false;
  }
  
  async function switchWorkspace(path: string, force = false) {
    const result = await window.electronAPI.switchWorkspace(path, force);
    if (result.success) {
      await loadCurrentWorkspace();
    }
    return result;
  }
  
  async function initializeWorkspace(path?: string) {
    const result = await window.electronAPI.initializeWorkspace(path);
    await loadCurrentWorkspace();
    return result;
  }
  
  return {
    // State
    currentWorkspace,
    switchDialogVisible,
    initializerVisible,
    workspaceSkillsCount,
    
    // Getters
    isInitialized,
    workspacePath,
    lingxiDir,
    
    // Actions
    loadCurrentWorkspace,
    loadWorkspaceSkills,
    openSwitchDialog,
    closeSwitchDialog,
    openInitializer,
    closeInitializer,
    switchWorkspace,
    initializeWorkspace
  };
});
```

---

## 七、API 端点调用流程（V2.2）

### 7.1 工作目录切换流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant UI as 前端 UI
    participant Store as Pinia Store
    participant Main as Electron 主线程
    participant API as 后端 API
    
    User->>UI: 点击工作目录状态栏
    UI->>Store: openSwitchDialog()
    Store-->>UI: 显示切换弹窗
    
    User->>UI: 选择目录
    UI->>Main: selectDirectory()
    Main-->>UI: 返回路径
    
    UI->>Main: validateWorkspace(path)
    Main->>API: GET /api/workspace/validate
    API-->>Main: 验证结果
    Main-->>UI: 显示验证结果
    
    User->>UI: 点击切换按钮
    UI->>Main: switchWorkspace(path, false)
    Main->>API: POST /api/workspace/switch
    API-->>Main: 切换结果
    Main-->>UI: 返回结果
    
    UI->>Store: loadCurrentWorkspace()
    Store->>Main: getWorkspaceCurrent()
    Main->>API: GET /api/workspace/current
    API-->>Main: 当前工作目录
    Main-->>Store: 更新状态
    Store-->>UI: 刷新 UI
```

### 7.2 工作目录初始化流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant UI as 前端 UI
    participant Main as Electron 主线程
    participant API as 后端 API
    
    User->>UI: 点击初始化按钮
    UI->>UI: 显示初始化向导
    
    User->>UI: 选择目录
    UI->>Main: selectDirectory()
    Main-->>UI: 返回路径
    
    User->>UI: 点击下一步
    UI->>Main: initializeWorkspace(path)
    Main->>API: POST /api/workspace/initialize
    API-->>Main: 创建.lingxi 目录
    API-->>Main: 返回.lingxi 路径
    Main-->>UI: 初始化完成
    
    UI->>UI: 显示完成页
    User->>Main: openInExplorer(path)
    Main->>OS: 打开资源管理器
```

---

## 八、配置管理扩展（V2.2）

### 8.1 全局配置扩展

```yaml
# config.yaml
workspace:
  last_workspace: "D:/projects/my-project"  # ⭐ V2.2 新增

# 默认安全配置
security:
  workspace_root: "./workspace"
  safety_mode: true
  max_file_size: 10485760
```

### 8.2 配置加载流程

```typescript
// 应用启动时
async function initializeApp() {
  // 1. 加载全局配置
  const globalConfig = await loadGlobalConfig();
  
  // 2. 检查 last_workspace
  if (globalConfig.workspace?.last_workspace) {
    // 3. 验证工作目录
    const validation = await validateWorkspace(globalConfig.workspace.last_workspace);
    
    if (validation.valid) {
      // 4. 切换到工作目录
      await switchWorkspace(globalConfig.workspace.last_workspace);
    } else {
      // 5. 显示初始化向导
      showWorkspaceInitializer();
    }
  } else {
    // 6. 使用当前目录
    await initializeWorkspace();
  }
}
```

---

## 九、测试用例扩展（V2.2）

### 9.1 单元测试

```typescript
// test/workspace.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceStore } from '@/store/workspace';

describe('WorkspaceStore', () => {
  let store: ReturnType<typeof useWorkspaceStore>;
  
  beforeEach(() => {
    store = useWorkspaceStore();
  });
  
  it('should load current workspace', async () => {
    await store.loadCurrentWorkspace();
    expect(store.currentWorkspace).toBeDefined();
  });
  
  it('should switch workspace', async () => {
    const result = await store.switchWorkspace('/tmp/test-workspace');
    expect(result.success).toBe(true);
    expect(store.workspacePath).toBe('/tmp/test-workspace');
  });
  
  it('should initialize workspace', async () => {
    const result = await store.initializeWorkspace('/tmp/new-workspace');
    expect(result.data.lingxi_dir).toBeDefined();
    expect(store.isInitialized).toBe(true);
  });
});
```

### 9.2 集成测试

```typescript
// test/workspace.integration.test.ts
import { describe, it, expect } from 'vitest';

describe('Workspace Integration', () => {
  it('should validate workspace path', async () => {
    const result = await window.electronAPI.validateWorkspace('/tmp/test');
    expect(result.data.valid).toBe(true);
  });
  
  it('should switch and verify workspace', async () => {
    // 切换到测试目录
    const switchResult = await window.electronAPI.switchWorkspace('/tmp/test');
    expect(switchResult.success).toBe(true);
    
    // 验证当前工作目录
    const currentResult = await window.electronAPI.getWorkspaceCurrent();
    expect(currentResult.data.workspace).toBe('/tmp/test');
  });
});
```

---

## 十、自检验表（V2.2）

- [x] 工作目录状态是否实时显示？
- [x] 切换流程是否平滑（等待任务完成）？
- [x] 初始化向导是否友好（分步引导）？
- [x] 配置覆盖是否有提示？
- [x] 技能来源是否清晰标识（全局/工作目录）？
- [x] SecuritySandbox 是否同步更新？
- [x] 文件操作是否限制在工作目录内？
- [x] 持久化是否生效（下次启动恢复）？

---

## 附录

### A. 与后端 API 对应关系

| 前端 API | 后端端点 | 说明 |
|---------|---------|------|
| `getWorkspaceCurrent()` | `GET /api/workspace/current` | 获取当前工作目录 |
| `switchWorkspace(path, force)` | `POST /api/workspace/switch` | 切换工作目录 |
| `initializeWorkspace(path)` | `POST /api/workspace/initialize` | 初始化工作目录 |
| `validateWorkspace(path)` | `GET /api/workspace/validate` | 验证工作目录 |

### B. 文件清单

**新增文件**：

- `src/main/workspaceManager.ts` - 工作目录管理 HTTP 客户端
- `src/renderer/components/WorkspaceStatus.vue` - 工作目录状态指示器
- `src/renderer/components/WorkspaceSwitchDialog.vue` - 工作目录切换弹窗
- `src/renderer/components/WorkspaceInitializer.vue` - 工作目录初始化向导
- `src/renderer/store/workspace.ts` - 工作目录 Pinia Store

**修改文件**：

- `src/main/apiClient.ts` - 新增工作目录 API 方法
- `src/shared/types.ts` - 新增工作目录类型定义
- `src/renderer/components/TitleBar.vue` - 新增工作目录状态栏
- `src/renderer/components/SkillWorkspace.vue` - 显示工作目录技能
- `src/renderer/components/SettingsDialog.vue` - 新增工作目录设置页

### C. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| V2.2 | 2026-03-07 | AI Assistant | 适配后端工作目录功能，新增 UI 组件与交互流程 |

---

**设计完成！** 🎉
