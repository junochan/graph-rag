"""
Build API - handles HTTP request/response for knowledge graph construction.
Business logic is delegated to BuildService.
"""

import logging
from typing import Any

from flask import request
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage

from src.services.build import BuildService, get_build_service

logger = logging.getLogger(__name__)

api = Namespace("build", description="Knowledge graph construction operations")


# ============================================================================
# API Models
# ============================================================================


build_text_request = api.model(
    "BuildTextRequest",
    {
        "text": fields.String(required=True, description="Text content to process"),
        "source_name": fields.String(
            description="Source name/identifier", default="text_input"
        ),
        "space": fields.String(description="Graph space name (optional)"),
        "collection": fields.String(description="Vector collection name (optional)"),
        "chunk_size": fields.Integer(
            description="Chunk size for text splitting", default=1000
        ),
        "chunk_overlap": fields.Integer(
            description="Chunk overlap size", default=200
        ),
    },
)

build_response = api.model(
    "BuildResponse",
    {
        "success": fields.Boolean(description="Whether the build was successful"),
        "document_id": fields.String(description="Generated document ID"),
        "chunks_count": fields.Integer(description="Number of chunks created"),
        "entities_count": fields.Integer(description="Number of entities extracted"),
        "relationships_count": fields.Integer(
            description="Number of relationships created"
        ),
        "processing_time": fields.Float(description="Processing time in seconds"),
        "errors": fields.List(fields.String, description="List of errors if any"),
    },
)

init_schema_request = api.model(
    "InitSchemaRequest",
    {
        "space": fields.String(description="Graph space name (optional)"),
        "partition_num": fields.Integer(description="Number of partitions", default=10),
        "replica_factor": fields.Integer(description="Replica factor", default=1),
    },
)

init_schema_response = api.model(
    "InitSchemaResponse",
    {
        "success": fields.Boolean(description="Whether initialization was successful"),
        "space_initialized": fields.Boolean(description="Whether space was initialized"),
        "space": fields.String(description="Graph space name"),
        "schema_initialized": fields.Boolean(description="Whether schema was initialized"),
        "created_tags": fields.List(fields.String, description="Created tag names"),
        "created_edges": fields.List(fields.String, description="Created edge type names"),
        "errors": fields.List(fields.String, description="List of errors if any"),
    },
)

schema_info_response = api.model(
    "SchemaInfoResponse",
    {
        "success": fields.Boolean(description="Whether query was successful"),
        "space": fields.String(description="Graph space name"),
        "tags": fields.List(fields.String, description="Available tags"),
        "edge_types": fields.List(fields.String, description="Available edge types"),
        "error": fields.String(description="Error message if failed"),
    },
)

# File upload parser
file_upload_parser = api.parser()
file_upload_parser.add_argument(
    "file",
    location="files",
    type=FileStorage,
    required=True,
    help="File to upload (PDF, DOCX, TXT, MD)",
)
file_upload_parser.add_argument(
    "space", location="form", type=str, required=False, help="Graph space name"
)
file_upload_parser.add_argument(
    "collection",
    location="form",
    type=str,
    required=False,
    help="Vector collection name",
)
file_upload_parser.add_argument(
    "chunk_size",
    location="form",
    type=int,
    required=False,
    default=1000,
    help="Chunk size for text splitting",
)
file_upload_parser.add_argument(
    "chunk_overlap",
    location="form",
    type=int,
    required=False,
    default=200,
    help="Chunk overlap size",
)


# ============================================================================
# API Endpoints
# ============================================================================


@api.route("/text")
class BuildFromText(Resource):
    """Build knowledge graph from text input."""

    @api.expect(build_text_request)
    @api.marshal_with(build_response)
    @api.doc(
        description="Build knowledge graph from text. Extracts entities and relationships using LLM.",
        responses={200: "Success", 400: "Bad Request", 500: "Internal Server Error"},
    )
    def post(self) -> dict[str, Any]:
        """Build knowledge graph from text."""
        data = request.json or {}

        chunk_size = data.get("chunk_size", 1000)
        chunk_overlap = data.get("chunk_overlap", 200)
        service = get_build_service(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        result = service.build_from_text(
            text=data.get("text", ""),
            source_name=data.get("source_name", "text_input"),
            space=data.get("space"),
            collection=data.get("collection"),
        )

        return result.to_dict()


@api.route("/file")
class BuildFromFile(Resource):
    """Build knowledge graph from file upload."""

    @api.expect(file_upload_parser)
    @api.marshal_with(build_response)
    @api.doc(
        description="Build knowledge graph from uploaded file. Supports PDF, DOCX, TXT, MD.",
        responses={
            200: "Success",
            400: "Bad Request - Invalid file",
            500: "Internal Server Error",
        },
    )
    def post(self) -> dict[str, Any]:
        """Build knowledge graph from uploaded file."""
        args = file_upload_parser.parse_args()
        file: FileStorage = args["file"]

        chunk_size = args.get("chunk_size", 1000)
        chunk_overlap = args.get("chunk_overlap", 200)
        service = get_build_service(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        result = service.build_from_file(
            file=file,
            space=args.get("space"),
            collection=args.get("collection"),
        )

        return result.to_dict()


@api.route("/init-schema")
class InitSchema(Resource):
    """Initialize graph database schema."""

    @api.expect(init_schema_request)
    @api.marshal_with(init_schema_response)
    @api.doc(
        description="Initialize graph space and schema (Tags and Edge Types). "
        "Call this before building knowledge graph.",
        responses={200: "Success", 500: "Internal Server Error"},
    )
    def post(self) -> dict[str, Any]:
        """Initialize graph schema."""
        data = request.json or {}
        service = get_build_service()

        result = service.initialize_schema(
            space=data.get("space"),
            partition_num=data.get("partition_num", 10),
            replica_factor=data.get("replica_factor", 1),
        )

        return result.to_dict()


@api.route("/schema")
class SchemaInfo(Resource):
    """Get current schema information."""

    @api.marshal_with(schema_info_response)
    @api.doc(
        description="Get current graph schema information (available Tags and Edge Types).",
        responses={200: "Success", 500: "Internal Server Error"},
    )
    def get(self) -> dict[str, Any]:
        """Get schema information."""
        space = request.args.get("space")
        service = get_build_service()

        result = service.get_schema_info(space=space)

        return result.to_dict()


@api.route("/health")
class Health(Resource):
    """Health check endpoint."""

    @api.doc("health_check")
    def get(self) -> dict[str, Any]:
        """Check build service health."""
        return {
            "status": "healthy",
            "service": "build",
        }
