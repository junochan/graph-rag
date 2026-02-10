"""
Pydantic models for API request/response schemas.
"""

from typing import Any

from pydantic import BaseModel, Field


# ==================== Data Build Schemas ====================


class EntityData(BaseModel):
    """Entity data for graph construction."""

    id: str = Field(..., description="Unique entity ID")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type/tag")
    properties: dict[str, Any] = Field(default_factory=dict, description="Entity properties")
    text: str | None = Field(default=None, description="Text content for embedding")


class RelationData(BaseModel):
    """Relation data for graph construction."""

    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relation_type: str = Field(..., description="Relation type")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relation properties")


class BuildRequest(BaseModel):
    """Request schema for data build endpoint."""

    entities: list[EntityData] = Field(..., description="List of entities to build")
    relations: list[RelationData] = Field(default_factory=list, description="List of relations")
    collection: str | None = Field(default=None, description="Vector collection name (optional)")
    space: str | None = Field(default=None, description="Graph space name (optional)")


class BuildResponse(BaseModel):
    """Response schema for data build endpoint."""

    success: bool = Field(..., description="Whether the build was successful")
    message: str = Field(..., description="Status message")
    entities_count: int = Field(..., description="Number of entities processed")
    relations_count: int = Field(..., description="Number of relations processed")
    errors: list[str] = Field(default_factory=list, description="List of errors if any")


# ==================== Data Retrieve Schemas ====================


class RetrieveRequest(BaseModel):
    """Request schema for data retrieve endpoint."""

    query: str = Field(..., description="Query text for retrieval")
    top_k: int = Field(default=10, description="Number of top results to return")
    collection: str | None = Field(default=None, description="Vector collection name (optional)")
    space: str | None = Field(default=None, description="Graph space name (optional)")
    expand_graph: bool = Field(default=True, description="Whether to expand graph neighbors")
    graph_depth: int = Field(default=1, description="Depth of graph expansion")
    use_llm: bool = Field(default=False, description="Whether to use LLM for answer generation")


class RetrievedEntity(BaseModel):
    """Retrieved entity with score."""

    id: str = Field(..., description="Entity ID")
    name: str = Field(default="", description="Entity name")
    type: str = Field(default="", description="Entity type")
    score: float = Field(..., description="Similarity score")
    properties: dict[str, Any] = Field(default_factory=dict, description="Entity properties")
    text: str | None = Field(default=None, description="Original text content")


class GraphContext(BaseModel):
    """Graph context from expansion."""

    neighbors: list[dict[str, Any]] = Field(default_factory=list, description="Neighboring entities")
    relations: list[dict[str, Any]] = Field(default_factory=list, description="Connected relations")
    paths: list[dict[str, Any]] = Field(default_factory=list, description="Graph paths")


class RetrieveResponse(BaseModel):
    """Response schema for data retrieve endpoint."""

    success: bool = Field(..., description="Whether the retrieval was successful")
    query: str = Field(..., description="Original query")
    results: list[RetrievedEntity] = Field(default_factory=list, description="Retrieved entities")
    graph_context: GraphContext | None = Field(default=None, description="Graph context if expanded")
    answer: str | None = Field(default=None, description="LLM generated answer if requested")
    errors: list[str] = Field(default_factory=list, description="List of errors if any")


# ==================== Schema Init Schemas ====================


class InitSchemaRequest(BaseModel):
    """Request schema for schema initialization."""

    space: str | None = Field(default=None, description="Graph space name")
    tags: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Tags to create: {tag_name: {prop_name: prop_type}}",
    )
    edge_types: dict[str, dict[str, str] | None] = Field(
        default_factory=dict,
        description="Edge types to create: {edge_name: {prop_name: prop_type} or None}",
    )


class InitSchemaResponse(BaseModel):
    """Response schema for schema initialization."""

    success: bool = Field(..., description="Whether the initialization was successful")
    message: str = Field(..., description="Status message")
    errors: list[str] = Field(default_factory=list, description="List of errors if any")
