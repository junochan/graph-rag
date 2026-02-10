#!/usr/bin/env python
"""
Quick test script to test knowledge graph building and retrieval.
Run this while the Flask server is running.

Usage:
    1. Start the server: uv run python main.py
    2. Run this test: uv run python scripts/run_test.py
"""

import json
import sys
import time

import httpx

BASE_URL = "http://localhost:8008"  # 根据 .env 配置


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def test_health():
    """Test API health."""
    print_header("1. Health Check")
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_build_text():
    """Test building knowledge graph from text."""
    print_header("2. Build Knowledge Graph from Text")
    
    test_text = """
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
    
    try:
        print("Sending build request...")
        resp = httpx.post(
            f"{BASE_URL}/api/build/text",
            json={
                "text": test_text,
                "source_name": "test_multi_hop.txt",
                "chunk_size": 500,
                "chunk_overlap": 100,
            },
            timeout=120,
        )
        
        data = resp.json()
        print(f"Success: {data.get('success')}")
        print(f"Document ID: {data.get('document_id')}")
        print(f"Chunks: {data.get('chunks_count')}")
        print(f"Entities: {data.get('entities_count')}")
        print(f"Relationships: {data.get('relationships_count')}")
        print(f"Processing Time: {data.get('processing_time', 0):.2f}s")
        
        if data.get('errors'):
            print(f"Errors: {data.get('errors')[:3]}")
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_vector_search():
    """Test vector search."""
    print_header("3. Vector Search")
    
    try:
        resp = httpx.post(
            f"{BASE_URL}/api/retrieve/",
            json={
                "query": "张三在哪家公司工作？",
                "top_k": 5,
                "search_type": "vector",
                "expand_graph": False,
                "use_llm": False,
            },
            timeout=30,
        )
        
        data = resp.json()
        print(f"Success: {data.get('success')}")
        print(f"Results: {len(data.get('results', []))}")
        
        for i, r in enumerate(data.get('results', [])[:3], 1):
            print(f"  [{i}] {r.get('name')} (score: {r.get('score', 0):.3f})")
            text = r.get('text', '')[:100]
            if text:
                print(f"      Text: {text}...")
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_graph_query():
    """Test direct graph query."""
    print_header("4. Graph Query - List Persons")
    
    try:
        resp = httpx.post(
            f"{BASE_URL}/api/retrieve/graph-query",
            json={
                "query": "MATCH (p:person) RETURN p.person.name AS name LIMIT 10",
            },
            timeout=30,
        )
        
        data = resp.json()
        print(f"Success: {data.get('success')}")
        print(f"Data: {data.get('data', [])}")
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_multi_hop_2():
    """Test 2-hop query: Person -> Company -> City."""
    print_header("5. Multi-Hop Query (2-hop): Person -> Company -> City")
    
    try:
        resp = httpx.post(
            f"{BASE_URL}/api/retrieve/graph-query",
            json={
                "query": """
                    MATCH (p:person)-[:works_for]->(o:organization)-[:located_in]->(l:location)
                    RETURN p.person.name AS person, 
                           o.organization.name AS company, 
                           l.location.name AS city
                    LIMIT 10
                """,
            },
            timeout=30,
        )
        
        data = resp.json()
        print(f"Success: {data.get('success')}")
        
        if data.get('data'):
            print("2-hop paths found:")
            for row in data['data']:
                print(f"  {row.get('person')} -> {row.get('company')} -> {row.get('city')}")
        else:
            print("No 2-hop paths found")
            print(f"Error: {data.get('error')}")
        
        return data.get('success', False) and bool(data.get('data'))
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_multi_hop_3():
    """Test 3-hop query: Person -> knows -> Person -> Company -> City."""
    print_header("6. Multi-Hop Query (3-hop): Person -> knows -> Person -> Company -> City")
    
    try:
        resp = httpx.post(
            f"{BASE_URL}/api/retrieve/graph-query",
            json={
                "query": """
                    MATCH (p1:person)-[:knows]->(p2:person)-[:works_for]->(o:organization)-[:located_in]->(l:location)
                    RETURN p1.person.name AS person1,
                           p2.person.name AS friend,
                           o.organization.name AS company,
                           l.location.name AS city
                    LIMIT 10
                """,
            },
            timeout=30,
        )
        
        data = resp.json()
        print(f"Success: {data.get('success')}")
        
        if data.get('data'):
            print("3-hop paths found:")
            for row in data['data']:
                print(f"  {row.get('person1')} -> knows -> {row.get('friend')} -> {row.get('company')} -> {row.get('city')}")
        else:
            print("No 3-hop paths found")
            print(f"Error: {data.get('error')}")
        
        return data.get('success', False) and bool(data.get('data'))
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_hybrid_with_llm():
    """Test hybrid retrieval with LLM answer."""
    print_header("7. Hybrid Retrieval with LLM Answer")
    
    try:
        resp = httpx.post(
            f"{BASE_URL}/api/retrieve/",
            json={
                "query": "张三工作的公司总部在哪个城市？",
                "top_k": 10,
                "search_type": "hybrid",
                "expand_graph": True,
                "graph_depth": 2,
                "use_llm": True,
            },
            timeout=60,
        )
        
        data = resp.json()
        print(f"Success: {data.get('success')}")
        print(f"Results: {len(data.get('results', []))}")
        
        graph_ctx = data.get('graph_context')
        if graph_ctx:
            print(f"Graph nodes: {len(graph_ctx.get('nodes', []))}")
            print(f"Graph edges: {len(graph_ctx.get('edges', []))}")
        
        answer = data.get('answer')
        if answer:
            print(f"\nLLM Answer:\n{answer[:500]}")
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    print("="*60)
    print(" Graph RAG Test Suite")
    print("="*60)
    print(f"API URL: {BASE_URL}")
    
    # Test health
    if not test_health():
        print("\n❌ API is not running. Please start the server first:")
        print("   uv run python main.py")
        sys.exit(1)
    
    print("\n✓ API is healthy")
    
    # Build knowledge graph
    build_success = test_build_text()
    
    if build_success:
        print("\n✓ Knowledge graph built successfully")
        time.sleep(2)  # Wait for data sync
    else:
        print("\n⚠ Build may have had errors, continuing with tests...")
    
    # Run retrieval tests
    results = {
        "vector_search": test_vector_search(),
        "graph_query": test_graph_query(),
        "multi_hop_2": test_multi_hop_2(),
        "multi_hop_3": test_multi_hop_3(),
        "hybrid_llm": test_hybrid_with_llm(),
    }
    
    # Summary
    print_header("Test Summary")
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
    elif passed_count > 0:
        print("\n⚠ Some tests failed. Multi-hop queries may need more data.")
    else:
        print("\n❌ Tests failed. Check the errors above.")


if __name__ == "__main__":
    main()
