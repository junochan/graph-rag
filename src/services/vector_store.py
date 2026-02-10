"""
Vector store abstraction layer with pluggable backends.
Default implementation: Qdrant
"""

import hashlib
import uuid
from abc import ABC, abstractmethod
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from src.config import get_settings


class VectorStoreBase(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a new collection/index."""
        pass

    @abstractmethod
    def insert(
        self,
        collection_name: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]] | None = None,
    ) -> None:
        """Insert vectors with optional payloads."""
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    def delete(self, collection_name: str, ids: list[str]) -> None:
        """Delete vectors by IDs."""
        pass

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        pass


def _string_to_uuid(s: str) -> str:
    """Convert a string ID to a valid UUID format for Qdrant."""
    # Use MD5 hash to generate deterministic UUID from string
    hash_bytes = hashlib.md5(s.encode()).digest()
    return str(uuid.UUID(bytes=hash_bytes))


class QdrantVectorStore(VectorStoreBase):
    """Qdrant vector store implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: str | None = None,
    ):
        # Disable version check for compatibility
        self.client = QdrantClient(
            host=host, 
            port=port, 
            api_key=api_key,
            check_compatibility=False,
        )

    def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a new Qdrant collection."""
        if self.collection_exists(collection_name):
            return

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=dimension,
                distance=qdrant_models.Distance.COSINE,
            ),
        )

    def _convert_id(self, id_: str) -> str:
        """Convert string ID to UUID format for Qdrant."""
        # If already a valid UUID, return as-is
        try:
            uuid.UUID(id_)
            return id_
        except ValueError:
            pass
        
        # Convert to UUID
        return _string_to_uuid(id_)

    def insert(
        self,
        collection_name: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]] | None = None,
    ) -> None:
        """Insert vectors into Qdrant collection."""
        points = []
        for i, (id_, vector) in enumerate(zip(ids, vectors)):
            payload = payloads[i] if payloads else {}
            # Store original ID in payload for reference
            payload["_original_id"] = id_
            
            points.append(
                qdrant_models.PointStruct(
                    id=self._convert_id(id_),
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=collection_name, points=points)

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in Qdrant."""
        query_filter = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key=key,
                        match=qdrant_models.MatchValue(value=value),
                    )
                )
            query_filter = qdrant_models.Filter(must=must_conditions)

        # Use query method (works with both old and new Qdrant client versions)
        try:
            # Try new API first (query)
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                query_filter=query_filter,
            )
            # New API returns QueryResponse with .points
            hits = results.points if hasattr(results, 'points') else results
        except AttributeError:
            # Fall back to old API (search)
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
            )
            hits = results

        return [
            {
                "id": hit.payload.get("_original_id", str(hit.id)),
                "score": hit.score,
                "payload": {k: v for k, v in hit.payload.items() if k != "_original_id"},
            }
            for hit in hits
        ]

    def delete(self, collection_name: str, ids: list[str]) -> None:
        """Delete vectors from Qdrant collection."""
        converted_ids = [self._convert_id(id_) for id_ in ids]
        self.client.delete(
            collection_name=collection_name,
            points_selector=qdrant_models.PointIdsList(points=converted_ids),
        )

    def collection_exists(self, collection_name: str) -> bool:
        """Check if Qdrant collection exists."""
        try:
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False


def get_vector_store() -> VectorStoreBase:
    """Factory function to get configured vector store instance."""
    settings = get_settings()
    vs_config = settings.vector_store

    if vs_config.type == "qdrant":
        return QdrantVectorStore(
            host=vs_config.qdrant_host,
            port=vs_config.qdrant_port,
            api_key=vs_config.qdrant_api_key,
        )
    elif vs_config.type == "milvus":
        # TODO: Implement MilvusVectorStore
        raise NotImplementedError("Milvus vector store not implemented yet")
    elif vs_config.type == "chroma":
        # TODO: Implement ChromaVectorStore
        raise NotImplementedError("Chroma vector store not implemented yet")
    elif vs_config.type == "faiss":
        # TODO: Implement FAISSVectorStore
        raise NotImplementedError("FAISS vector store not implemented yet")
    else:
        raise ValueError(f"Unknown vector store type: {vs_config.type}")
