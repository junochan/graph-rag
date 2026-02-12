"""
Build service - handles knowledge graph construction from text and files.
"""

import logging
from dataclasses import dataclass, field
from io import BufferedReader, BytesIO
from typing import Any, BinaryIO

from werkzeug.datastructures import FileStorage

from src.config import get_settings
from src.services.graph_schema import get_schema_manager
from src.services.knowledge_builder import get_knowledge_builder

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class BuildResult:
    """Result from a build operation."""
    success: bool
    document_id: str = ""
    chunks_count: int = 0
    entities_count: int = 0
    relationships_count: int = 0
    processing_time: float = 0.0
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "document_id": self.document_id,
            "chunks_count": self.chunks_count,
            "entities_count": self.entities_count,
            "relationships_count": self.relationships_count,
            "processing_time": self.processing_time,
            "errors": self.errors,
        }


@dataclass
class SchemaInitResult:
    """Result from schema initialization."""
    success: bool
    space_initialized: bool = False
    space: str = ""
    schema_initialized: bool = False
    created_tags: list[str] = field(default_factory=list)
    created_edges: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "space_initialized": self.space_initialized,
            "space": self.space,
            "schema_initialized": self.schema_initialized,
            "created_tags": self.created_tags,
            "created_edges": self.created_edges,
            "errors": self.errors,
        }


@dataclass
class SchemaInfo:
    """Schema information result."""
    success: bool
    space: str = ""
    tags: list[str] = field(default_factory=list)
    edge_types: list[str] = field(default_factory=list)
    error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "space": self.space,
            "tags": self.tags,
            "edge_types": self.edge_types,
            "error": self.error,
        }


# ============================================================================
# Build Service
# ============================================================================


# Allowed file extensions
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", ".doc", ".md"}


class BuildService:
    """
    Service for building knowledge graphs from text and files.
    Coordinates text processing, entity extraction, and graph construction.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._builder = None
        self._schema_manager = None
    
    @property
    def builder(self):
        """Lazy-load knowledge builder."""
        if self._builder is None:
            self._builder = get_knowledge_builder(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        return self._builder
    
    @property
    def schema_manager(self):
        """Lazy-load schema manager."""
        if self._schema_manager is None:
            self._schema_manager = get_schema_manager()
        return self._schema_manager
    
    def build_from_text(
        self,
        text: str,
        source_name: str = "text_input",
        space: str | None = None,
        collection: str | None = None,
    ) -> BuildResult:
        """
        Build knowledge graph from text content.
        
        Args:
            text: Text content to process
            source_name: Name/identifier for the source
            space: Graph space name (optional)
            collection: Vector collection name (optional)
        """
        text = text.strip()
        if not text:
            return BuildResult(
                success=False,
                errors=["Text content is required"],
            )
        
        try:
            result = self.builder.build_from_text(
                text=text,
                source_name=source_name,
                space=space,
                collection=collection,
            )
            
            return BuildResult(
                success=result.success,
                document_id=result.document_id,
                chunks_count=result.chunks_count,
                entities_count=result.entities_count,
                relationships_count=result.relationships_count,
                processing_time=result.processing_time,
                errors=result.errors,
            )
        
        except Exception as e:
            logger.error(f"Build from text failed: {e}")
            return BuildResult(success=False, errors=[str(e)])
    
    def build_from_file(
        self,
        file: FileStorage,
        space: str | None = None,
        collection: str | None = None,
    ) -> BuildResult:
        """
        Build knowledge graph from uploaded file.
        
        Args:
            file: Uploaded file (FileStorage)
            space: Graph space name (optional)
            collection: Vector collection name (optional)
        """
        # Validate file
        if not file or not file.filename:
            return BuildResult(
                success=False,
                errors=["No file uploaded"],
            )
        
        filename = file.filename
        ext = self._get_file_extension(filename)
        
        if ext not in ALLOWED_EXTENSIONS:
            return BuildResult(
                success=False,
                errors=[
                    f"Unsupported file type: {ext}. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ],
            )
        
        try:
            result = self.builder.build_from_file(
                file=file.stream,
                filename=filename,
                space=space,
                collection=collection,
            )
            
            return BuildResult(
                success=result.success,
                document_id=result.document_id,
                chunks_count=result.chunks_count,
                entities_count=result.entities_count,
                relationships_count=result.relationships_count,
                processing_time=result.processing_time,
                errors=result.errors,
            )
        
        except Exception as e:
            logger.error(f"Build from file failed: {e}")
            return BuildResult(success=False, errors=[str(e)])
    
    def build_from_file_bytes(
        self,
        content: bytes,
        filename: str,
        space: str | None = None,
        collection: str | None = None,
    ) -> BuildResult:
        """
        Build knowledge graph from file bytes.
        
        Args:
            content: File content as bytes
            filename: Original filename
            space: Graph space name (optional)
            collection: Vector collection name (optional)
        """
        ext = self._get_file_extension(filename)
        
        if ext not in ALLOWED_EXTENSIONS:
            return BuildResult(
                success=False,
                errors=[
                    f"Unsupported file type: {ext}. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ],
            )
        
        try:
            file_stream = BytesIO(content)
            result = self.builder.build_from_file(
                file=file_stream,
                filename=filename,
                space=space,
                collection=collection,
            )
            
            return BuildResult(
                success=result.success,
                document_id=result.document_id,
                chunks_count=result.chunks_count,
                entities_count=result.entities_count,
                relationships_count=result.relationships_count,
                processing_time=result.processing_time,
                errors=result.errors,
            )
        
        except Exception as e:
            logger.error(f"Build from file bytes failed: {e}")
            return BuildResult(success=False, errors=[str(e)])
    
    def initialize_schema(
        self,
        space: str | None = None,
        partition_num: int = 10,
        replica_factor: int = 1,
    ) -> SchemaInitResult:
        """
        Initialize graph space and schema.
        
        Args:
            space: Graph space name (optional, uses default)
            partition_num: Number of partitions
            replica_factor: Replica factor
        """
        try:
            result = self.schema_manager.initialize_all(
                space_name=space,
                partition_num=partition_num,
                replica_factor=replica_factor,
            )
            
            return SchemaInitResult(
                success=result["success"],
                space_initialized=result.get("space_initialized", False),
                space=result.get("space", ""),
                schema_initialized=result.get("schema_initialized", False),
                created_tags=result.get("created_tags", []),
                created_edges=result.get("created_edges", []),
                errors=result.get("errors", []),
            )
        
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            return SchemaInitResult(success=False, errors=[str(e)])
    
    def get_schema_info(self, space: str | None = None) -> SchemaInfo:
        """
        Get current schema information.
        
        Args:
            space: Graph space name (optional, uses default)
        """
        try:
            result = self.schema_manager.get_schema_info(space_name=space)
            
            return SchemaInfo(
                success=result["success"],
                space=result.get("space", ""),
                tags=result.get("tags", []),
                edge_types=result.get("edge_types", []),
                error=result.get("error"),
            )
        
        except Exception as e:
            logger.error(f"Get schema info failed: {e}")
            return SchemaInfo(success=False, error=str(e))
    
    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Extract file extension from filename."""
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""
    
    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        """Check if file extension is allowed."""
        ext = BuildService._get_file_extension(filename)
        return ext in ALLOWED_EXTENSIONS


# ============================================================================
# Singleton Access
# ============================================================================


_build_service: BuildService | None = None


def get_build_service(
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> BuildService:
    """Get singleton build service instance."""
    global _build_service
    if _build_service is None:
        _build_service = BuildService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    return _build_service
