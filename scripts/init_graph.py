#!/usr/bin/env python
"""
NebulaGraph initialization script.
Creates graph space, tags, and edge types for the knowledge graph.

Usage:
    python scripts/init_graph.py
    python scripts/init_graph.py --space my_space --host 192.168.1.100 --port 9669
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nebula3.Config import Config as NebulaConfig
from nebula3.gclient.net import ConnectionPool


# ==================== Schema Definitions ====================

# Tags (顶点类型)
TAGS = {
    "entity": {
        "properties": {
            "name": "string",
            "type": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Base entity tag for all extracted entities",
    },
    "person": {
        "properties": {
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Person entity",
    },
    "organization": {
        "properties": {
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Organization/Company entity",
    },
    "location": {
        "properties": {
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Location/Place entity",
    },
    "event": {
        "properties": {
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Event entity",
    },
    "concept": {
        "properties": {
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Concept/Abstract entity",
    },
    "technology": {
        "properties": {
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Technology entity",
    },
    "product": {
        "properties": {
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        "comment": "Product entity",
    },
    "document": {
        "properties": {
            "name": "string",
            "description": "string",
            "file_type": "string",
            "source_path": "string",
            "created_at": "timestamp",
        },
        "comment": "Source document",
    },
    "chunk": {
        "properties": {
            "content": "string",
            "chunk_index": "int",
            "document_id": "string",
            "created_at": "timestamp",
        },
        "comment": "Text chunk from document",
    },
}

# Edge Types (边类型)
EDGE_TYPES = {
    "related_to": {
        "properties": {
            "description": "string",
            "weight": "double",
            "source_chunk": "string",
        },
        "comment": "General relationship between entities",
    },
    "belongs_to": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Membership/belonging relationship",
    },
    "located_in": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Location relationship",
    },
    "works_for": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Employment relationship",
    },
    "created_by": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Creation/authorship relationship",
    },
    "part_of": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Part-whole relationship",
    },
    "causes": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Causal relationship",
    },
    "uses": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Usage relationship",
    },
    "mentions": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Mention relationship",
    },
    "similar_to": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Similarity relationship",
    },
    "contains": {
        "properties": {
            "chunk_index": "int",
        },
        "comment": "Document contains chunk",
    },
    "extracted_from": {
        "properties": {
            "chunk_id": "string",
        },
        "comment": "Entity extracted from chunk",
    },
    "knows": {
        "properties": {
            "description": "string",
            "weight": "double",
        },
        "comment": "Person knows person",
    },
    "has_skill": {
        "properties": {
            "description": "string",
            "level": "string",
        },
        "comment": "Person has skill/technology",
    },
    "produces": {
        "properties": {
            "description": "string",
        },
        "comment": "Organization produces product",
    },
}


def create_connection_pool(host: str, port: int, max_size: int = 10) -> ConnectionPool:
    """Create NebulaGraph connection pool."""
    config = NebulaConfig()
    config.max_connection_pool_size = max_size

    pool = ConnectionPool()
    if not pool.init([(host, port)], config):
        raise ConnectionError(f"Failed to connect to NebulaGraph at {host}:{port}")

    return pool


def execute_query(session, query: str) -> tuple[bool, str]:
    """Execute nGQL query and return (success, message)."""
    result = session.execute(query)
    if result.is_succeeded():
        return True, "OK"
    else:
        return False, result.error_msg()


def init_space(
    session,
    space_name: str,
    partition_num: int = 10,
    replica_factor: int = 1,
    vid_type: str = "FIXED_STRING(256)",
) -> bool:
    """Create graph space if not exists."""
    print(f"\n{'='*60}")
    print(f"Creating space: {space_name}")
    print(f"{'='*60}")

    query = f"""
    CREATE SPACE IF NOT EXISTS {space_name} (
        partition_num = {partition_num},
        replica_factor = {replica_factor},
        vid_type = {vid_type}
    ) COMMENT = 'Graph RAG Knowledge Graph'
    """

    success, msg = execute_query(session, query)
    if success:
        print(f"✓ Space '{space_name}' created (or already exists)")
        return True
    else:
        print(f"✗ Failed to create space: {msg}")
        return False


def init_tags(session, space_name: str) -> tuple[int, int]:
    """Create all tags. Returns (success_count, fail_count)."""
    print(f"\n{'='*60}")
    print("Creating Tags (Vertex Types)")
    print(f"{'='*60}")

    # Switch to space
    execute_query(session, f"USE {space_name}")

    success_count = 0
    fail_count = 0

    for tag_name, tag_def in TAGS.items():
        props = tag_def["properties"]
        comment = tag_def.get("comment", "")

        # Build property string
        prop_parts = [f"{k} {v}" for k, v in props.items()]
        props_str = ", ".join(prop_parts)

        query = f"CREATE TAG IF NOT EXISTS {tag_name}({props_str})"
        if comment:
            query += f" COMMENT = '{comment}'"

        success, msg = execute_query(session, query)
        if success:
            print(f"  ✓ Tag: {tag_name}")
            success_count += 1
        else:
            print(f"  ✗ Tag: {tag_name} - {msg}")
            fail_count += 1

    return success_count, fail_count


def init_edge_types(session, space_name: str) -> tuple[int, int]:
    """Create all edge types. Returns (success_count, fail_count)."""
    print(f"\n{'='*60}")
    print("Creating Edge Types")
    print(f"{'='*60}")

    # Switch to space
    execute_query(session, f"USE {space_name}")

    success_count = 0
    fail_count = 0

    for edge_name, edge_def in EDGE_TYPES.items():
        props = edge_def.get("properties", {})
        comment = edge_def.get("comment", "")

        # Build property string
        if props:
            prop_parts = [f"{k} {v}" for k, v in props.items()]
            props_str = ", ".join(prop_parts)
            query = f"CREATE EDGE IF NOT EXISTS {edge_name}({props_str})"
        else:
            query = f"CREATE EDGE IF NOT EXISTS {edge_name}()"

        if comment:
            query += f" COMMENT = '{comment}'"

        success, msg = execute_query(session, query)
        if success:
            print(f"  ✓ Edge: {edge_name}")
            success_count += 1
        else:
            print(f"  ✗ Edge: {edge_name} - {msg}")
            fail_count += 1

    return success_count, fail_count


def create_indexes(session, space_name: str) -> tuple[int, int]:
    """Create indexes for common queries. Returns (success_count, fail_count)."""
    print(f"\n{'='*60}")
    print("Creating Indexes")
    print(f"{'='*60}")

    # Switch to space
    execute_query(session, f"USE {space_name}")

    indexes = [
        # Tag indexes
        ("entity_name_idx", "TAG", "entity", "name(64)"),
        ("person_name_idx", "TAG", "person", "name(64)"),
        ("organization_name_idx", "TAG", "organization", "name(64)"),
        ("location_name_idx", "TAG", "location", "name(64)"),
        ("document_name_idx", "TAG", "document", "name(64)"),
        ("chunk_document_idx", "TAG", "chunk", "document_id(64)"),
    ]

    success_count = 0
    fail_count = 0

    for idx_name, idx_type, target, props in indexes:
        query = f"CREATE {idx_type} INDEX IF NOT EXISTS {idx_name} ON {target}({props})"

        success, msg = execute_query(session, query)
        if success:
            print(f"  ✓ Index: {idx_name}")
            success_count += 1
        else:
            print(f"  ✗ Index: {idx_name} - {msg}")
            fail_count += 1

    return success_count, fail_count


def verify_schema(session, space_name: str):
    """Verify created schema."""
    print(f"\n{'='*60}")
    print("Verifying Schema")
    print(f"{'='*60}")

    execute_query(session, f"USE {space_name}")

    # Show tags
    result = session.execute("SHOW TAGS")
    if result.is_succeeded():
        tags = [result.row_values(i)[0].as_string() for i in range(result.row_size())]
        print(f"\n  Tags ({len(tags)}): {', '.join(tags)}")

    # Show edges
    result = session.execute("SHOW EDGES")
    if result.is_succeeded():
        edges = [result.row_values(i)[0].as_string() for i in range(result.row_size())]
        print(f"  Edges ({len(edges)}): {', '.join(edges)}")

    # Show indexes
    result = session.execute("SHOW TAG INDEXES")
    if result.is_succeeded():
        indexes = [result.row_values(i)[0].as_string() for i in range(result.row_size())]
        print(f"  Tag Indexes ({len(indexes)}): {', '.join(indexes)}")


def main():
    parser = argparse.ArgumentParser(
        description="Initialize NebulaGraph schema for Graph RAG"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="NebulaGraph host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9669,
        help="NebulaGraph port (default: 9669)",
    )
    parser.add_argument(
        "--user",
        default="root",
        help="NebulaGraph username (default: root)",
    )
    parser.add_argument(
        "--password",
        default="nebula",
        help="NebulaGraph password (default: nebula)",
    )
    parser.add_argument(
        "--space",
        default="graph_rag",
        help="Graph space name (default: graph_rag)",
    )
    parser.add_argument(
        "--partition-num",
        type=int,
        default=10,
        help="Number of partitions (default: 10)",
    )
    parser.add_argument(
        "--replica-factor",
        type=int,
        default=1,
        help="Replica factor (default: 1)",
    )
    parser.add_argument(
        "--skip-indexes",
        action="store_true",
        help="Skip creating indexes",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("NebulaGraph Schema Initialization")
    print("=" * 60)
    print(f"Host: {args.host}:{args.port}")
    print(f"User: {args.user}")
    print(f"Space: {args.space}")
    print(f"Partitions: {args.partition_num}")
    print(f"Replica Factor: {args.replica_factor}")

    # Connect
    try:
        print(f"\nConnecting to NebulaGraph...")
        pool = create_connection_pool(args.host, args.port)
        session = pool.get_session(args.user, args.password)
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)

    try:
        # Create space
        if not init_space(
            session,
            args.space,
            args.partition_num,
            args.replica_factor,
        ):
            sys.exit(1)

        # Wait for space to be ready
        print("\nWaiting for space to be ready...")
        time.sleep(5)

        # Create tags
        tag_success, tag_fail = init_tags(session, args.space)

        # Wait for tags
        time.sleep(2)

        # Create edge types
        edge_success, edge_fail = init_edge_types(session, args.space)

        # Wait for edges
        time.sleep(2)

        # Create indexes
        idx_success, idx_fail = 0, 0
        if not args.skip_indexes:
            idx_success, idx_fail = create_indexes(session, args.space)
            # Rebuild indexes
            print("\n  Rebuilding indexes (this may take a moment)...")
            time.sleep(3)

        # Verify
        verify_schema(session, args.space)

        # Summary
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        print(f"  Tags:    {tag_success} created, {tag_fail} failed")
        print(f"  Edges:   {edge_success} created, {edge_fail} failed")
        if not args.skip_indexes:
            print(f"  Indexes: {idx_success} created, {idx_fail} failed")

        total_fail = tag_fail + edge_fail + idx_fail
        if total_fail == 0:
            print("\n✓ Schema initialization completed successfully!")
        else:
            print(f"\n⚠ Schema initialization completed with {total_fail} errors")

    finally:
        session.release()
        pool.close()


if __name__ == "__main__":
    main()
