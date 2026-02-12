# Changelog

本项目所有值得注意的变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- **Docker 容器化部署** — 新增 `Dockerfile`（后端/前端）、`docker-compose.yml`，支持一键 `docker compose up` 启动全栈服务
- **暗色主题** — 完善暗色模式切换，包括 ReactFlow 图可视化、Controls、MiniMap 的暗色适配，切换时带平滑过渡动画
- **图扩展深度控制** — 图谱搜索新增 1/2/3 跳深度选择，避免搜索时展示过多无关节点
- **Markdown 增强** — 支持 GFM（表格、任务列表），集成 `rehype-sanitize` 防止 XSS
- **组件拆分** — `ChatInterface` 拆分为 `ChatMessages`、`ChatInput`、`ChatSettings` 及 `useStreamQuery` hook

### 优化

- **图可视化** — 圆形布局替换为力导向布局；节点选中不再触发全图重排；新增 MiniMap、缩放控制、键盘导航（Escape 取消选中）
- **搜索/筛选性能** — `filteredNodes`、`filteredEdges`、`outgoingEdges`、`incomingEdges` 使用 `useMemo` 优化
- **自动滚动** — `ScrollArea` 替换为原生 `div + overflow-auto`，配合 `scrollIntoView` 解决滚动失效问题
- **首页卡片** — 整个卡片可点击（原仅按钮可点），hover 时带箭头动效

### 修复

- `use_llm` 默认值统一为 `True`，非流式端点补充 `history` 参数传递
- 非流式 `retrieve` 接口增加 `try/except` 错误处理
- `MessageBubble` 中 `setTimeout` 在组件卸载时正确清理，防止内存泄漏
- 搜索实体时结果中缺失起始实体本身的问题（后端 `GraphExpansionService.expand` + 前端双端修复）
- GitHub 链接指向正确仓库地址

## [0.1.0] - 2026-02-10

### 新增

- **知识图谱构建** — 支持文本和文件（PDF/DOCX/TXT）导入，LLM 自动提取实体与关系
- **三种检索模式** — `vector`（向量）、`graph`（图）、`hybrid`（混合）
- **多跳推理** — 支持自然语言查询的多跳关系推理
- **LLM 回答生成** — 基于检索上下文生成准确答案
- **流式输出（SSE）** — 对话响应实时流式返回
- **多轮对话** — 聊天历史记录传递，支持上下文连续对话
- **图谱可视化** — 基于 ReactFlow 的交互式知识图谱浏览
- **Swagger API 文档** — Flask-RESTX 自动生成 API 文档
- **GitHub Actions CI** — 后端 ruff/mypy 检查，前端 ESLint + 构建验证

### 技术栈

- **后端**: Python 3.10+ / Flask / Flask-RESTX / Pydantic
- **前端**: Next.js 15 / React 19 / TypeScript / Tailwind CSS / shadcn/ui
- **图数据库**: NebulaGraph
- **向量数据库**: Qdrant
- **LLM/Embedding**: OpenAI 兼容接口
- **包管理**: uv（后端）/ npm（前端）

[Unreleased]: https://github.com/junochan/graph-rag/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/junochan/graph-rag/releases/tag/v0.1.0
