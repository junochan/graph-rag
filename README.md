# Graph RAG

基于 NebulaGraph 图数据库的知识图谱检索增强生成 (RAG) 系统。支持自动实体关系抽取、知识图谱构建和混合检索（向量 + 图遍历），通过 LLM 基于检索结果生成答案。

## 架构

```
                         ┌──────────────┐
                         │   Frontend   │
                         │  (Next.js)   │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │  Flask API   │
                         │  /api/build  │
                         │ /api/retrieve│
                         └──────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
     ┌────────▼────────┐ ┌─────▼──────┐  ┌───────▼───────┐
     │    Document      │ │  Embedding │  │     LLM       │
     │    Parser        │ │  Service   │  │   Service     │
     │ (PDF/Word/TXT)   │ │ (OpenAI/..)│  │ (OpenAI/...) │
     └────────┬─────────┘ └─────┬──────┘  └───────┬───────┘
              │                 │                  │
     ┌────────▼─────────┐      │                  │
     │    Entity         │      │                  │
     │    Extractor      │      │                  │
     │    (LLM)          │      │                  │
     └───┬──────────┬────┘      │                  │
         │          │           │                  │
  ┌──────▼──────┐ ┌─▼───────────▼──┐              │
  │ NebulaGraph │ │     Qdrant     │              │
  │ (知识图谱)   │ │   (向量存储)    │              │
  └──────┬──────┘ └───────┬────────┘              │
         │                │                       │
         └────────┬───────┘                       │
          ┌───────▼────────┐                      │
          │ Hybrid Retrieval│──────────────────────┘
          │ (向量 + 图遍历)  │
          └────────────────┘
```

## 实现原理

### 知识构建流程

1. **文档解析** — 将 PDF / Word / 纯文本拆分为文本块 (Chunk)
2. **实体关系抽取** — LLM 从每个文本块中提取实体和关系，映射到预定义的 Schema（8 种 Tag + 12 种 Edge Type）
3. **双存储写入** — 实体和关系写入 NebulaGraph 图数据库；文本块和实体描述生成 Embedding 向量写入 Qdrant

### 混合检索流程

1. **向量召回** — 用户查询经 Embedding 后在 Qdrant 中检索 Top-K 相似节点
2. **图遍历扩展** — 以向量召回的实体为起点，在 NebulaGraph 中进行 N-hop 遍历（默认 2 跳），获取关联上下文
3. **上下文融合** — 合并向量检索结果和图遍历结果，去重后构建结构化上下文
4. **LLM 生成** — 将融合上下文作为 Prompt 的一部分，由 LLM 生成最终答案

### 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| 前端 | Next.js + React + Tailwind | 聊天界面 + 知识图谱可视化 |
| 后端 | Flask + Flask-RESTX | REST API + Swagger 文档 |
| 图数据库 | NebulaGraph | 存储实体和关系 |
| 向量数据库 | Qdrant | 语义相似度检索 |
| LLM / Embedding | OpenAI / Azure / Ollama | 可插拔，支持任意 OpenAI 兼容接口 |

## 安装与部署

### Docker 部署（推荐）

一键部署全部服务（NebulaGraph、Qdrant、后端、前端）：

```bash
# 1. 复制环境变量并填写 API Key
cp .env.docker.example .env

# 2. 启动全部服务
docker compose up -d
```

服务地址：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 Swagger | http://localhost:8008/docs |
| NebulaGraph Studio | http://localhost:7001 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

```bash
# 停止服务
docker compose down

# 停止并清空数据
docker compose down -v

# 重新构建某个服务
docker compose up -d --build backend
```

### 本地开发部署

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填写 NebulaGraph、Qdrant、OpenAI 配置

# 3. 启动 NebulaGraph 和 Qdrant
docker run -d --name nebula -p 9669:9669 -p 19669:19669 vesoft/nebula-graph:v3.6.0
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest

# 4. 初始化图数据库 Schema
uv run python scripts/init_graph.py

# 5. 启动后端
uv run python main.py
```

## License

MIT
