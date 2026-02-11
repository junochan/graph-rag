# Graph RAG Web 前端

基于 Next.js + TypeScript + shadcn/ui 的知识图谱 RAG 系统前端界面。

## 功能特性

- **对话检索** - 类 ChatGPT 的对话界面，支持自然语言问答
- **来源展示** - 清晰展示向量检索和图谱推理的数据来源
- **知识库构建** - 拖拽上传文件，自动构建知识图谱
- **图谱可视化** - 交互式知识图谱展示，支持节点筛选和详情查看

## 技术栈

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Flow (图谱可视化)
- Lucide Icons

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.local.example .env.local

# 编辑 .env.local 配置后端 API 地址
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 4. 构建生产版本

```bash
npm run build
npm start
```

## 项目结构

```
web/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # 全局布局
│   │   ├── page.tsx            # 首页
│   │   ├── chat/page.tsx       # 对话检索页
│   │   ├── build/page.tsx      # 知识库构建页
│   │   └── graph/page.tsx      # 图谱可视化页
│   ├── components/
│   │   ├── ui/                 # shadcn 组件
│   │   ├── chat/               # 对话相关组件
│   │   ├── build/              # 构建相关组件
│   │   ├── graph/              # 图谱相关组件
│   │   └── layout/             # 布局组件
│   └── lib/
│       ├── api.ts              # API 调用封装
│       ├── types.ts            # TypeScript 类型
│       └── utils.ts            # 工具函数
├── .env.local                  # 环境变量
└── package.json
```

## 页面说明

### 首页 (/)

系统概览和功能入口。

### 对话检索 (/chat)

- 支持三种检索模式：混合、向量、图
- 每条回答展示数据来源
- 可折叠的来源详情面板
- 预设问题快速开始

### 构建知识库 (/build)

- 拖拽上传文件 (PDF, DOCX, TXT, MD)
- 文本直接输入
- 实时显示构建进度
- 展示提取的实体和关系数量

### 图谱可视化 (/graph)

- React Flow 交互式图谱
- 节点按类型着色
- 支持搜索和类型筛选
- 点击节点查看详情

## 后端 API

前端依赖后端 Flask API，需确保后端服务运行：

```bash
# 在项目根目录
uv run python main.py
```

后端 API 文档: http://localhost:5000/docs
