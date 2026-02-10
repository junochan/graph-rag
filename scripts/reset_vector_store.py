#!/usr/bin/env python
"""
Reset vector store collection.

This script deletes and recreates the vector collection with the correct dimension.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from src.config import get_settings


def reset_collection(collection_name: str | None = None):
    """Delete and recreate the vector collection."""
    settings = get_settings()
    vs_config = settings.vector_store
    
    collection = collection_name or vs_config.qdrant_collection
    dimension = vs_config.dimension
    
    print(f"Connecting to Qdrant at {vs_config.qdrant_host}:{vs_config.qdrant_port}")
    client = QdrantClient(
        host=vs_config.qdrant_host,
        port=vs_config.qdrant_port,
        api_key=vs_config.qdrant_api_key,
        check_compatibility=False,
    )
    
    # Delete existing collection if exists
    try:
        client.delete_collection(collection)
        print(f"Deleted existing collection: {collection}")
    except Exception as e:
        print(f"Collection {collection} does not exist or could not be deleted: {e}")
    
    # Create new collection with correct dimension
    client.create_collection(
        collection_name=collection,
        vectors_config=qdrant_models.VectorParams(
            size=dimension,
            distance=qdrant_models.Distance.COSINE,
        ),
    )
    print(f"Created collection '{collection}' with dimension {dimension}")
    
    # Verify
    info = client.get_collection(collection)
    # Handle different Qdrant API versions
    try:
        vectors_count = info.vectors_count
    except AttributeError:
        vectors_count = getattr(info, 'points_count', 'unknown')
    
    try:
        dimension = info.config.params.vectors.size
    except AttributeError:
        try:
            dimension = info.config.params.size
        except AttributeError:
            dimension = vs_config.dimension
    
    print(f"Collection info: vectors_count={vectors_count}, dimension={dimension}")
    
    return True


def reset_test_collection():
    """Reset the test collection."""
    return reset_collection("test_graph_rag")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset Qdrant vector collection")
    parser.add_argument("--collection", "-c", help="Collection name to reset (default: from config)")
    parser.add_argument("--test", "-t", action="store_true", help="Reset test_graph_rag collection")
    parser.add_argument("--all", "-a", action="store_true", help="Reset both main and test collections")
    
    args = parser.parse_args()
    
    if args.all:
        print("=== Resetting main collection ===")
        reset_collection()
        print("\n=== Resetting test collection ===")
        reset_test_collection()
    elif args.test:
        reset_test_collection()
    elif args.collection:
        reset_collection(args.collection)
    else:
        reset_collection()
    
    print("\nDone!")
