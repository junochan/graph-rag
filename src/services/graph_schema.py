"""
Knowledge Graph Schema definition and initialization for NebulaGraph.
Defines Tags (vertex types), Edge Types, and provides initialization utilities.
"""

import logging
import time
from dataclasses import dataclass, field

from src.services.graph_store import NebulaGraphService, get_graph_service

logger = logging.getLogger(__name__)


@dataclass
class TagDefinition:
    """Definition of a Tag (vertex type) in NebulaGraph."""

    name: str
    properties: dict[str, str] = field(default_factory=dict)
    comment: str = ""


@dataclass
class EdgeTypeDefinition:
    """Definition of an Edge Type in NebulaGraph."""

    name: str
    properties: dict[str, str] = field(default_factory=dict)
    comment: str = ""


# ==================== Default Schema Definitions ====================

# Entity Tags (顶点类型)
DEFAULT_TAGS = [
    TagDefinition(
        name="entity",
        properties={
            "name": "string",
            "type": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        comment="Base entity tag for all extracted entities",
    ),
    TagDefinition(
        name="person",
        properties={
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        comment="Person entity",
    ),
    TagDefinition(
        name="organization",
        properties={
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        comment="Organization/Company entity",
    ),
    TagDefinition(
        name="location",
        properties={
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        comment="Location/Place entity",
    ),
    TagDefinition(
        name="event",
        properties={
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        comment="Event entity",
    ),
    TagDefinition(
        name="concept",
        properties={
            "name": "string",
            "description": "string",
            "source_chunk": "string",
            "created_at": "timestamp",
        },
        comment="Concept/Abstract entity",
    ),
    TagDefinition(
        name="document",
        properties={
            "name": "string",
            "description": "string",
            "file_type": "string",
            "source_path": "string",
            "created_at": "timestamp",
        },
        comment="Source document",
    ),
    TagDefinition(
        name="chunk",
        properties={
            "content": "string",
            "chunk_index": "int",
            "document_id": "string",
            "created_at": "timestamp",
        },
        comment="Text chunk from document",
    ),
]

# Edge Types (边类型)
DEFAULT_EDGE_TYPES = [
    EdgeTypeDefinition(
        name="related_to",
        properties={
            "description": "string",
            "weight": "double",
            "source_chunk": "string",
        },
        comment="General relationship between entities",
    ),
    EdgeTypeDefinition(
        name="belongs_to",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Membership/belonging relationship",
    ),
    EdgeTypeDefinition(
        name="located_in",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Location relationship",
    ),
    EdgeTypeDefinition(
        name="works_for",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Employment relationship",
    ),
    EdgeTypeDefinition(
        name="created_by",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Creation/authorship relationship",
    ),
    EdgeTypeDefinition(
        name="part_of",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Part-whole relationship",
    ),
    EdgeTypeDefinition(
        name="causes",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Causal relationship",
    ),
    EdgeTypeDefinition(
        name="uses",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Usage relationship",
    ),
    EdgeTypeDefinition(
        name="mentions",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Mention relationship",
    ),
    EdgeTypeDefinition(
        name="similar_to",
        properties={
            "description": "string",
            "weight": "double",
        },
        comment="Similarity relationship",
    ),
    EdgeTypeDefinition(
        name="contains",
        properties={
            "chunk_index": "int",
        },
        comment="Document contains chunk",
    ),
    EdgeTypeDefinition(
        name="extracted_from",
        properties={
            "chunk_id": "string",
        },
        comment="Entity extracted from chunk",
    ),
]


class GraphSchemaManager:
    """Manage knowledge graph schema in NebulaGraph."""

    def __init__(
        self,
        graph_service: NebulaGraphService | None = None,
        tags: list[TagDefinition] | None = None,
        edge_types: list[EdgeTypeDefinition] | None = None,
    ):
        self.graph_service = graph_service or get_graph_service()
        self.tags = tags or DEFAULT_TAGS
        self.edge_types = edge_types or DEFAULT_EDGE_TYPES

    def initialize_space(
        self,
        space_name: str | None = None,
        partition_num: int = 10,
        replica_factor: int = 1,
        vid_type: str = "FIXED_STRING(256)",
    ) -> dict:
        """
        Initialize graph space if not exists.

        Args:
            space_name: Graph space name (uses config default if None)
            partition_num: Number of partitions
            replica_factor: Replica factor
            vid_type: Vertex ID type

        Returns:
            Result dict with success status
        """
        try:
            self.graph_service.connect()
            space = space_name or self.graph_service.space

            result = self.graph_service.create_space_if_not_exists(
                space_name=space,
                partition_num=partition_num,
                replica_factor=replica_factor,
                vid_type=vid_type,
            )

            if not result["success"]:
                return {"success": False, "error": result.get("error")}

            # Wait for space to be ready
            logger.info(f"Waiting for space '{space}' to be ready...")
            time.sleep(3)

            return {"success": True, "space": space}

        except Exception as e:
            logger.error(f"Failed to initialize space: {e}")
            return {"success": False, "error": str(e)}

    def initialize_schema(self, space_name: str | None = None) -> dict:
        """
        Initialize all Tags and Edge Types in the graph space.

        Args:
            space_name: Graph space name

        Returns:
            Result dict with success status and details
        """
        errors = []
        created_tags = []
        created_edges = []

        try:
            self.graph_service.connect()
            space = space_name or self.graph_service.space

            # Create Tags
            for tag in self.tags:
                try:
                    result = self.graph_service.create_tag(
                        tag_name=tag.name,
                        properties=tag.properties,
                        space=space,
                    )
                    if result["success"]:
                        created_tags.append(tag.name)
                        logger.info(f"Created tag: {tag.name}")
                    else:
                        errors.append(f"Tag {tag.name}: {result.get('error')}")
                except Exception as e:
                    errors.append(f"Tag {tag.name}: {str(e)}")

            # Wait for tags to be ready
            time.sleep(2)

            # Create Edge Types
            for edge_type in self.edge_types:
                try:
                    result = self.graph_service.create_edge_type(
                        edge_name=edge_type.name,
                        properties=edge_type.properties,
                        space=space,
                    )
                    if result["success"]:
                        created_edges.append(edge_type.name)
                        logger.info(f"Created edge type: {edge_type.name}")
                    else:
                        errors.append(f"Edge {edge_type.name}: {result.get('error')}")
                except Exception as e:
                    errors.append(f"Edge {edge_type.name}: {str(e)}")

            return {
                "success": len(errors) == 0,
                "created_tags": created_tags,
                "created_edges": created_edges,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return {
                "success": False,
                "created_tags": created_tags,
                "created_edges": created_edges,
                "errors": errors + [str(e)],
            }

    def initialize_all(
        self,
        space_name: str | None = None,
        partition_num: int = 10,
        replica_factor: int = 1,
    ) -> dict:
        """
        Initialize both space and schema.

        Args:
            space_name: Graph space name
            partition_num: Number of partitions
            replica_factor: Replica factor

        Returns:
            Combined result dict
        """
        # Initialize space
        space_result = self.initialize_space(
            space_name=space_name,
            partition_num=partition_num,
            replica_factor=replica_factor,
        )

        if not space_result["success"]:
            return {
                "success": False,
                "space_initialized": False,
                "schema_initialized": False,
                "error": space_result.get("error"),
            }

        # Initialize schema
        schema_result = self.initialize_schema(space_name)

        return {
            "success": schema_result["success"],
            "space_initialized": True,
            "space": space_result.get("space"),
            "schema_initialized": schema_result["success"],
            "created_tags": schema_result.get("created_tags", []),
            "created_edges": schema_result.get("created_edges", []),
            "errors": schema_result.get("errors", []),
        }

    def get_schema_info(self, space_name: str | None = None) -> dict:
        """
        Get current schema information from graph space.

        Args:
            space_name: Graph space name

        Returns:
            Schema info dict
        """
        try:
            self.graph_service.connect()
            space = space_name or self.graph_service.space

            # Get tags
            tags_result = self.graph_service.execute("SHOW TAGS", space)
            tags = [row.get("Name") for row in tags_result.get("data", [])] if tags_result["success"] else []

            # Get edges
            edges_result = self.graph_service.execute("SHOW EDGES", space)
            edges = [row.get("Name") for row in edges_result.get("data", [])] if edges_result["success"] else []

            return {
                "success": True,
                "space": space,
                "tags": tags,
                "edge_types": edges,
            }

        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {"success": False, "error": str(e)}


def get_schema_manager(
    tags: list[TagDefinition] | None = None,
    edge_types: list[EdgeTypeDefinition] | None = None,
) -> GraphSchemaManager:
    """Get schema manager instance."""
    return GraphSchemaManager(tags=tags, edge_types=edge_types)
