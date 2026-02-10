"""
Retrieve API - handles HTTP request/response for knowledge retrieval.
Business logic is delegated to RetrievalService.
"""

import logging
from typing import Any

from flask import request
from flask_restx import Namespace, Resource, fields

from src.config import get_settings
from src.services.graph_store import get_graph_service
from src.services.retrieval import get_retrieval_service

logger = logging.getLogger(__name__)

api = Namespace("retrieve", description="Knowledge retrieval operations")

# ============================================================================
# API Models
# ============================================================================

retrieve_request = api.model(
    "RetrieveRequest",
    {
        "query": fields.String(required=True, description="Query text"),
        "search_type": fields.String(
            default="hybrid",
            description="Search type: hybrid, vector, or graph",
            enum=["hybrid", "vector", "graph"],
        ),
        "top_k": fields.Integer(default=10, description="Max results to return"),
        "expand_graph": fields.Boolean(
            default=True, description="Whether to expand graph context"
        ),
        "graph_depth": fields.Integer(default=2, description="Graph expansion depth"),
        "collection": fields.String(description="Vector collection name (optional)"),
        "space": fields.String(description="Graph space name (optional)"),
        "use_llm": fields.Boolean(
            default=False, description="Generate answer using LLM"
        ),
    },
)

graph_node = api.model(
    "GraphNode",
    {
        "id": fields.String(description="Node ID"),
        "name": fields.String(description="Node name"),
        "type": fields.String(description="Node type"),
        "properties": fields.Raw(description="Node properties"),
    },
)

graph_edge = api.model(
    "GraphEdge",
    {
        "source": fields.String(description="Source node ID"),
        "source_name": fields.String(description="Source node name"),
        "target": fields.String(description="Target node ID"),
        "target_name": fields.String(description="Target node name"),
        "type": fields.String(description="Edge type"),
        "properties": fields.Raw(description="Edge properties"),
    },
)

graph_context = api.model(
    "GraphContext",
    {
        "nodes": fields.List(fields.Nested(graph_node)),
        "edges": fields.List(fields.Nested(graph_edge)),
        "subgraph_summary": fields.String(description="Summary of the subgraph"),
    },
)

retrieval_result = api.model(
    "RetrievalResult",
    {
        "id": fields.String(description="Result ID"),
        "name": fields.String(description="Result name"),
        "type": fields.String(description="Result type (entity/chunk)"),
        "score": fields.Float(description="Relevance score"),
        "text": fields.String(description="Text content"),
        "is_entity": fields.Boolean(description="Whether this is an entity"),
        "properties": fields.Raw(description="Additional properties"),
    },
)

retrieve_response = api.model(
    "RetrieveResponse",
    {
        "success": fields.Boolean(description="Whether the request succeeded"),
        "query": fields.String(description="Original query"),
        "results": fields.List(fields.Nested(retrieval_result)),
        "graph_context": fields.Nested(graph_context, allow_null=True),
        "answer": fields.String(description="LLM-generated answer", allow_null=True),
        "sources": fields.List(fields.String, description="Source documents"),
        "errors": fields.List(fields.String, description="Error messages"),
    },
)


# ============================================================================
# API Endpoints
# ============================================================================


@api.route("/")
class Retrieve(Resource):
    """Knowledge retrieval endpoint."""

    @api.doc("retrieve")
    @api.expect(retrieve_request)
    @api.marshal_with(retrieve_response)
    def post(self) -> dict[str, Any]:
        """
        Retrieve knowledge from the graph and vector stores.

        Supports three search modes:
        - **hybrid**: Combines vector similarity search with graph traversal (recommended)
        - **vector**: Uses only vector similarity search
        - **graph**: Uses only graph database queries (extracts entities from query using LLM)
        """
        data = request.get_json() or {}

        # Validate required fields
        query = data.get("query", "").strip()
        if not query:
            return {
                "success": False,
                "query": "",
                "results": [],
                "graph_context": None,
                "answer": None,
                "sources": [],
                "errors": ["Query cannot be empty"],
            }

        # Extract parameters
        search_type = data.get("search_type", "hybrid")
        if search_type not in ("hybrid", "vector", "graph"):
            search_type = "hybrid"

        service = get_retrieval_service()

        # Delegate to service
        response = service.retrieve(
            query=query,
            search_type=search_type,
            collection=data.get("collection"),
            space=data.get("space"),
            top_k=data.get("top_k", 10),
            expand_graph=data.get("expand_graph", True),
            graph_depth=data.get("graph_depth", 2),
            use_llm=data.get("use_llm", False),
        )

        return response.to_dict()


@api.route("/health")
class Health(Resource):
    """Health check endpoint."""

    @api.doc("health_check")
    def get(self) -> dict[str, Any]:
        """Check retrieval service health."""
        return {
            "status": "healthy",
            "service": "retrieval",
        }


# ============================================================================
# Graph Query API Models
# ============================================================================


graph_query_request = api.model(
    "GraphQueryRequest",
    {
        "query": fields.String(required=True, description="nGQL query to execute"),
        "space": fields.String(description="Graph space name (optional)"),
    },
)

graph_query_response = api.model(
    "GraphQueryResponse",
    {
        "success": fields.Boolean(description="Whether the query succeeded"),
        "data": fields.List(fields.Raw, description="Query results"),
        "error": fields.String(description="Error message if failed"),
    },
)

entity_list_response = api.model(
    "EntityListResponse",
    {
        "success": fields.Boolean(description="Whether the request succeeded"),
        "count": fields.Integer(description="Number of entities returned"),
        "entities": fields.List(fields.Raw, description="List of entities"),
        "error": fields.String(description="Error message if failed"),
    },
)


# ============================================================================
# Graph Query Endpoints
# ============================================================================


@api.route("/graph-query")
class GraphQuery(Resource):
    """Execute direct nGQL queries on the graph database."""

    @api.doc("graph_query")
    @api.expect(graph_query_request)
    @api.marshal_with(graph_query_response)
    def post(self) -> dict[str, Any]:
        """
        Execute a direct nGQL query on the graph database.

        This endpoint allows executing raw nGQL queries for advanced use cases.
        Use with caution - only SELECT/MATCH queries are recommended.
        """
        data = request.get_json() or {}

        query = data.get("query", "").strip()
        if not query:
            return {
                "success": False,
                "data": [],
                "error": "Query cannot be empty",
            }

        settings = get_settings()
        space = data.get("space") or settings.nebula.space

        try:
            graph_service = get_graph_service()
            graph_service.connect()

            result = graph_service.execute(query, space)

            return {
                "success": result.get("success", False),
                "data": result.get("data", []),
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {
                "success": False,
                "data": [],
                "error": str(e),
            }


@api.route("/entities")
class ListEntities(Resource):
    """List entities from the graph database."""

    @api.doc("list_entities")
    @api.marshal_with(entity_list_response)
    def get(self) -> dict[str, Any]:
        """
        List entities from the graph database.

        Query parameters:
        - space: Graph space name (optional)
        - type: Entity type filter (person, organization, location, etc.)
        - limit: Maximum number of entities to return (default: 20)
        """
        settings = get_settings()
        space = request.args.get("space") or settings.nebula.space
        entity_type = request.args.get("type")
        limit = request.args.get("limit", 20, type=int)

        try:
            graph_service = get_graph_service()
            graph_service.connect()

            # Build query based on entity type
            if entity_type:
                query = f"""
                    MATCH (v:{entity_type})
                    RETURN id(v) AS id, v.{entity_type}.name AS name, 
                           v.{entity_type}.description AS description,
                           "{entity_type}" AS type
                    LIMIT {limit}
                """
            else:
                # Query all entity types
                entity_types = ["person", "organization", "location", "entity", "concept"]
                queries = []
                for et in entity_types:
                    queries.append(f"""
                        MATCH (v:{et})
                        RETURN id(v) AS id, v.{et}.name AS name,
                               v.{et}.description AS description,
                               "{et}" AS type
                        LIMIT {limit // len(entity_types) + 1}
                    """)

                # Execute each query and combine results
                all_entities = []
                for q in queries:
                    result = graph_service.execute(q, space)
                    if result.get("success") and result.get("data"):
                        all_entities.extend(result["data"])

                return {
                    "success": True,
                    "count": len(all_entities),
                    "entities": all_entities[:limit],
                    "error": None,
                }

            result = graph_service.execute(query, space)

            if result.get("success"):
                entities = result.get("data", [])
                return {
                    "success": True,
                    "count": len(entities),
                    "entities": entities,
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "count": 0,
                    "entities": [],
                    "error": result.get("error"),
                }

        except Exception as e:
            logger.error(f"List entities failed: {e}")
            return {
                "success": False,
                "count": 0,
                "entities": [],
                "error": str(e),
            }
