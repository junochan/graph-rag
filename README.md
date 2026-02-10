# Graph RAG

基于 NebulaGraph 图数据库的知识图谱检索增强生成 (RAG) 系统。参考 Microsoft GraphRAG 和 RAG-Anything 的设计理念，支持自动实体关系抽取、知识图谱构建和混合检索。

## 特性

- **知识图谱构建**: 使用 LLM 自动抽取实体和关系，构建知识图谱
- **多格式支持**: 支持文本、PDF、Word (.docx) 文件上传
- **图数据库**: NebulaGraph 存储，预定义 Schema (Tags/Edge Types)
- **向量检索**: Qdrant 向量库，支持语义相似搜索
- **混合检索**: 结合向量检索和图遍历的 GraphRAG 风格检索
- **LLM 问答**: 基于检索结果生成答案
- **API 文档**: 内置 Swagger UI

## 架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Document      │────▶│   Entity        │────▶│   Knowledge     │
│   Parser        │     │   Extractor     │     │   Graph         │
│  (PDF/Word/TXT) │     │   (LLM)         │     │  (NebulaGraph)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌─────────────────┐             │
                        │   Vector        │◀────────────┘
                        │   Store         │
                        │   (Qdrant)      │
                        └─────────────────┘
                                │
                        ┌───────▼─────────┐
                        │   Hybrid        │
                        │   Retrieval     │
                        │ (Vector+Graph)  │
                        └─────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或手动安装
uv venv && source .venv/bin/activate
uv pip install -e .
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env 设置 NebulaGraph、Qdrant、OpenAI 配置
```

### 3. 启动依赖服务

```bash
# NebulaGraph
docker run -d --name nebula-standalone \
  -p 9669:9669 -p 19669:19669 -p 19670:19670 \
  vesoft/nebula-graph:v3.6.0

# Qdrant
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  qdrant/qdrant:latest
```

### 4. 初始化 Schema

**方式一：使用初始化脚本（推荐）**

```bash
# 使用默认配置
uv run python scripts/init_graph.py

# 自定义配置
uv run python scripts/init_graph.py \
  --host 192.168.1.100 \
  --port 9669 \
  --space my_knowledge_graph \
  --user root \
  --password nebula
```

脚本参数：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 127.0.0.1 | NebulaGraph 主机 |
| `--port` | 9669 | NebulaGraph 端口 |
| `--user` | root | 用户名 |
| `--password` | nebula | 密码 |
| `--space` | graph_rag | 图空间名称 |
| `--partition-num` | 10 | 分区数 |
| `--replica-factor` | 1 | 副本因子 |
| `--skip-indexes` | - | 跳过创建索引 |

**方式二：通过 API 初始化**

```bash
curl -X POST http://localhost:5000/api/build/init-schema \
  -H "Content-Type: application/json" \
  -d '{"space": "graph_rag"}'
```

### 5. 启动服务

```bash
uv run python main.py
```

访问 Swagger UI: `http://localhost:5000/docs`

## API 接口

### 构建接口 (`/api/build`)

#### 初始化 Schema

**POST /api/build/init-schema**

初始化图空间和 Schema（首次使用必须调用）。

```json
{
  "space": "graph_rag",
  "partition_num": 10,
  "replica_factor": 1
}
```

预定义的 Tags:
- `entity` - 通用实体
- `person` - 人物
- `organization` - 组织
- `location` - 地点
- `event` - 事件
- `concept` - 概念
- `document` - 源文档
- `chunk` - 文本块

预定义的 Edge Types:
- `related_to` - 相关
- `belongs_to` - 属于
- `located_in` - 位于
- `works_for` - 工作于
- `created_by` - 创建
- `part_of` - 组成部分
- `causes` - 导致
- `uses` - 使用
- `mentions` - 提及
- `similar_to` - 相似
- `contains` - 包含
- `extracted_from` - 抽取自

#### 从文本构建

**POST /api/build/text**

```json
{
  "text": "张三是阿里巴巴的高级工程师，他在杭州工作。阿里巴巴是一家科技公司，总部位于杭州。",
  "source_name": "example.txt",
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

响应:

```json
{
  "success": true,
  "document_id": "doc_abc123",
  "chunks_count": 1,
  "entities_count": 4,
  "relationships_count": 3,
  "processing_time": 2.5,
  "errors": []
}
```

#### 从文件构建

**POST /api/build/file**

支持 PDF、DOCX、TXT、MD 文件上传。

```bash
curl -X POST http://localhost:5000/api/build/file \
  -F "file=@document.pdf" \
  -F "chunk_size=1000"
```

### 检索接口 (`/api/retrieve`)

#### 混合检索

**POST /api/retrieve/**

```json
{
  "query": "张三在哪家公司工作？",
  "top_k": 10,
  "search_type": "hybrid",
  "expand_graph": true,
  "graph_depth": 2,
  "use_llm": true
}
```

响应:

```json
{
  "success": true,
  "query": "张三在哪家公司工作？",
  "results": [
    {
      "id": "e_abc123",
      "name": "张三",
      "type": "entity",
      "score": 0.95,
      "text": "张三: 阿里巴巴的高级工程师"
    }
  ],
  "graph_context": {
    "nodes": [
      {"id": "e_def456", "name": "阿里巴巴", "type": "organization"}
    ],
    "edges": [
      {"source": "e_abc123", "target": "e_def456", "type": "works_for"}
    ]
  },
  "answer": "根据知识图谱，张三在阿里巴巴公司工作，职位是高级工程师。",
  "sources": ["example.txt"]
}
```

#### 图查询

**POST /api/retrieve/graph-query**

直接执行 nGQL 查询：

```json
{
  "query": "MATCH (p:person)-[e:works_for]->(o:organization) RETURN p, e, o LIMIT 10",
  "space": "graph_rag"
}
```

#### 列出实体

**GET /api/retrieve/entities?type=person&limit=50**

## 配置说明

通过 `.env` 文件配置，使用 `__` 分隔嵌套配置：

```bash
# 应用配置
DEBUG=true
PORT=5000

# NebulaGraph
NEBULA__HOSTS=["127.0.0.1:9669"]
NEBULA__USERNAME=root
NEBULA__PASSWORD=nebula
NEBULA__SPACE=graph_rag

# Qdrant
VECTOR_STORE__TYPE=qdrant
VECTOR_STORE__QDRANT_HOST=localhost
VECTOR_STORE__QDRANT_PORT=6333

# Embedding (OpenAI 兼容接口)
EMBEDDING__TYPE=openai
EMBEDDING__OPENAI_API_KEY=sk-xxx
EMBEDDING__OPENAI_API_BASE=https://api.openai.com/v1
EMBEDDING__OPENAI_MODEL=text-embedding-3-small

# LLM (OpenAI 兼容接口)
LLM__TYPE=openai
LLM__OPENAI_API_KEY=sk-xxx
LLM__OPENAI_API_BASE=https://api.openai.com/v1
LLM__OPENAI_MODEL=gpt-4o-mini
```

## 项目结构

```
graph-rag/
├── main.py                          # 主入口
├── pyproject.toml                   # 依赖配置
├── .env.example                     # 环境变量示例
├── scripts/
│   └── init_graph.py                # 图数据库初始化脚本
└── src/
    ├── app.py                       # Flask 应用
    ├── config/
    │   └── settings.py              # 配置管理
    ├── api/
    │   ├── build.py                 # 构建接口
    │   └── retrieve.py              # 检索接口
    └── services/
        ├── document_parser.py       # 文档解析
        ├── entity_extractor.py      # 实体抽取
        ├── graph_schema.py          # Schema 管理
        ├── graph_store.py           # NebulaGraph 服务
        ├── knowledge_builder.py     # 知识图谱构建
        ├── vector_store.py          # 向量库服务
        ├── embedding.py             # Embedding 服务
        └── llm.py                   # LLM 服务
```

## 工作流程

1. **初始化**: 调用 `/api/build/init-schema` 创建图空间和 Schema
2. **构建**: 
   - 上传文件或提交文本到 `/api/build/file` 或 `/api/build/text`
   - 系统自动解析文档、分块、使用 LLM 抽取实体关系
   - 存入 NebulaGraph (图) 和 Qdrant (向量)
3. **检索**:
   - 调用 `/api/retrieve/` 进行混合检索
   - 向量搜索找到相关内容
   - 图遍历扩展上下文
   - 可选 LLM 生成答案

## 测试

### 单元测试

```bash
# 运行所有测试
uv run pytest tests/ -v -s

# 运行知识图谱测试
uv run pytest tests/test_knowledge_graph.py -v -s
```

### 多跳推理测试

测试知识图谱的多跳推理能力：

```bash
# 运行多跳推理测试脚本
uv run python scripts/test_multi_hop.py

# 自定义参数
uv run python scripts/test_multi_hop.py --host localhost --port 5000 --space test_space

# 跳过构建（使用已有数据）
uv run python scripts/test_multi_hop.py --skip-build

# 不使用 LLM 生成答案
uv run python scripts/test_multi_hop.py --no-llm
```

测试内容包括：
- **1-hop**: 张三 → 阿里巴巴 (works_for)
- **2-hop**: 张三 → 阿里巴巴 → 杭州 (works_for → located_in)
- **3-hop**: 张三 → 李四 → 腾讯 → 深圳 (knows → works_for → located_in)

## License

MIT
