#!/usr/bin/env python
"""Debug script to test graph expansion."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.services.graph_store import get_graph_service
from src.services.vector_store import get_vector_store
from src.services.embedding import get_embedding_model


def main():
    settings = get_settings()
    space = "test_graph_rag"
    collection = "test_graph_rag"
    
    print("=" * 60)
    print("Debug Graph Expansion")
    print("=" * 60)
    
    # 1. Test vector search
    print("\n### Step 1: Vector Search ###")
    vector_store = get_vector_store()
    embedding_model = get_embedding_model()
    
    query = "张三在哪个城市工作？"
    query_vector = embedding_model.embed_single(query)
    
    results = vector_store.search(collection, query_vector, top_k=5)
    print(f"Query: {query}")
    print(f"Found {len(results)} results:")
    
    entity_ids = []
    chunk_ids = []
    
    for r in results:
        rid = r.get("id", "")
        payload = r.get("payload", {})
        score = r.get("score", 0)
        is_entity = payload.get("is_entity", False)
        
        print(f"  - ID: {rid}")
        print(f"    Score: {score:.3f}")
        print(f"    is_entity: {is_entity}")
        print(f"    Payload keys: {list(payload.keys())}")
        
        if is_entity or rid.startswith("e_"):
            entity_ids.append(rid)
            print(f"    -> Identified as ENTITY")
        elif rid.startswith("chunk_"):
            chunk_ids.append(rid)
            print(f"    -> Identified as CHUNK")
        else:
            print(f"    -> UNKNOWN type")
    
    print(f"\nSummary: {len(entity_ids)} entities, {len(chunk_ids)} chunks")
    
    # 2. Test graph connection
    print("\n### Step 2: Graph Service ###")
    graph_service = get_graph_service()
    graph_service.connect()
    print("Connected to NebulaGraph")
    
    # 3. Test MATCH query (more reliable than LOOKUP)
    print("\n### Step 3: Test MATCH queries ###")
    for tag in ["person", "entity", "organization"]:
        try:
            # MATCH works without index
            query = f'''
                MATCH (v:{tag}) 
                RETURN id(v) as vid, v.{tag}.name as name 
                LIMIT 5
            '''
            result = graph_service.execute(query, space)
            print(f"MATCH (:{tag}): success={result['success']}")
            if result["success"] and result["data"]:
                for row in result["data"][:3]:
                    print(f"  - {row}")
            elif result.get("error"):
                print(f"  Error: {result['error']}")
        except Exception as e:
            print(f"  Exception: {e}")
    
    # 4. Test MATCH with edges
    print("\n### Step 4: Test MATCH with edges ###")
    # Get persons and their relationships
    fetch_query = f'''
        MATCH (p:person) RETURN id(p) as vid, p.person.name as name LIMIT 5
    '''
    result = graph_service.execute(fetch_query, space)
    print(f"MATCH persons: success={result['success']}")
    
    if result["success"] and result["data"]:
        for row in result["data"]:
            vid = row.get("vid", "")
            name = row.get("name", "")
            print(f"  Person: {name} (vid: {vid})")
            
            # Use MATCH to get edges (more reliable than GO)
            match_query = f'''
                MATCH (n)-[e]-(m) WHERE id(n) == "{vid}"
                RETURN id(m) AS neighbor_id, type(e) AS edge_type, labels(m) AS labels
                LIMIT 10
            '''
            match_result = graph_service.execute(match_query, space)
            print(f"    MATCH edges: success={match_result['success']}")
            if match_result["success"] and match_result["data"]:
                for edge in match_result["data"][:5]:
                    print(f"      -> {edge}")
            elif match_result.get("error"):
                print(f"      Error: {match_result['error']}")
    
    # 5. Test MATCH from vector search entity IDs
    print("\n### Step 5: Test MATCH from vector search entities ###")
    if entity_ids:
        for eid in entity_ids[:3]:
            print(f"Testing entity: {eid}")
            match_query = f'''
                MATCH (n)-[e]-(m) WHERE id(n) == "{eid}"
                RETURN id(m) AS neighbor_id, type(e) AS edge_type, properties(m) AS props
                LIMIT 10
            '''
            match_result = graph_service.execute(match_query, space)
            data = match_result.get("data") or []
            print(f"  MATCH result: success={match_result['success']}, data_len={len(data)}")
            if data:
                for edge in data[:3]:
                    print(f"    {edge}")
            if match_result.get("error"):
                print(f"  Error: {match_result['error']}")
    else:
        print("No entity IDs from vector search to test")
    
    # 6. Check if extracted_from edges exist
    print("\n### Step 6: Check extracted_from edges ###")
    if chunk_ids:
        chunk_id = chunk_ids[0]
        print(f"Testing chunk: {chunk_id}")
        
        # Use MATCH to find edges
        match_query = f'''
            MATCH (c)-[e:extracted_from]-(n) WHERE id(c) == "{chunk_id}"
            RETURN id(n) AS entity_id, type(e) AS edge_type
            LIMIT 10
        '''
        match_result = graph_service.execute(match_query, space)
        print(f"  MATCH extracted_from: success={match_result['success']}, data={match_result.get('data', [])}")
        
        # Also check all edges from chunk
        all_edges_query = f'''
            MATCH (c)-[e]-(n) WHERE id(c) == "{chunk_id}"
            RETURN id(n) AS neighbor_id, type(e) AS edge_type, labels(n) AS labels
            LIMIT 10
        '''
        all_result = graph_service.execute(all_edges_query, space)
        print(f"  All edges from chunk: success={all_result['success']}, data={all_result.get('data', [])}")
    
    # 7. Check all edge types from a known person
    print("\n### Step 7: Test specific edge types ###")
    if result["success"] and result["data"]:
        vid = result["data"][0].get("vid", "")
        print(f"Testing edges from: {vid}")
        for edge_type in ["works_for", "related_to", "located_in", "belongs_to"]:
            edge_query = f'''
                MATCH (n)-[e:{edge_type}]-(m) WHERE id(n) == "{vid}"
                RETURN id(m) AS target, type(e) AS etype, properties(m) AS props
                LIMIT 5
            '''
            edge_result = graph_service.execute(edge_query, space)
            data = edge_result.get("data") or []
            print(f"  {edge_type}: success={edge_result['success']}, count={len(data)}")
            for row in data:
                print(f"    -> {row}")


if __name__ == "__main__":
    main()
