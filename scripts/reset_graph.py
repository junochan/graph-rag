#!/usr/bin/env python
"""
Reset NebulaGraph space - drop all data and reinitialize schema.

Usage:
    python scripts/reset_graph.py
    python scripts/reset_graph.py --space graph_rag --confirm
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

# Import schema definitions from init_graph
from scripts.init_graph import (
    TAGS,
    EDGE_TYPES,
    execute_query,
    init_tags,
    init_edge_types,
    create_indexes,
    verify_schema,
)


def create_connection_pool(host: str, port: int, max_size: int = 10) -> ConnectionPool:
    """Create NebulaGraph connection pool."""
    config = NebulaConfig()
    config.max_connection_pool_size = max_size

    pool = ConnectionPool()
    if not pool.init([(host, port)], config):
        raise ConnectionError(f"Failed to connect to NebulaGraph at {host}:{port}")

    return pool


def drop_space(session, space_name: str) -> bool:
    """Drop the graph space (deletes ALL data)."""
    print(f"\n{'='*60}")
    print(f"Dropping space: {space_name}")
    print(f"{'='*60}")

    query = f"DROP SPACE IF EXISTS {space_name}"
    success, msg = execute_query(session, query)
    
    if success:
        print(f"[OK] Space '{space_name}' dropped")
        return True
    else:
        print(f"[FAILED] Failed to drop space: {msg}")
        return False


def create_space(
    session,
    space_name: str,
    partition_num: int = 10,
    replica_factor: int = 1,
    vid_type: str = "FIXED_STRING(256)",
) -> bool:
    """Create graph space."""
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
        print(f"[OK] Space '{space_name}' created")
        return True
    else:
        print(f"[FAILED] Failed to create space: {msg}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Reset NebulaGraph space - drop all data and reinitialize"
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
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("NebulaGraph Space Reset")
    print("=" * 60)
    print(f"Host: {args.host}:{args.port}")
    print(f"Space: {args.space}")
    print()
    print("[WARNING] This will DELETE ALL DATA in the space!")
    print()

    # Confirmation
    if not args.confirm:
        response = input(f"Type '{args.space}' to confirm deletion: ")
        if response != args.space:
            print("Aborted.")
            sys.exit(0)

    # Connect
    try:
        print(f"\nConnecting to NebulaGraph...")
        pool = create_connection_pool(args.host, args.port)
        session = pool.get_session(args.user, args.password)
        print("[OK] Connected successfully")
    except Exception as e:
        print(f"[FAILED] Connection failed: {e}")
        sys.exit(1)

    try:
        # Drop existing space
        drop_space(session, args.space)
        
        # Wait for drop to complete
        print("\nWaiting for space to be dropped...")
        time.sleep(3)

        # Create new space
        if not create_space(
            session,
            args.space,
            args.partition_num,
            args.replica_factor,
        ):
            sys.exit(1)

        # Wait for space to be ready (NebulaGraph needs time to create partitions)
        print("\nWaiting for space to be ready...")
        time.sleep(10)
        
        # Verify space is usable by trying to USE it
        print("Verifying space is ready...")
        for attempt in range(5):
            result = session.execute(f"USE {args.space}")
            if result.is_succeeded():
                print(f"[OK] Space '{args.space}' is ready")
                break
            else:
                print(f"  Attempt {attempt + 1}/5: Space not ready yet, waiting...")
                time.sleep(3)
        else:
            print("[FAILED] Space did not become ready in time")
            sys.exit(1)

        # Create tags
        tag_success, tag_fail = init_tags(session, args.space)

        # Wait for tags
        time.sleep(2)

        # Create edge types
        edge_success, edge_fail = init_edge_types(session, args.space)

        # Wait for edges
        time.sleep(2)

        # Create indexes
        idx_success, idx_fail = create_indexes(session, args.space)
        
        # Wait for indexes
        print("\n  Rebuilding indexes...")
        time.sleep(3)

        # Verify
        verify_schema(session, args.space)

        # Summary
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        print(f"  Tags:    {tag_success} created, {tag_fail} failed")
        print(f"  Edges:   {edge_success} created, {edge_fail} failed")
        print(f"  Indexes: {idx_success} created, {idx_fail} failed")

        total_fail = tag_fail + edge_fail + idx_fail
        if total_fail == 0:
            print("\n[OK] Space reset and reinitialized successfully!")
        else:
            print(f"\n[WARNING] Reset completed with {total_fail} errors")

    finally:
        session.release()
        pool.close()


if __name__ == "__main__":
    main()
