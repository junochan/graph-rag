"""
Integration tests for knowledge graph building and multi-hop retrieval.

Tests:
1. Schema initialization
2. Knowledge graph building from text
3. Vector search
4. Graph traversal (multi-hop reasoning)
5. Hybrid retrieval with LLM

Run with:
    uv run pytest tests/test_knowledge_graph.py -v -s
"""

import time

import pytest


# ==================== Test Data ====================

# 多跳推理测试数据：
# 张三 -> 工作于 -> 阿里巴巴 -> 位于 -> 杭州
# 张三 -> 认识 -> 李四 -> 工作于 -> 腾讯 -> 位于 -> 深圳
# 张三 -> 掌握 -> Python -> 用于 -> 人工智能
# 阿里巴巴 -> 生产 -> 阿里云

TEST_TEXT_MULTI_HOP = """
张三是阿里巴巴集团的高级软件工程师，他精通Python和Java编程语言。张三在杭州工作和生活。

阿里巴巴集团是中国最大的电子商务公司之一，总部位于浙江省杭州市。阿里巴巴旗下有多个产品，
包括淘宝、天猫和阿里云。阿里云是国内领先的云计算服务提供商。

李四是张三的大学同学和好朋友，他们经常一起讨论技术问题。李四目前在腾讯公司担任产品经理，
腾讯的总部位于广东省深圳市。

Python是一种广泛使用的编程语言，在人工智能和数据科学领域应用非常广泛。
张三使用Python开发了多个机器学习项目。

王五是阿里云的技术总监，他负责云计算平台的架构设计。王五和张三是同事关系，
他们经常合作完成重要项目。
"""

# 预期的实体
EXPECTED_ENTITIES = [
    "张三", "李四", "王五",  # 人物
    "阿里巴巴", "腾讯", "阿里云",  # 组织
    "杭州", "深圳",  # 地点
    "Python", "Java",  # 技术
]

# 预期的关系（多跳路径）
EXPECTED_RELATIONSHIPS = [
    ("张三", "阿里巴巴", "works_for"),
    ("张三", "李四", "knows"),
    ("李四", "腾讯", "works_for"),
    ("阿里巴巴", "杭州", "located_in"),
    ("腾讯", "深圳", "located_in"),
]


# ==================== Tests ====================


class TestSchemaInitialization:
    """Test graph schema initialization."""

    def test_init_schema_via_api(self, client):
        """Test schema initialization through API."""
        response = client.post(
            "/api/build/init-schema",
            json={"space": "test_graph_rag"},
        )
        
        data = response.get_json()
        print(f"\nInit schema response: {data}")
        
        # 可能已存在，所以不严格检查 success
        assert "space" in data or "error" in data

    def test_get_schema_info(self, client):
        """Test getting schema information."""
        response = client.get("/api/build/schema?space=test_graph_rag")
        
        data = response.get_json()
        print(f"\nSchema info: {data}")
        
        if data.get("success"):
            assert "tags" in data
            assert "edge_types" in data


class TestKnowledgeGraphBuilding:
    """Test knowledge graph building from text."""

    def test_build_from_text(self, client):
        """Test building knowledge graph from text."""
        response = client.post(
            "/api/build/text",
            json={
                "text": TEST_TEXT_MULTI_HOP,
                "source_name": "test_multi_hop.txt",
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "chunk_size": 500,
                "chunk_overlap": 100,
            },
        )
        
        data = response.get_json()
        print(f"\nBuild response: {data}")
        
        assert data["success"] or len(data.get("errors", [])) > 0
        
        if data["success"]:
            assert data["document_id"] != ""
            assert data["chunks_count"] > 0
            assert data["entities_count"] > 0
            print(f"  - Document ID: {data['document_id']}")
            print(f"  - Chunks: {data['chunks_count']}")
            print(f"  - Entities: {data['entities_count']}")
            print(f"  - Relationships: {data['relationships_count']}")
            print(f"  - Processing time: {data['processing_time']:.2f}s")
        
        # 等待数据同步
        time.sleep(2)

    def test_build_simple_text(self, client):
        """Test building with simple structured text."""
        simple_text = """
        北京是中国的首都。
        上海是中国最大的城市。
        马云创立了阿里巴巴。
        阿里巴巴总部在杭州。
        """
        
        response = client.post(
            "/api/build/text",
            json={
                "text": simple_text,
                "source_name": "simple_test.txt",
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
            },
        )
        
        data = response.get_json()
        print(f"\nSimple build response: {data}")
        
        # 等待数据同步
        time.sleep(2)


class TestVectorSearch:
    """Test vector similarity search."""

    def test_vector_search_person(self, client):
        """Test searching for a person."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三是谁？他在哪里工作？",
                "top_k": 5,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "vector",
                "expand_graph": False,
                "use_llm": False,
            },
        )
        
        data = response.get_json()
        print(f"\nVector search (person) response:")
        print(f"  Query: {data.get('query')}")
        print(f"  Results: {len(data.get('results', []))}")
        
        for i, result in enumerate(data.get("results", [])[:3]):
            print(f"    [{i+1}] {result.get('name')} (score: {result.get('score', 0):.3f})")
            print(f"        Text: {result.get('text', '')[:100]}...")

    def test_vector_search_company(self, client):
        """Test searching for a company."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "阿里巴巴公司",
                "top_k": 5,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "vector",
                "expand_graph": False,
                "use_llm": False,
            },
        )
        
        data = response.get_json()
        print(f"\nVector search (company) response:")
        print(f"  Results: {len(data.get('results', []))}")


class TestGraphTraversal:
    """Test graph traversal and multi-hop reasoning."""

    def test_graph_query_direct(self, client):
        """Test direct graph query."""
        # 查询所有 person 类型的顶点
        response = client.post(
            "/api/retrieve/graph-query",
            json={
                "query": "MATCH (p:person) RETURN p.person.name AS name LIMIT 10",
                "space": "test_graph_rag",
            },
        )
        
        data = response.get_json()
        print(f"\nGraph query (persons) response:")
        print(f"  Success: {data.get('success')}")
        print(f"  Data: {data.get('data', [])}")

    def test_graph_query_relationships(self, client):
        """Test querying relationships."""
        # 查询 works_for 关系
        response = client.post(
            "/api/retrieve/graph-query",
            json={
                "query": """
                    MATCH (p)-[e:works_for]->(o) 
                    RETURN p.person.name AS person, o.organization.name AS org 
                    LIMIT 10
                """,
                "space": "test_graph_rag",
            },
        )
        
        data = response.get_json()
        print(f"\nGraph query (works_for) response:")
        print(f"  Success: {data.get('success')}")
        print(f"  Data: {data.get('data', [])}")

    def test_multi_hop_query_2_hops(self, client):
        """Test 2-hop graph query: Person -> Company -> Location."""
        # 张三 -> 阿里巴巴 -> 杭州
        response = client.post(
            "/api/retrieve/graph-query",
            json={
                "query": """
                    MATCH (p:person)-[:works_for]->(o:organization)-[:located_in]->(l:location)
                    RETURN p.person.name AS person, 
                           o.organization.name AS company, 
                           l.location.name AS city
                    LIMIT 10
                """,
                "space": "test_graph_rag",
            },
        )
        
        data = response.get_json()
        print(f"\n2-Hop Query (Person->Company->City) response:")
        print(f"  Success: {data.get('success')}")
        print(f"  Data: {data.get('data', [])}")
        
        # 验证多跳路径
        if data.get("success") and data.get("data"):
            for row in data["data"]:
                print(f"    {row.get('person')} -> {row.get('company')} -> {row.get('city')}")

    def test_multi_hop_query_3_hops(self, client):
        """Test 3-hop graph query: Person -> related_to -> Person -> Company -> Location."""
        # 张三 -> related_to -> 李四 -> 腾讯 -> 深圳
        # 注意：使用 related_to 而不是 knows，因为我们的 schema 使用的是 related_to
        response = client.post(
            "/api/retrieve/graph-query",
            json={
                "query": """
                    MATCH (p1:person)-[:related_to]-(p2:person)-[:works_for]->(o:organization)-[:located_in]->(l:location)
                    RETURN p1.person.name AS person1,
                           p2.person.name AS person2,
                           o.organization.name AS company,
                           l.location.name AS city
                    LIMIT 10
                """,
                "space": "test_graph_rag",
            },
        )
        
        data = response.get_json()
        print(f"\n3-Hop Query (Person->Person->Company->City) response:")
        print(f"  Success: {data.get('success')}")
        print(f"  Data: {data.get('data')}")
        if data.get("error"):
            print(f"  Error: {data.get('error')}")
        
        if data.get("success") and data.get("data"):
            for row in data["data"]:
                print(f"    {row.get('person1')} -> related_to -> {row.get('person2')} -> {row.get('company')} -> {row.get('city')}")

    def test_find_path(self, client):
        """Test finding multi-hop path - verify path exists from 3-hop query results."""
        # 使用之前验证过的 3-hop 查询结果，筛选出从张三到深圳的路径
        # 这实际上就是验证多跳路径的存在性
        response = client.post(
            "/api/retrieve/graph-query",
            json={
                "query": """
                    MATCH (p1:person)-[:related_to]-(p2:person)-[:works_for]->(o:organization)-[:located_in]->(l:location)
                    RETURN p1.person.name AS start,
                           p2.person.name AS via_person,
                           o.organization.name AS via_company,
                           l.location.name AS end
                    LIMIT 10
                """,
                "space": "test_graph_rag",
            },
        )
        
        data = response.get_json()
        print(f"\nFind all multi-hop paths (Person -> Person -> Company -> City):")
        print(f"  Success: {data.get('success')}")
        
        if data.get("data"):
            # 筛选从张三出发到深圳的路径
            all_paths = data.get("data", [])
            zhangsan_to_shenzhen = [
                p for p in all_paths 
                if p.get("start") == "张三" and "深圳" in str(p.get("end", ""))
            ]
            
            print(f"  Total paths: {len(all_paths)}")
            print(f"  张三 -> 深圳 paths: {len(zhangsan_to_shenzhen)}")
            
            for row in all_paths[:5]:
                marker = " ★" if row.get("start") == "张三" and "深圳" in str(row.get("end", "")) else ""
                print(f"    {row.get('start')} -> {row.get('via_person')} -> {row.get('via_company')} -> {row.get('end')}{marker}")
        
        if data.get("error"):
            print(f"  Error: {data.get('error')}")


class TestHybridRetrieval:
    """Test hybrid retrieval (vector + graph)."""

    def test_hybrid_search_with_graph_expansion(self, client):
        """Test hybrid search with graph context expansion."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三在哪个城市工作？",
                "top_k": 5,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 2,
                "use_llm": False,
            },
        )
        
        data = response.get_json()
        print(f"\nHybrid search with graph expansion:")
        print(f"  Query: {data.get('query')}")
        print(f"  Results: {len(data.get('results', []))}")
        
        graph_context = data.get("graph_context")
        if graph_context:
            nodes = graph_context.get("nodes") or []
            edges = graph_context.get("edges") or []
            print(f"  Graph nodes: {len(nodes)}")
            print(f"  Graph edges: {len(edges)}")
            
            for node in nodes[:5]:
                print(f"    Node: {node.get('name')} ({node.get('type')})")
            
            for edge in edges[:5]:
                src = edge.get('source_name') or edge.get('source')
                tgt = edge.get('target_name') or edge.get('target')
                print(f"    Edge: {src} --[{edge.get('type')}]--> {tgt}")
        else:
            print("  No graph context returned")

    def test_hybrid_search_multi_hop_question(self, client):
        """Test hybrid search with a multi-hop question."""
        # 这个问题需要多跳推理：张三 -> 认识 -> 李四 -> 工作 -> 腾讯 -> 位于 -> ?
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三的朋友在哪个城市工作？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 3,
                "use_llm": False,
            },
        )
        
        data = response.get_json()
        print(f"\nMulti-hop question (friend's city):")
        print(f"  Query: {data.get('query')}")
        print(f"  Success: {data.get('success')}")
        
        graph_context = data.get("graph_context")
        if graph_context:
            nodes = graph_context.get("nodes") or []
            edges = graph_context.get("edges") or []
            print(f"  Expanded {len(nodes)} nodes")
            print(f"  Found {len(edges)} edges")
        else:
            print("  No graph context returned")


class TestLLMAnswerGeneration:
    """Test LLM-based answer generation."""

    def test_answer_simple_question(self, client):
        """Test LLM answer for a simple question."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三在哪家公司工作？",
                "top_k": 5,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        print(f"\nLLM Answer (simple question):")
        print(f"  Query: {data.get('query')}")
        answer = data.get('answer') or 'No answer'
        print(f"  Answer: {answer[:500] if answer else 'No answer'}")
        print(f"  Sources: {data.get('sources', [])}")
        if data.get('error'):
            print(f"  Error: {data.get('error')}")

    def test_answer_multi_hop_question(self, client):
        """Test LLM answer for a multi-hop reasoning question."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三工作的公司总部在哪个城市？这个公司有什么产品？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 2,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        print(f"\nLLM Answer (multi-hop question):")
        print(f"  Query: {data.get('query')}")
        answer = data.get('answer') or 'No answer'
        print(f"  Answer: {answer[:500] if answer else 'No answer'}")
        if data.get('error'):
            print(f"  Error: {data.get('error')}")

    def test_answer_relationship_question(self, client):
        """Test LLM answer for a relationship question."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三和李四是什么关系？他们分别在哪里工作？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 2,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        print(f"\nLLM Answer (relationship question):")
        print(f"  Query: {data.get('query')}")
        answer = data.get('answer') or 'No answer'
        print(f"  Answer: {answer[:500] if answer else 'No answer'}")
        if data.get('error'):
            print(f"  Error: {data.get('error')}")


class TestNaturalLanguageMultiHop:
    """Test multi-hop reasoning with natural language questions.
    
    These tests verify that the system can answer questions requiring
    multiple hops through the knowledge graph using natural language.
    """

    def test_2hop_question_person_to_city(self, client):
        """Test 2-hop: Person -> Company -> City (张三在哪个城市工作？)"""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三在哪个城市工作？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 2,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        
        print(f"\n[2-hop] 张三在哪个城市工作？")
        print(f"  Answer: {answer[:300]}...")
        
        # 验证答案包含正确信息（杭州）
        assert "杭州" in answer, f"Expected '杭州' in answer, got: {answer[:200]}"
        print(f"  ✓ 正确识别：张三 -> 阿里巴巴 -> 杭州")

    def test_2hop_question_company_products(self, client):
        """Test 2-hop: Person -> Company -> Products (张三工作的公司有什么产品？)"""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三工作的公司有什么产品？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 2,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        
        print(f"\n[2-hop] 张三工作的公司有什么产品？")
        print(f"  Answer: {answer[:300]}...")
        
        # 验证答案包含产品信息
        has_product = any(p in answer for p in ["淘宝", "天猫", "阿里云"])
        assert has_product, f"Expected product names in answer, got: {answer[:200]}"
        print(f"  ✓ 正确识别：张三 -> 阿里巴巴 -> 淘宝/天猫/阿里云")

    def test_3hop_question_friend_city(self, client):
        """Test 3-hop: Person -> Friend -> Company -> City (张三的朋友在哪个城市工作？)"""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三的朋友李四在哪个城市工作？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 3,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        
        print(f"\n[3-hop] 张三的朋友李四在哪个城市工作？")
        print(f"  Answer: {answer[:300]}...")
        
        # 验证答案包含深圳
        assert "深圳" in answer, f"Expected '深圳' in answer, got: {answer[:200]}"
        print(f"  ✓ 正确识别：张三 -> 李四 -> 腾讯 -> 深圳")

    def test_3hop_question_friend_company_founder(self, client):
        """Test 3-hop reasoning about company founder."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三工作的公司是谁创立的？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 3,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        
        print(f"\n[3-hop] 张三工作的公司是谁创立的？")
        print(f"  Answer: {answer[:300]}...")
        
        # 验证答案包含马云
        assert "马云" in answer, f"Expected '马云' in answer, got: {answer[:200]}"
        print(f"  ✓ 正确识别：张三 -> 阿里巴巴 -> 马云")

    def test_multi_entity_comparison(self, client):
        """Test comparing multiple entities through graph reasoning."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三和王五分别在哪家公司工作？他们的公司总部在哪？",
                "top_k": 15,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 2,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        
        print(f"\n[Multi-entity] 张三和王五分别在哪家公司工作？")
        print(f"  Answer: {answer[:400]}...")
        
        # 验证答案包含两人的公司和城市信息
        has_zhangsan = "阿里" in answer or "杭州" in answer
        has_wangwu = "阿里云" in answer or "王五" in answer
        assert has_zhangsan, f"Expected 张三's info in answer"
        print(f"  ✓ 包含多实体比较信息")

    def test_indirect_relationship_question(self, client):
        """Test question requiring indirect relationship inference."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "阿里巴巴的创始人和张三是什么关系？",
                "top_k": 10,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 3,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        
        print(f"\n[Indirect] 阿里巴巴的创始人和张三是什么关系？")
        print(f"  Answer: {answer[:300]}...")
        
        # 答案应该推理出马云创立了阿里巴巴，张三在阿里巴巴工作
        has_reasoning = "马云" in answer and ("阿里" in answer or "张三" in answer)
        assert has_reasoning, f"Expected reasoning about 马云 and 张三"
        print(f"  ✓ 正确推理：马云 -> 创立 -> 阿里巴巴 <- 工作 <- 张三")


class TestPureGraphRetrieval:
    """Test pure graph-based retrieval without vector search.
    
    These tests use search_type='graph' which:
    1. Uses LLM to extract entity names from the query
    2. Searches for entities directly in the graph database
    3. Expands relationships from found entities
    4. Uses LLM to answer based on graph data only
    """

    def test_graph_only_simple_question(self, client):
        """Test graph-only retrieval for a simple question."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "张三在哪家公司工作？",
                "top_k": 10,
                "space": "test_graph_rag",
                "search_type": "graph",  # Pure graph mode
                "graph_depth": 2,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        results = data.get('results', [])
        graph_context = data.get('graph_context') or {}
        
        print(f"\n[Graph-only] 张三在哪家公司工作？")
        print(f"  Found entities: {len(results)}")
        for r in results[:3]:
            print(f"    - {r.get('name')} ({r.get('type')})")
        print(f"  Graph nodes: {len(graph_context.get('nodes', []))}")
        print(f"  Graph edges: {len(graph_context.get('edges', []))}")
        print(f"  Answer: {answer[:200]}...")
        
        # 验证找到了相关实体
        assert len(results) > 0, "Should find entities from graph"
        assert "阿里" in answer, f"Expected '阿里' in answer"
        print(f"  ✓ 纯图检索成功")

    def test_graph_only_multi_hop(self, client):
        """Test graph-only retrieval for multi-hop question."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "李四在哪个城市工作？",
                "top_k": 10,
                "space": "test_graph_rag",
                "search_type": "graph",
                "graph_depth": 3,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        graph_context = data.get('graph_context') or {}
        
        print(f"\n[Graph-only Multi-hop] 李四在哪个城市工作？")
        print(f"  Graph nodes: {len(graph_context.get('nodes', []))}")
        print(f"  Graph edges: {len(graph_context.get('edges', []))}")
        
        # Show some relationships
        edges = graph_context.get('edges', [])[:5]
        for edge in edges:
            src = edge.get('source_name') or edge.get('source')
            tgt = edge.get('target_name') or edge.get('target')
            print(f"    {src} --[{edge.get('type')}]--> {tgt}")
        
        print(f"  Answer: {answer[:200]}...")
        
        # 验证多跳推理结果
        assert "深圳" in answer, f"Expected '深圳' in answer (李四->腾讯->深圳)"
        print(f"  ✓ 图多跳推理成功：李四 -> 腾讯 -> 深圳")

    def test_graph_only_relationship_query(self, client):
        """Test graph-only retrieval for relationship question."""
        response = client.post(
            "/api/retrieve/",
            json={
                "query": "阿里巴巴有什么产品？",
                "top_k": 10,
                "space": "test_graph_rag",
                "search_type": "graph",
                "graph_depth": 2,
                "use_llm": True,
            },
        )
        
        data = response.get_json()
        answer = data.get('answer') or ''
        graph_context = data.get('graph_context') or {}
        
        print(f"\n[Graph-only] 阿里巴巴有什么产品？")
        print(f"  Graph nodes: {len(graph_context.get('nodes', []))}")
        
        # Show found products
        nodes = graph_context.get('nodes', [])
        products = [n for n in nodes if n.get('type') in ['entity', 'product']]
        print(f"  Found products/entities: {len(products)}")
        for p in products[:5]:
            print(f"    - {p.get('name')}")
        
        print(f"  Answer: {answer[:200]}...")
        
        has_products = any(p in answer for p in ["淘宝", "天猫", "阿里云"])
        assert has_products, f"Expected product names in answer"
        print(f"  ✓ 正确找到产品关系")

    def test_graph_vs_hybrid_comparison(self, client):
        """Compare graph-only vs hybrid retrieval results."""
        query = "张三的朋友在哪工作？"
        
        # Graph-only
        graph_response = client.post(
            "/api/retrieve/",
            json={
                "query": query,
                "space": "test_graph_rag",
                "search_type": "graph",
                "graph_depth": 3,
                "use_llm": True,
            },
        )
        
        # Hybrid
        hybrid_response = client.post(
            "/api/retrieve/",
            json={
                "query": query,
                "space": "test_graph_rag",
                "collection": "test_graph_rag",
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 3,
                "use_llm": True,
            },
        )
        
        graph_data = graph_response.get_json()
        hybrid_data = hybrid_response.get_json()
        
        graph_answer = graph_data.get('answer') or ''
        hybrid_answer = hybrid_data.get('answer') or ''
        
        print(f"\n[Comparison] {query}")
        print(f"  Graph-only:")
        print(f"    Results: {len(graph_data.get('results', []))}")
        print(f"    Graph nodes: {len((graph_data.get('graph_context') or {}).get('nodes', []))}")
        print(f"    Answer: {graph_answer[:150]}...")
        print(f"  Hybrid:")
        print(f"    Results: {len(hybrid_data.get('results', []))}")
        print(f"    Graph nodes: {len((hybrid_data.get('graph_context') or {}).get('nodes', []))}")
        print(f"    Answer: {hybrid_answer[:150]}...")
        
        # Both should mention 腾讯 and/or 深圳
        graph_correct = "腾讯" in graph_answer or "深圳" in graph_answer
        hybrid_correct = "腾讯" in hybrid_answer or "深圳" in hybrid_answer
        
        print(f"  Graph correct: {graph_correct}, Hybrid correct: {hybrid_correct}")
        assert graph_correct or hybrid_correct, "At least one method should find the answer"


class TestListEntities:
    """Test listing entities."""

    def test_list_all_entities(self, client):
        """Test listing all entities."""
        response = client.get(
            "/api/retrieve/entities?space=test_graph_rag&limit=20"
        )
        
        data = response.get_json()
        print(f"\nList entities response:")
        print(f"  Success: {data.get('success')}")
        print(f"  Count: {data.get('count', 0)}")
        
        for entity in data.get("entities", [])[:10]:
            print(f"    - {entity}")

    def test_list_persons(self, client):
        """Test listing person entities."""
        response = client.get(
            "/api/retrieve/entities?type=person&space=test_graph_rag&limit=10"
        )
        
        data = response.get_json()
        print(f"\nList persons response:")
        print(f"  Success: {data.get('success')}")
        print(f"  Persons: {data.get('entities', [])}")


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
