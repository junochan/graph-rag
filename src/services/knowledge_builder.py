"""
Knowledge Graph Builder Service.
Orchestrates document parsing, entity extraction, and graph construction.
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import Any, BinaryIO

from pydantic import BaseModel, Field

from src.config import get_settings
from src.services.document_parser import get_document_parser, get_text_chunker
from src.services.embedding import get_embedding_model
from src.services.entity_extractor import ExtractionResult, get_entity_extractor
from src.services.graph_store import get_graph_service
from src.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class BuildResult(BaseModel):
    """Result of knowledge graph building."""

    success: bool = Field(default=False)
    document_id: str = Field(default="")
    chunks_count: int = Field(default=0)
    entities_count: int = Field(default=0)
    relationships_count: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
    processing_time: float = Field(default=0.0)


class KnowledgeBuilder:
    """Build knowledge graph from documents."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize services lazily
        self._parser = None
        self._chunker = None
        self._extractor = None
        self._graph_service = None
        self._vector_store = None
        self._embedding_model = None

    @property
    def parser(self):
        if self._parser is None:
            self._parser = get_document_parser()
        return self._parser

    @property
    def chunker(self):
        if self._chunker is None:
            self._chunker = get_text_chunker(self.chunk_size, self.chunk_overlap)
        return self._chunker

    @property
    def extractor(self):
        if self._extractor is None:
            self._extractor = get_entity_extractor()
        return self._extractor

    @property
    def graph_service(self):
        if self._graph_service is None:
            self._graph_service = get_graph_service()
            self._graph_service.connect()
        return self._graph_service

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def _generate_id(self, content: str, prefix: str = "") -> str:
        """Generate deterministic ID from content."""
        hash_obj = hashlib.md5(content.encode())
        return f"{prefix}{hash_obj.hexdigest()[:16]}"

    def build_from_file(
        self,
        file: BinaryIO,
        filename: str,
        space: str | None = None,
        collection: str | None = None,
    ) -> BuildResult:
        """
        Build knowledge graph from uploaded file.

        Args:
            file: File-like object
            filename: Original filename
            space: Graph space name
            collection: Vector collection name

        Returns:
            BuildResult
        """
        start_time = time.time()
        errors = []

        settings = get_settings()
        space = space or settings.nebula.space
        collection = collection or settings.vector_store.qdrant_collection

        # Parse document
        try:
            text = self.parser.parse(file, filename)
        except Exception as e:
            return BuildResult(
                success=False,
                errors=[f"Document parsing failed: {e}"],
                processing_time=time.time() - start_time,
            )

        # Build from parsed text
        result = self.build_from_text(
            text=text,
            source_name=filename,
            space=space,
            collection=collection,
        )
        result.processing_time = time.time() - start_time
        return result

    def build_from_text(
        self,
        text: str,
        source_name: str = "text_input",
        space: str | None = None,
        collection: str | None = None,
    ) -> BuildResult:
        """
        Build knowledge graph from text.

        Args:
            text: Text content
            source_name: Source name/identifier
            space: Graph space name
            collection: Vector collection name

        Returns:
            BuildResult
        """
        start_time = time.time()
        errors = []

        settings = get_settings()
        space = space or settings.nebula.space
        collection = collection or settings.vector_store.qdrant_collection

        # Generate document ID
        doc_id = self._generate_id(f"{source_name}:{text[:100]}", "doc_")
        timestamp = int(datetime.now().timestamp())

        # Split into chunks
        chunks = self.chunker.split(text)
        if not chunks:
            return BuildResult(
                success=False,
                document_id=doc_id,
                errors=["No text content to process"],
                processing_time=time.time() - start_time,
            )

        logger.info(f"Split document into {len(chunks)} chunks")

        # Create document vertex
        try:
            self.graph_service.insert_vertex(
                tag_name="document",
                vid=doc_id,
                properties={
                    "name": source_name,
                    "description": f"Source document: {source_name}",
                    "file_type": source_name.split(".")[-1] if "." in source_name else "text",
                    "source_path": source_name,
                    "created_at": timestamp,
                },
                space=space,
            )
        except Exception as e:
            errors.append(f"Document vertex creation failed: {e}")

        # Process chunks
        chunk_ids = []
        chunk_texts = []
        all_entities = []
        all_relationships = []

        for i, chunk in enumerate(chunks):
            chunk_id = self._generate_id(f"{doc_id}:{i}:{chunk[:50]}", "chunk_")
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk)

            # Create chunk vertex
            try:
                self.graph_service.insert_vertex(
                    tag_name="chunk",
                    vid=chunk_id,
                    properties={
                        "content": chunk[:1000],  # Truncate for storage
                        "chunk_index": i,
                        "document_id": doc_id,
                        "created_at": timestamp,
                    },
                    space=space,
                )

                # Link document to chunk
                self.graph_service.insert_edge(
                    edge_type="contains",
                    src_vid=doc_id,
                    dst_vid=chunk_id,
                    properties={"chunk_index": i},
                    space=space,
                )
            except Exception as e:
                errors.append(f"Chunk {i} creation failed: {e}")

            # Extract entities and relationships
            try:
                extraction = self.extractor.extract(chunk, chunk_id)
                all_entities.extend(extraction.entities)
                all_relationships.extend(extraction.relationships)

                logger.info(f"Chunk {i}: extracted {len(extraction.entities)} entities, {len(extraction.relationships)} relationships")
            except Exception as e:
                errors.append(f"Entity extraction for chunk {i} failed: {e}")

        # Merge and deduplicate entities
        merged = self.extractor.merge_results([
            ExtractionResult(entities=all_entities, relationships=all_relationships)
        ])

        # Create entity vertices
        entity_vid_map = {}  # name -> vid mapping
        entities_created = 0

        for entity in merged.entities:
            entity_vid = self._generate_id(f"{entity.name}:{entity.type}", "e_")
            entity_vid_map[entity.name.lower()] = entity_vid

            # Determine tag based on entity type
            tag_name = entity.type if entity.type in ["person", "organization", "location", "event", "concept"] else "entity"

            try:
                self.graph_service.insert_vertex(
                    tag_name=tag_name,
                    vid=entity_vid,
                    properties={
                        "name": entity.name,
                        "description": entity.description,
                        "source_chunk": entity.properties.get("source_chunk", ""),
                        "created_at": timestamp,
                    } if tag_name != "entity" else {
                        "name": entity.name,
                        "type": entity.type,
                        "description": entity.description,
                        "source_chunk": entity.properties.get("source_chunk", ""),
                        "created_at": timestamp,
                    },
                    space=space,
                )
                entities_created += 1
            except Exception as e:
                errors.append(f"Entity '{entity.name}' creation failed: {e}")

        # Create relationship edges
        relationships_created = 0

        for rel in merged.relationships:
            source_vid = entity_vid_map.get(rel.source.lower())
            target_vid = entity_vid_map.get(rel.target.lower())

            if not source_vid or not target_vid:
                continue

            # Use appropriate edge type
            edge_type = rel.relation_type if rel.relation_type in [
                "related_to", "belongs_to", "located_in", "works_for",
                "created_by", "part_of", "causes", "uses", "mentions", "similar_to"
            ] else "related_to"

            try:
                self.graph_service.insert_edge(
                    edge_type=edge_type,
                    src_vid=source_vid,
                    dst_vid=target_vid,
                    properties={
                        "description": rel.description,
                        "weight": rel.weight,
                    },
                    space=space,
                )
                relationships_created += 1
            except Exception as e:
                errors.append(f"Relationship '{rel.source}->{rel.target}' creation failed: {e}")

        # Create vector embeddings for chunks
        try:
            # Ensure collection exists
            self.vector_store.create_collection(collection, self.embedding_model.dimension)

            # Generate embeddings
            embeddings = self.embedding_model.embed(chunk_texts)

            # Prepare payloads
            payloads = []
            for i, (chunk_id, chunk_text) in enumerate(zip(chunk_ids, chunk_texts)):
                payloads.append({
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "document_name": source_name,
                    "chunk_index": i,
                    "text": chunk_text,
                })

            # Insert vectors
            self.vector_store.insert(collection, chunk_ids, embeddings, payloads)
            logger.info(f"Created {len(chunk_ids)} vector embeddings")

        except Exception as e:
            errors.append(f"Vector embedding failed: {e}")

        # Also create embeddings for entities
        try:
            entity_ids = []
            entity_texts = []

            for entity in merged.entities:
                entity_vid = entity_vid_map.get(entity.name.lower())
                if entity_vid:
                    entity_ids.append(entity_vid)
                    # Combine name and description for embedding
                    entity_text = f"{entity.name}: {entity.description}" if entity.description else entity.name
                    entity_texts.append(entity_text)

            if entity_ids:
                entity_embeddings = self.embedding_model.embed(entity_texts)
                entity_payloads = [
                    {
                        "entity_id": eid,
                        "name": entity.name,
                        "type": entity.type,
                        "description": entity.description,
                        "is_entity": True,
                    }
                    for eid, entity in zip(entity_ids, merged.entities)
                ]
                self.vector_store.insert(collection, entity_ids, entity_embeddings, entity_payloads)
                logger.info(f"Created {len(entity_ids)} entity vector embeddings")

        except Exception as e:
            errors.append(f"Entity embedding failed: {e}")

        return BuildResult(
            success=len(errors) == 0 or (entities_created > 0),
            document_id=doc_id,
            chunks_count=len(chunks),
            entities_count=entities_created,
            relationships_count=relationships_created,
            errors=errors,
            processing_time=time.time() - start_time,
        )


def get_knowledge_builder(
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> KnowledgeBuilder:
    """Get knowledge builder instance."""
    return KnowledgeBuilder(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
