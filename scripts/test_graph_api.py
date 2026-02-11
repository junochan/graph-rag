#!/usr/bin/env python
"""Test the graph-data API."""

import requests

try:
    r = requests.get('http://127.0.0.1:8008/api/retrieve/graph-data', params={'limit': 50}, timeout=10)
    print('Status:', r.status_code)
    data = r.json()
    print('Nodes:', len(data.get('nodes', [])))
    print('Edges:', len(data.get('edges', [])))
    
    # Get all node IDs
    node_ids = set(n['id'] for n in data.get('nodes', []))
    print(f'\nNode IDs: {node_ids}')
    
    if data.get('edges'):
        print('\nEdges with ID check:')
        for e in data['edges'][:10]:
            src_in = e['source'] in node_ids
            tgt_in = e['target'] in node_ids
            print(f"  {e['source']} ({src_in}) --[{e['type']}]--> {e['target']} ({tgt_in})")
            print(f"    Names: {e.get('source_name')} --> {e.get('target_name')}")
    else:
        print('\nNo edges returned')
        
    if data.get('error'):
        print('\nError:', data['error'])
        
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'Error: {e}')
