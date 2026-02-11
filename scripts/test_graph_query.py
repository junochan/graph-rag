#!/usr/bin/env python
"""Test graph query and expansion."""

import requests
import json

API_URL = "http://127.0.0.1:8008"

# Test 1: Check graph-data API
print("=" * 60)
print("Test 1: Graph Data API")
print("=" * 60)
r = requests.get(f"{API_URL}/api/retrieve/graph-data", params={"limit": 50})
data = r.json()
print(f"Nodes: {len(data.get('nodes', []))}")
print(f"Edges: {len(data.get('edges', []))}")

if data.get("edges"):
    print("\nSample edges:")
    for e in data["edges"][:5]:
        print(f"  {e['source_name']} --[{e['type']}]--> {e['target_name']}")

# Test 2: Retrieve with graph search
print("\n" + "=" * 60)
print("Test 2: Retrieve API (graph search)")
print("=" * 60)

query = "李四的朋友在哪个城市工作"
r = requests.post(f"{API_URL}/api/retrieve/", json={
    "query": query,
    "search_type": "graph",
    "expand_graph": True,
    "graph_depth": 2,
    "use_llm": False,
})
data = r.json()
print(f"Query: {query}")
print(f"Success: {data.get('success')}")
print(f"Results: {len(data.get('results', []))}")

gc = data.get("graph_context")
if gc:
    print(f"Graph Context Nodes: {len(gc.get('nodes', []))}")
    print(f"Graph Context Edges: {len(gc.get('edges', []))}")
    
    if gc.get("nodes"):
        print("\nNodes found:")
        for n in gc["nodes"][:10]:
            print(f"  {n['id']}: {n['name']} ({n['type']})")
    
    if gc.get("edges"):
        print("\nEdges found:")
        for e in gc["edges"][:10]:
            print(f"  {e.get('source_name', e['source'])} --[{e['type']}]--> {e.get('target_name', e['target'])}")
    else:
        print("\nNo edges in graph context!")
else:
    print("No graph_context returned!")

# Test 3: Direct graph query to check edges exist
print("\n" + "=" * 60)
print("Test 3: Direct nGQL Query for Edges")
print("=" * 60)

r = requests.post(f"{API_URL}/api/retrieve/graph-query", json={
    "query": 'MATCH (n)-[e]-(m) RETURN id(n) AS src, type(e) AS edge, id(m) AS dst LIMIT 20'
})
data = r.json()
print(f"Direct edge query success: {data.get('success')}")
print(f"Edge count: {len(data.get('data', []))}")

if data.get("data"):
    print("\nEdges in database:")
    for row in data["data"][:10]:
        print(f"  {row.get('src')} --[{row.get('edge')}]--> {row.get('dst')}")
else:
    print("No edges found in database!")
    if data.get("error"):
        print(f"Error: {data['error']}")
