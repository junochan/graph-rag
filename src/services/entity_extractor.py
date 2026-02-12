"""
LLM-based entity and relationship extraction service.
Inspired by Microsoft GraphRAG and RAG-Anything.
"""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from src.services.llm import get_llm

logger = logging.getLogger(__name__)


class Entity(BaseModel):
    """Extracted entity."""

    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (e.g., person, organization, location, concept)")
    description: str = Field(default="", description="Entity description")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class Relationship(BaseModel):
    """Extracted relationship between entities."""

    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    relation_type: str = Field(..., description="Relationship type")
    description: str = Field(default="", description="Relationship description")
    weight: float = Field(default=1.0, description="Relationship weight/strength")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class ExtractionResult(BaseModel):
    """Result of entity and relationship extraction."""

    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    source_text: str = Field(default="", description="Original source text")
    chunk_id: str = Field(default="", description="Chunk identifier")


# Default entity types for knowledge graph
DEFAULT_ENTITY_TYPES = [
    "person",        # 人物
    "organization",  # 组织/公司
    "location",      # 地点
    "event",         # 事件
    "concept",       # 概念
    "product",       # 产品
    "technology",    # 技术
    "time",          # 时间
    "document",      # 文档
]

# Default relationship types
DEFAULT_RELATION_TYPES = [
    "related_to",    # 相关
    "belongs_to",    # 属于
    "located_in",    # 位于
    "works_for",     # 工作于
    "created_by",    # 创建
    "part_of",       # 组成部分
    "causes",        # 导致
    "uses",          # 使用
    "mentions",      # 提及
    "similar_to",    # 相似
]


ENTITY_EXTRACTION_PROMPT = '''You are an expert at extracting knowledge graph entities and relationships from text.

## Task
Extract all entities and relationships from the given text. Focus on important concepts, people, organizations, locations, events, and their connections.

## Entity Types
{entity_types}

## Relationship Types
{relation_types}

## Output Format
Output a valid JSON object with the following structure:
```json
{{
  "entities": [
    {{
      "name": "entity name",
      "type": "entity type from the list above",
      "description": "brief description of the entity"
    }}
  ],
  "relationships": [
    {{
      "source": "source entity name",
      "target": "target entity name", 
      "relation_type": "relationship type from the list above",
      "description": "brief description of the relationship"
    }}
  ]
}}
```

## Rules
1. Extract ALL meaningful entities, not just the most obvious ones
2. Entity names should be normalized (e.g., "Microsoft Corporation" -> "Microsoft")
3. Use the provided entity types; if none fit, use the closest match
4. Each relationship must reference entities that exist in the entities list
5. Avoid duplicate entities (same name and type)
6. Keep descriptions short (under 50 characters each)
7. Output ONLY the JSON object, no additional text, no comments, no trailing commas
8. Ensure the JSON is complete and valid — do NOT truncate

## Text to analyze:
{text}

## JSON Output:'''


class EntityExtractor:
    """Extract entities and relationships from text using LLM."""

    def __init__(
        self,
        entity_types: list[str] | None = None,
        relation_types: list[str] | None = None,
    ):
        self.entity_types = entity_types or DEFAULT_ENTITY_TYPES
        self.relation_types = relation_types or DEFAULT_RELATION_TYPES
        self.llm = get_llm()

    def extract(self, text: str, chunk_id: str = "") -> ExtractionResult:
        """
        Extract entities and relationships from text.

        Args:
            text: Text to analyze
            chunk_id: Optional chunk identifier

        Returns:
            ExtractionResult with entities and relationships
        """
        if not text.strip():
            return ExtractionResult(source_text=text, chunk_id=chunk_id)

        prompt = ENTITY_EXTRACTION_PROMPT.format(
            entity_types=", ".join(self.entity_types),
            relation_types=", ".join(self.relation_types),
            text=text,
        )

        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": "You are a knowledge graph extraction expert. Always output valid, complete JSON. Never truncate the output."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=8192,  # Ensure enough room for complete JSON output
            )

            # Parse JSON from response
            result = self._parse_response(response)
            result.source_text = text
            result.chunk_id = chunk_id
            return result

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return ExtractionResult(source_text=text, chunk_id=chunk_id)

    def extract_batch(self, chunks: list[str]) -> list[ExtractionResult]:
        """
        Extract entities and relationships from multiple text chunks.

        Args:
            chunks: List of text chunks

        Returns:
            List of ExtractionResult
        """
        results = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{i}"
            result = self.extract(chunk, chunk_id)
            results.append(result)
        return results

    def merge_results(self, results: list[ExtractionResult]) -> ExtractionResult:
        """
        Merge multiple extraction results, deduplicating entities.

        Args:
            results: List of ExtractionResult to merge

        Returns:
            Merged ExtractionResult
        """
        entity_map: dict[str, Entity] = {}
        relationships: list[Relationship] = []

        for result in results:
            # Deduplicate entities by name (case-insensitive)
            for entity in result.entities:
                key = f"{entity.name.lower()}:{entity.type.lower()}"
                if key not in entity_map:
                    entity_map[key] = entity
                else:
                    # Merge descriptions if different
                    existing = entity_map[key]
                    if entity.description and entity.description != existing.description:
                        existing.description = f"{existing.description}; {entity.description}"

            # Add all relationships (may have duplicates)
            relationships.extend(result.relationships)

        # Deduplicate relationships
        rel_set = set()
        unique_relationships = []
        for rel in relationships:
            key = f"{rel.source.lower()}-{rel.relation_type.lower()}-{rel.target.lower()}"
            if key not in rel_set:
                rel_set.add(key)
                unique_relationships.append(rel)

        return ExtractionResult(
            entities=list(entity_map.values()),
            relationships=unique_relationships,
        )

    @staticmethod
    def _fix_json(text: str) -> str:
        """Attempt to fix common JSON issues from LLM output."""
        # Remove code-fence markers (```json ... ```)
        text = re.sub(r"```(?:json)?\s*", "", text)

        # Remove single-line JS/C-style comments  ( // ... )
        text = re.sub(r"//[^\n]*", "", text)

        # Remove trailing commas before } or ]  (e.g.  , } → } )
        text = re.sub(r",\s*([}\]])", r"\1", text)

        # If the JSON is truncated mid-string, try to close it gracefully.
        # Count open vs close braces/brackets to detect truncation.
        opens = text.count("{") + text.count("[")
        closes = text.count("}") + text.count("]")
        if opens > closes:
            # Ensure we're not inside an unterminated string
            # Simple heuristic: strip to last complete entry, then close
            diff = opens - closes
            # Try appending the missing closers
            # Detect the order of openers that are unclosed
            stack: list[str] = []
            in_string = False
            escape = False
            for ch in text:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch in ("{", "["):
                    stack.append(ch)
                elif ch == "}" and stack and stack[-1] == "{":
                    stack.pop()
                elif ch == "]" and stack and stack[-1] == "[":
                    stack.pop()

            # Close in reverse order
            for opener in reversed(stack):
                text += "]" if opener == "[" else "}"

            # If we were inside a string, close it first
            if in_string:
                text = text.rstrip()
                if not text.endswith('"'):
                    text += '"'
                # re-close containers
                for opener in reversed(stack):
                    text += "]" if opener == "[" else "}"

        return text

    def _parse_response(self, response: str) -> ExtractionResult:
        """Parse LLM response to ExtractionResult."""
        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            logger.warning("No JSON found in response")
            return ExtractionResult()

        raw_json = json_match.group()

        # Attempt 1: parse as-is
        data = None
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            pass

        # Attempt 2: fix common issues and retry
        if data is None:
            try:
                fixed = self._fix_json(raw_json)
                data = json.loads(fixed)
                logger.info("JSON parsed successfully after auto-fix")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON even after fix attempt: {e}")
                return ExtractionResult()

        entities = []
        for e in data.get("entities", []):
            try:
                entities.append(Entity(
                    name=e.get("name", ""),
                    type=e.get("type", "concept").lower(),
                    description=e.get("description", ""),
                    properties=e.get("properties", {}),
                ))
            except Exception as ex:
                logger.warning(f"Failed to parse entity: {ex}")

        relationships = []
        for r in data.get("relationships", []):
            try:
                relationships.append(Relationship(
                    source=r.get("source", ""),
                    target=r.get("target", ""),
                    relation_type=r.get("relation_type", "related_to").lower(),
                    description=r.get("description", ""),
                    weight=r.get("weight", 1.0),
                    properties=r.get("properties", {}),
                ))
            except Exception as ex:
                logger.warning(f"Failed to parse relationship: {ex}")

        return ExtractionResult(entities=entities, relationships=relationships)


def get_entity_extractor(
    entity_types: list[str] | None = None,
    relation_types: list[str] | None = None,
) -> EntityExtractor:
    """Get entity extractor instance."""
    return EntityExtractor(entity_types=entity_types, relation_types=relation_types)
