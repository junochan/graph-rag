# Services module
"""
Services layer - contains all business logic.

- build: Knowledge graph construction from text/files
- retrieval: Knowledge retrieval (vector, graph, hybrid)
- embedding: Embedding model operations
- graph_store: Graph database operations
- knowledge_builder: Core knowledge building logic
- llm: LLM chat operations
- vector_store: Vector store operations
"""

from src.services.build import BuildService, get_build_service
from src.services.retrieval import (
    AnswerGenerationService,
    GraphContext,
    GraphEdge,
    GraphExpansionService,
    GraphNode,
    GraphSearchService,
    RetrievalResponse,
    RetrievalResult,
    RetrievalService,
    VectorSearchService,
    get_retrieval_service,
)

__all__ = [
    # Build
    "BuildService",
    "get_build_service",
    # Retrieval
    "RetrievalService",
    "get_retrieval_service",
    "VectorSearchService",
    "GraphSearchService",
    "GraphExpansionService",
    "AnswerGenerationService",
    # Data classes
    "RetrievalResult",
    "RetrievalResponse",
    "GraphNode",
    "GraphEdge",
    "GraphContext",
]
