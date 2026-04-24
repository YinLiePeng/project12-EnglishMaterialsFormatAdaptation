# 英语教学资料智能格式适配与内容纠错工具 - 前端应用

面向全国卷高三/初三英语教师的轻量化网站工具前端应用。

## 技术栈

- **框架**: React 19 + TypeScript
- **构建工具**: Vite 8
- **样式**: Tailwind CSS 4
- **路由**: React Router 7
- **状态管理**: Zustand
- **HTTP客户端**: Axios
- **数据获取**: TanStack React Query

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

应用将运行在: http://localhost:5173

### 3. 构建生产版本

```bash
npm run build
```

构建产物将生成在 `dist/` 目录。

### 4. 预览生产版本

```bash
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── main.tsx                    # 应用入口
│   ├── App.tsx                     # 主应用组件，包含路由配置
│   ├── index.css                   # 全局样式
│   ├── pages/                      # 页面组件
│   │   ├── Home.tsx                # 主页（文件上传）
│   │   ├── Process.tsx             # 处理进度页
│   │   ├── Result.tsx              # 结果页
│   │   ├── TaskList.tsx            # 任务列表页
│   │   ├── TestCase.tsx            # 反馈提交页
│   │   └── TestCaseManagement.tsx  # 测试用例管理页
│   ├── components/                 # 可复用组件
│   │   ├── common/                 # 通用组件
│   │   │   ├── Button.tsx          # 按钮组件
│   │   │   ├── Loading.tsx         # 加载组件
│   │   │   ├── Toast.tsx           # 通知组件
│   │   │   ├── ConfirmDialog.tsx   # 确认对话框
│   │   │   ├── EmptyState.tsx      # 空状态组件
│   │   │   └── ErrorBoundary.tsx   # 错误边界
│   │   ├── upload/                 # 上传相关组件
│   │   │   └── FileDropzone.tsx    # 文件拖拽上传
│   │   └── template/               # 模板相关组件
│   │       ├── ModeSelector.tsx    # 排版模式选择
│   │       └── PresetGallery.tsx   # 预设样式选择
│   ├── services/                   # API服务层
│   │   └── api.ts                  # API调用封装
│   ├── store/                      # 状态管理
│   │   └── uploadStore.ts          # 上传状态管理
│   ├── hooks/                      # 自定义Hooks
│   │   └── useTaskPolling.ts       # 任务轮询Hook
│   ├── contexts/                   # React上下文
│   │   └── ToastContext.tsx         # Toast通知上下文
│   └── types/                      # TypeScript类型定义
│       └── index.ts                # 类型定义
├── public/                         # 静态资源
├── dist/                           # 构建输出
├── package.json                    # 项目依赖
├── vite.config.ts                  # Vite配置
├── tailwind.config.js              # Tailwind配置
├── tsconfig.json                   # TypeScript配置
└── postcss.config.js               # PostCSS配置
```

## 主要功能

### 1. 文件上传与处理
- 支持DOCX格式文件上传
- 支持拖拽上传
- 三种排版模式：无模板、空模板、完整模板
- 处理选项：内容清洗、内容纠错、大模型语义识别

### 2. 任务管理
- 实时处理进度展示
- 任务列表查看和管理
- 任务状态筛选
- 任务详情查看
- 文件下载

### 3. 测试用例收集
- 用户反馈提交
- 测试用例管理
- 状态更新和跟踪

### 4. 用户体验
- 响应式设计
- 实时通知（Toast）
- 错误边界处理
- 加载状态展示

## 开发指南

### 代码规范

```bash
# 运行ESLint检查
npm run lint
```

### API代理配置

开发环境下，API请求会自动代理到后端服务：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### 状态管理

使用Zustand进行状态管理：

```typescript
// 示例：使用uploadStore
import { useUploadStore } from '../store/uploadStore';

function MyComponent() {
  const { file, setFile } = useUploadStore();
  // ...
}
```

### 添加新页面

1. 在 `src/pages/` 目录创建页面组件
2. 在 `src/App.tsx` 中添加路由配置
3. 如需导航，在导航栏中添加链接

### 添加新组件

1. 在 `src/components/` 对应目录创建组件
2. 使用TypeScript定义props接口
3. 导出组件供其他模块使用

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| VITE_API_BASE_URL | API基础URL | /api/v1 |

## 注意事项

1. 开发环境需要后端服务运行在 `http://localhost:8000`
2. 生产环境需要配置正确的API地址
3. 文件上传大小限制为50MB
4. 建议使用现代浏览器（Chrome、Firefox、Edge等）
5. 移动端响应式设计已适配，但建议在桌面端使用以获得最佳体验

## 相关项目

- [后端服务](../backend/README.md) - FastAPI后端服务
- [技术方案](../技术方案及开发任务清单/) - 项目技术方案文档
- [测试用例](../测试用例/) - 测试用例样例
