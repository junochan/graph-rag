#!/usr/bin/env python
"""
Multi-hop reasoning test script.
Tests the knowledge graph's ability to perform multi-hop inference.

Usage:
    uv run python scripts/test_multi_hop.py
    uv run python scripts/test_multi_hop.py --host localhost --port 5000
"""

import argparse
import json
import sys
import time

import httpx


# ==================== Test Data ====================

TEST_TEXT = """
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

# 多跳推理测试问题
MULTI_HOP_QUESTIONS = [
    # 1-hop
    {
        "question": "张三在哪家公司工作？",
        "expected_path": "张三 -> works_for -> 阿里巴巴",
        "hops": 1,
    },
    # 2-hop
    {
        "question": "张三工作的公司总部在哪个城市？",
        "expected_path": "张三 -> works_for -> 阿里巴巴 -> located_in -> 杭州",
        "hops": 2,
    },
    # 2-hop (different path)
    {
        "question": "阿里巴巴有什么产品？",
        "expected_path": "阿里巴巴 -> produces -> [淘宝, 天猫, 阿里云]",
        "hops": 2,
    },
    # 3-hop
    {
        "question": "张三的朋友在哪个城市工作？",
        "expected_path": "张三 -> knows -> 李四 -> works_for -> 腾讯 -> located_in -> 深圳",
        "hops": 3,
    },
    # Complex multi-hop
    {
        "question": "张三和王五有什么关系？他们在同一个城市工作吗？",
        "expected_path": "张三 -> works_for -> 阿里巴巴, 王五 -> works_for -> 阿里云 -> part_of -> 阿里巴巴",
        "hops": 3,
    },
]


def print_separator(title: str = ""):
    """Print a separator line."""
    print("\n" + "=" * 70)
    if title:
        print(f" {title}")
        print("=" * 70)


def init_schema(base_url: str, space: str) -> bool:
    """Initialize graph schema."""
    print_separator("Step 1: Initialize Schema")
    
    try:
        response = httpx.post(
            f"{base_url}/api/build/init-schema",
            json={"space": space},
            timeout=60.0,
        )
        data = response.json()
        
        if data.get("success") or data.get("space_initialized"):
            print(f"✓ Schema initialized for space: {space}")
            print(f"  Tags: {data.get('created_tags', [])}")
            print(f"  Edges: {data.get('created_edges', [])}")
            return True
        else:
            print(f"⚠ Schema may already exist: {data.get('errors', [])}")
            return True  # Continue anyway
            
    except Exception as e:
        print(f"✗ Failed to initialize schema: {e}")
        return False


def build_knowledge_graph(base_url: str, space: str, collection: str) -> bool:
    """Build knowledge graph from test text."""
    print_separator("Step 2: Build Knowledge Graph")
    
    try:
        print("Building knowledge graph from test text...")
        print(f"Text length: {len(TEST_TEXT)} characters")
        
        response = httpx.post(
            f"{base_url}/api/build/text",
            json={
                "text": TEST_TEXT,
                "source_name": "multi_hop_test.txt",
                "space": space,
                "collection": collection,
                "chunk_size": 500,
                "chunk_overlap": 100,
            },
            timeout=120.0,
        )
        data = response.json()
        
        if data.get("success"):
            print(f"✓ Knowledge graph built successfully!")
            print(f"  Document ID: {data['document_id']}")
            print(f"  Chunks: {data['chunks_count']}")
            print(f"  Entities: {data['entities_count']}")
            print(f"  Relationships: {data['relationships_count']}")
            print(f"  Processing time: {data['processing_time']:.2f}s")
            return True
        else:
            print(f"✗ Build failed: {data.get('errors', [])}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to build knowledge graph: {e}")
        return False


def test_graph_queries(base_url: str, space: str):
    """Test direct graph queries."""
    print_separator("Step 3: Test Graph Queries")
    
    queries = [
        ("List all persons", "MATCH (p:person) RETURN p.person.name AS name LIMIT 10"),
        ("List all organizations", "MATCH (o:organization) RETURN o.organization.name AS name LIMIT 10"),
        ("List works_for relations", 
         "MATCH (p:person)-[e:works_for]->(o:organization) RETURN p.person.name AS person, o.organization.name AS org LIMIT 10"),
        ("2-hop: Person->Company->City",
         "MATCH (p:person)-[:works_for]->(o:organization)-[:located_in]->(l:location) "
         "RETURN p.person.name AS person, o.organization.name AS company, l.location.name AS city LIMIT 10"),
    ]
    
    for title, query in queries:
        print(f"\n  Query: {title}")
        try:
            response = httpx.post(
                f"{base_url}/api/retrieve/graph-query",
                json={"query": query, "space": space},
                timeout=30.0,
            )
            data = response.json()
            
            if data.get("success"):
                results = data.get("data", [])
                print(f"  Results ({len(results)}):")
                for row in results[:5]:
                    print(f"    {row}")
            else:
                print(f"  Error: {data.get('error')}")
                
        except Exception as e:
            print(f"  Error: {e}")


def test_multi_hop_reasoning(base_url: str, space: str, collection: str, use_llm: bool = True):
    """Test multi-hop reasoning with questions."""
    print_separator("Step 4: Test Multi-Hop Reasoning")
    
    for i, test_case in enumerate(MULTI_HOP_QUESTIONS, 1):
        question = test_case["question"]
        expected_path = test_case["expected_path"]
        hops = test_case["hops"]
        
        print(f"\n  [{i}] Question ({hops}-hop): {question}")
        print(f"      Expected path: {expected_path}")
        
        try:
            response = httpx.post(
                f"{base_url}/api/retrieve/",
                json={
                    "query": question,
                    "top_k": 10,
                    "space": space,
                    "collection": collection,
                    "search_type": "hybrid",
                    "expand_graph": True,
                    "graph_depth": hops + 1,
                    "use_llm": use_llm,
                },
                timeout=60.0,
            )
            data = response.json()
            
            if data.get("success"):
                # Show retrieved results
                results = data.get("results", [])
                print(f"      Retrieved {len(results)} items")
                
                # Show graph context
                graph_context = data.get("graph_context")
                if graph_context:
                    nodes = graph_context.get("nodes", [])
                    edges = graph_context.get("edges", [])
                    print(f"      Graph context: {len(nodes)} nodes, {len(edges)} edges")
                    
                    # Show key edges (paths)
                    if edges:
                        print("      Key relationships:")
                        for edge in edges[:5]:
                            print(f"        {edge.get('source')} --[{edge.get('type')}]--> {edge.get('target')}")
                
                # Show LLM answer
                answer = data.get("answer")
                if answer:
                    print(f"      Answer: {answer[:300]}...")
                    
            else:
                print(f"      Error: {data.get('errors', [])}")
                
        except Exception as e:
            print(f"      Error: {e}")


def test_specific_path_query(base_url: str, space: str):
    """Test specific multi-hop path queries."""
    print_separator("Step 5: Specific Path Queries")
    
    # Test 3-hop path: Person -> knows -> Person -> works_for -> Organization -> located_in -> Location
    print("\n  Testing 3-hop path: Who does 张三's friend work for, and where?")
    
    query = """
    MATCH (p1:person)-[:knows]->(p2:person)-[:works_for]->(o:organization)-[:located_in]->(l:location)
    WHERE p1.person.name CONTAINS '张'
    RETURN p1.person.name AS person1, 
           p2.person.name AS friend,
           o.organization.name AS company,
           l.location.name AS city
    LIMIT 10
    """
    
    try:
        response = httpx.post(
            f"{base_url}/api/retrieve/graph-query",
            json={"query": query, "space": space},
            timeout=30.0,
        )
        data = response.json()
        
        if data.get("success") and data.get("data"):
            print("  ✓ 3-hop path found!")
            for row in data["data"]:
                print(f"    {row.get('person1')} -> knows -> {row.get('friend')} -> works_for -> {row.get('company')} -> located_in -> {row.get('city')}")
        else:
            print(f"  Path not found or error: {data.get('error')}")
            
    except Exception as e:
        print(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test multi-hop reasoning in knowledge graph")
    parser.add_argument("--host", default="localhost", help="API host (default: localhost)")
    parser.add_argument("--port", type=int, default=5000, help="API port (default: 5000)")
    parser.add_argument("--space", default="test_multi_hop", help="Graph space name")
    parser.add_argument("--collection", default="test_multi_hop", help="Vector collection name")
    parser.add_argument("--skip-build", action="store_true", help="Skip building (use existing data)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM answer generation")
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    
    print("=" * 70)
    print(" Multi-Hop Reasoning Test")
    print("=" * 70)
    print(f" API: {base_url}")
    print(f" Space: {args.space}")
    print(f" Collection: {args.collection}")
    
    # Check API health
    try:
        response = httpx.get(f"{base_url}/health", timeout=5.0)
        if response.status_code == 200:
            print(" Status: API is running ✓")
        else:
            print(f" Status: API returned {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f" Status: Cannot connect to API - {e}")
        sys.exit(1)
    
    if not args.skip_build:
        # Initialize schema
        if not init_schema(base_url, args.space):
            print("\nWarning: Schema initialization had issues, continuing anyway...")
        
        time.sleep(3)  # Wait for schema
        
        # Build knowledge graph
        if not build_knowledge_graph(base_url, args.space, args.collection):
            print("\nFailed to build knowledge graph. Exiting.")
            sys.exit(1)
        
        time.sleep(3)  # Wait for data sync
    
    # Test graph queries
    test_graph_queries(base_url, args.space)
    
    # Test multi-hop reasoning
    test_multi_hop_reasoning(base_url, args.space, args.collection, use_llm=not args.no_llm)
    
    # Test specific path queries
    test_specific_path_query(base_url, args.space)
    
    print_separator("Test Complete")
    print("\nMulti-hop reasoning test completed!")
    print("Check the results above to verify if the knowledge graph can perform multi-hop inference.")


if __name__ == "__main__":
    main()
