"""
Retrieval service - handles all retrieval logic including vector search,
graph search, and hybrid retrieval.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from src.config import get_settings
from src.services.embedding import get_embedding_model
from src.services.graph_store import get_graph_service
from src.services.llm import get_llm
from src.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from retrieval operation."""
    id: str
    name: str
    type: str  # "entity" or "chunk"
    score: float
    text: str
    is_entity: bool = False
    properties: dict = field(default_factory=dict)


@dataclass
class GraphNode:
    """Node in the graph context."""
    id: str
    name: str
    type: str
    properties: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Edge in the graph context."""
    source: str
    source_name: str
    target: str
    target_name: str
    type: str
    properties: dict = field(default_factory=dict)


@dataclass
class GraphContext:
    """Graph context containing nodes and edges."""
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        return f"Found {len(self.nodes)} related entities and {len(self.edges)} relationships"
    
    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"id": n.id, "name": n.name, "type": n.type, "properties": n.properties}
                for n in self.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "source_name": e.source_name,
                    "target": e.target,
                    "target_name": e.target_name,
                    "type": e.type,
                    "properties": e.properties,
                }
                for e in self.edges
            ],
            "subgraph_summary": self.summary,
        }


@dataclass
class TimingInfo:
    """Timing information for retrieval operations."""
    vector_search_ms: float = 0
    graph_search_ms: float = 0
    graph_expansion_ms: float = 0
    llm_ms: float = 0
    total_ms: float = 0
    
    def to_dict(self) -> dict:
        return {
            "vector_search_ms": round(self.vector_search_ms, 1),
            "graph_search_ms": round(self.graph_search_ms, 1),
            "graph_expansion_ms": round(self.graph_expansion_ms, 1),
            "llm_ms": round(self.llm_ms, 1),
            "total_ms": round(self.total_ms, 1),
        }


@dataclass
class RetrievalResponse:
    """Complete retrieval response."""
    success: bool
    query: str
    results: list[RetrievalResult] = field(default_factory=list)
    graph_context: GraphContext | None = None
    answer: str | None = None
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timing: TimingInfo = field(default_factory=TimingInfo)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "query": self.query,
            "results": [
                {
                    "id": r.id,
                    "name": r.name,
                    "type": r.type,
                    "score": r.score,
                    "text": r.text,
                    "is_entity": r.is_entity,
                    "properties": r.properties,
                }
                for r in self.results
            ],
            "graph_context": self.graph_context.to_dict() if self.graph_context else None,
            "answer": self.answer,
            "sources": list(set(self.sources)),
            "errors": self.errors,
            "timing": self.timing.to_dict(),
        }


# Minimum similarity score threshold for vector search results
MIN_SIMILARITY_THRESHOLD = 0.4


class VectorSearchService:
    """Service for vector-based search."""
    
    def __init__(self):
        self._embedding_model = None
        self._vector_store = None
    
    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model
    
    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store
    
    def search(
        self,
        query: str,
        collection: str,
        top_k: int = 10,
        min_score: float = MIN_SIMILARITY_THRESHOLD,
    ) -> tuple[list[RetrievalResult], list[str]]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query
            collection: Vector collection name
            top_k: Maximum results to return
            min_score: Minimum similarity score threshold (0-1)
        
        Returns:
            Tuple of (results, sources)
        """
        results = []
        sources = []
        
        query_embedding = self.embedding_model.embed_single(query)
        vector_results = self.vector_store.search(collection, query_embedding, top_k)
        
        for hit in vector_results:
            score = hit.get("score", 0)
            
            # Filter out low-relevance results
            if score < min_score:
                logger.debug(f"Skipping result with low score: {score:.3f} < {min_score}")
                continue
            
            payload = hit.get("payload", {})
            is_entity = payload.get("is_entity", False)
            item_id = payload.get("entity_id") or payload.get("chunk_id") or hit.get("id")
            
            result = RetrievalResult(
                id=item_id,
                name=payload.get("name", payload.get("document_name", "")),
                type="entity" if is_entity else "chunk",
                score=score,
                text=payload.get("text", payload.get("description", "")),
                is_entity=is_entity,
                properties={
                    k: v for k, v in payload.items()
                    if k not in ("text", "name", "entity_id", "chunk_id")
                },
            )
            results.append(result)
            
            if payload.get("document_name"):
                sources.append(payload["document_name"])
        
        return results, sources


class GraphSearchService:
    """Service for graph-based search."""
    
    def __init__(self):
        self._graph_service = None
        self._llm = None
    
    @property
    def graph_service(self):
        if self._graph_service is None:
            self._graph_service = get_graph_service()
            self._graph_service.connect()
        return self._graph_service
    
    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
    
    def extract_entities_from_query(self, query: str) -> list[str]:
        """Use LLM to extract entity names from the query."""
        extract_prompt = f"""从以下问题中提取所有可能的实体名称（人名、公司名、地名、产品名等）。
只返回实体名称，用逗号分隔，不要其他内容。

问题：{query}

实体名称："""
        
        extracted = self.llm.chat([{"role": "user", "content": extract_prompt}])
        return [name.strip() for name in extracted.split(",") if name.strip()]
    
    def search_entities_by_names(
        self,
        names: list[str],
        space: str,
        limit_per_name: int = 3,
    ) -> list[RetrievalResult]:
        """Search for entities by name in the graph."""
        results = []
        seen_ids = set()
        tags = ["person", "organization", "location", "entity", "concept"]
        
        for name in names[:5]:
            for tag in tags:
                search_query = f'''
                    MATCH (v:{tag}) WHERE v.{tag}.name CONTAINS "{name}"
                    RETURN id(v) AS vid, v.{tag}.name AS name, 
                           v.{tag}.description AS description, "{tag}" AS type
                    LIMIT {limit_per_name}
                '''
                try:
                    result = self.graph_service.execute(search_query, space)
                    if result["success"] and result["data"]:
                        for row in result["data"]:
                            vid = str(row.get("vid", ""))
                            if vid and vid not in seen_ids:
                                seen_ids.add(vid)
                                results.append(RetrievalResult(
                                    id=vid,
                                    name=row.get("name", name),
                                    type="entity",
                                    score=1.0 - (len(results) * 0.05),
                                    text=row.get("description", ""),
                                    is_entity=True,
                                    properties={"entity_type": row.get("type", tag)},
                                ))
                except Exception as e:
                    logger.debug(f"Graph search for {name} in {tag} failed: {e}")
        
        return results
    
    def search(
        self,
        query: str,
        space: str,
    ) -> list[RetrievalResult]:
        """
        Perform graph-based search by extracting entities from query.
        """
        entity_names = self.extract_entities_from_query(query)
        logger.info(f"Graph search: extracted entities: {entity_names}")
        
        results = self.search_entities_by_names(entity_names, space)
        logger.info(f"Graph search: found {len(results)} entities")
        
        return results


class GraphExpansionService:
    """Service for expanding graph context from entities."""
    
    def __init__(self):
        self._graph_service = None
    
    @property
    def graph_service(self):
        if self._graph_service is None:
            self._graph_service = get_graph_service()
            self._graph_service.connect()
        return self._graph_service
    
    def get_entity_name(self, entity_id: str, space: str) -> str:
        """Get entity name from graph by ID."""
        name_query = f'''
            MATCH (n) WHERE id(n) == "{entity_id}"
            RETURN properties(n) AS props, labels(n) AS labels
            LIMIT 1
        '''
        try:
            result = self.graph_service.execute(name_query, space)
            if result["success"] and result["data"]:
                row = result["data"][0]
                props = row.get("props", {}) or {}
                labels = row.get("labels", []) or []
                
                if isinstance(props, dict):
                    for label in labels + ["person", "entity", "organization", "location", "concept"]:
                        key = f"{label}.name"
                        if key in props:
                            return props[key]
                    if "name" in props:
                        return props["name"]
        except Exception as e:
            logger.debug(f"Failed to get name for {entity_id}: {e}")
        
        return entity_id
    
    @staticmethod
    def _extract_name_from_props(props: dict, labels: list, default: str) -> str:
        """Extract name from node properties."""
        if not isinstance(props, dict):
            return default
        
        for label in labels + ["person", "entity", "organization", "location", "concept"]:
            key = f"{label}.name"
            if key in props:
                return props[key]
        
        if "name" in props:
            return props["name"]
        
        return default
    
    # Priority edge types for multi-hop reasoning
    PRIORITY_EDGE_TYPES = [
        "works_for", "located_in", "founded", "belongs_to",
        "related_to", "knows", "uses", "has",
    ]
    
    def expand(
        self,
        entity_ids: list[str],
        space: str,
        max_depth: int = 2,
        id_to_name: dict[str, str] | None = None,
    ) -> GraphContext:
        """
        Expand graph context from a list of entity IDs.
        
        Args:
            entity_ids: List of entity IDs to start expansion from
            space: Graph space name
            max_depth: Maximum depth of expansion
            id_to_name: Optional pre-populated ID to name mapping
        """
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()
        seen_edges: set[str] = set()
        name_map = id_to_name or {}
        pending_expansion: list[tuple[str, int]] = []  # (node_id, depth)
        
        # Fetch names for starting entities
        for eid in entity_ids:
            if eid not in name_map:
                name_map[eid] = self.get_entity_name(eid, space)
        
        def process_node(vid: str, current_depth: int) -> list[str]:
            """Process a node and return neighbor IDs for further expansion."""
            neighbors_to_expand = []
            
            if vid in seen_nodes:
                return neighbors_to_expand
            
            seen_nodes.add(vid)
            
            try:
                # Increase limit to capture more relationships
                match_query = f'''
                    MATCH (n)-[e]-(m) WHERE id(n) == "{vid}"
                    RETURN 
                        id(n) AS src_id,
                        id(m) AS dst_id,
                        type(e) AS edge_type,
                        properties(n) AS src_props,
                        properties(m) AS dst_props,
                        labels(n) AS src_labels,
                        labels(m) AS dst_labels
                    LIMIT 50
                '''
                result = self.graph_service.execute(match_query, space)
                
                if result["success"] and result["data"]:
                    # Sort by priority edge types
                    rows = result["data"]
                    priority_rows = []
                    other_rows = []
                    
                    for row in rows:
                        edge_type = row.get("edge_type", "")
                        if edge_type in self.PRIORITY_EDGE_TYPES:
                            priority_rows.append(row)
                        else:
                            other_rows.append(row)
                    
                    # Process priority edges first
                    sorted_rows = priority_rows + other_rows
                    
                    for row in sorted_rows:
                        src_id = str(row.get("src_id", ""))
                        dst_id = str(row.get("dst_id", ""))
                        edge_type = row.get("edge_type", "")
                        src_props = row.get("src_props", {}) or {}
                        dst_props = row.get("dst_props", {}) or {}
                        src_labels = row.get("src_labels", []) or []
                        dst_labels = row.get("dst_labels", []) or []
                        
                        if not dst_id:
                            continue
                        
                        # Get names
                        src_name = self._extract_name_from_props(src_props, src_labels, src_id)
                        dst_name = self._extract_name_from_props(dst_props, dst_labels, dst_id)
                        neighbor_type = dst_labels[0] if dst_labels else "entity"
                        
                        # Update name mapping
                        if src_id and src_name:
                            name_map[src_id] = src_name
                        if dst_id and dst_name:
                            name_map[dst_id] = dst_name
                        
                        # Add node if not seen
                        if dst_id not in seen_nodes:
                            nodes.append(GraphNode(
                                id=dst_id,
                                name=dst_name,
                                type=neighbor_type,
                                properties=dst_props if isinstance(dst_props, dict) else {},
                            ))
                        
                        # Add edge
                        edge_key = f"{vid}-{edge_type}-{dst_id}"
                        reverse_key = f"{dst_id}-{edge_type}-{vid}"
                        if edge_key not in seen_edges and reverse_key not in seen_edges:
                            seen_edges.add(edge_key)
                            edges.append(GraphEdge(
                                source=vid,
                                source_name=name_map.get(vid, vid),
                                target=dst_id,
                                target_name=dst_name,
                                type=edge_type,
                            ))
                        
                        # Add to expansion list (prioritize important edges)
                        if dst_id not in seen_nodes:
                            if edge_type in self.PRIORITY_EDGE_TYPES:
                                neighbors_to_expand.insert(0, dst_id)
                            else:
                                neighbors_to_expand.append(dst_id)
                
                elif result.get("error"):
                    logger.debug(f"MATCH query error for {vid}: {result['error']}")
            
            except Exception as e:
                logger.warning(f"Failed to expand node {vid} at depth {current_depth}: {e}")
            
            return neighbors_to_expand
        
        # BFS expansion with depth tracking
        for entity_id in entity_ids[:10]:
            pending_expansion.append((entity_id, 1))
        
        while pending_expansion:
            vid, depth = pending_expansion.pop(0)
            
            if depth > max_depth:
                continue
            
            neighbors = process_node(vid, depth)
            
            # Add neighbors for next level expansion
            if depth < max_depth:
                for neighbor_id in neighbors[:15]:  # Limit neighbors per node
                    if neighbor_id not in seen_nodes:
                        pending_expansion.append((neighbor_id, depth + 1))
        
        # Update edge source names
        for edge in edges:
            if edge.source in name_map:
                edge.source_name = name_map[edge.source]
            if edge.target in name_map:
                edge.target_name = name_map[edge.target]
        
        logger.info(f"Graph expansion complete: {len(nodes)} nodes, {len(edges)} edges")
        
        return GraphContext(nodes=nodes, edges=edges)


class AnswerGenerationService:
    """Service for generating answers using LLM."""
    
    def __init__(self):
        self._llm = None
    
    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
    
    def build_context(
        self,
        results: list[RetrievalResult],
        graph_context: GraphContext | None,
    ) -> str:
        """Build context string for LLM prompt."""
        parts = []
        
        # Add retrieved results
        if results:
            parts.append("## Retrieved Information\n")
            for i, item in enumerate(results[:10], 1):
                parts.append(f"### [{i}] {item.name} ({item.type}, relevance: {item.score:.2f})")
                if item.text:
                    parts.append(f"{item.text}\n")
        
        # Add graph context
        if graph_context:
            # Build name lookup
            node_names = {n.id: n.name for n in graph_context.nodes}
            
            if graph_context.nodes:
                parts.append("\n## Related Entities (Knowledge Graph)\n")
                for node in graph_context.nodes[:20]:
                    desc = node.properties.get("description", "")
                    if desc:
                        parts.append(f"- **{node.name}** ({node.type}): {desc}")
                    else:
                        parts.append(f"- **{node.name}** ({node.type})")
            
            if graph_context.edges:
                parts.append("\n## Relationships (Knowledge Graph)\n")
                parts.append("These relationships show how entities are connected:\n")
                
                # Sort edges to prioritize important relationship types
                priority_types = {"works_for", "located_in", "founded", "belongs_to", "related_to"}
                priority_edges = [e for e in graph_context.edges if e.type in priority_types]
                other_edges = [e for e in graph_context.edges if e.type not in priority_types]
                sorted_edges = priority_edges + other_edges
                
                for edge in sorted_edges[:40]:  # Increased limit
                    src = edge.source_name or node_names.get(edge.source, edge.source)
                    tgt = edge.target_name or node_names.get(edge.target, edge.target)
                    edge_label = edge.type.replace("_", " ")
                    parts.append(f"- {src} --[{edge_label}]--> {tgt}")
        
        return "\n".join(parts)
    
    def _build_messages(
        self,
        query: str,
        results: list[RetrievalResult],
        graph_context: GraphContext | None,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build messages for LLM prompt with optional chat history."""
        context = self.build_context(results, graph_context)
        messages: list[dict[str, str]] = []
        
        # System message
        if not context.strip():
            messages.append({
                "role": "system",
                "content": "你是一个知识图谱问答助手。当知识库中没有相关信息时，请基于你的通用知识回答问题，并说明这是基于通用知识而非知识库的回答。请用中文回答。",
            })
        else:
            messages.append({
                "role": "system",
                "content": "你是一个知识图谱问答助手，基于知识图谱中的信息回答问题。请用中文回答。",
            })
        
        # Add chat history for context
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        
        # Build current user message
        if not context.strip():
            messages.append({"role": "user", "content": query})
        else:
            prompt = f"""基于以下知识图谱中的上下文信息，请回答用户的问题。

# 上下文
{context}

# 问题
{query}

# 回答要求
1. 优先基于提供的上下文回答
2. 如果上下文信息不足，可以结合通用知识补充说明
3. 引用相关的实体和关系
4. 回答要简洁但全面

# 回答:"""
            messages.append({"role": "user", "content": prompt})
        
        return messages

    def generate_answer(
        self,
        query: str,
        results: list[RetrievalResult],
        graph_context: GraphContext | None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate answer using LLM based on context."""
        messages = self._build_messages(query, results, graph_context, history)
        return self.llm.chat(messages)
    
    def generate_answer_stream(
        self,
        query: str,
        results: list[RetrievalResult],
        graph_context: GraphContext | None,
        history: list[dict[str, str]] | None = None,
    ):
        """Generate streaming answer using LLM based on context."""
        messages = self._build_messages(query, results, graph_context, history)
        return self.llm.chat_stream(messages)


class RetrievalService:
    """
    Main retrieval service that orchestrates vector search, graph search,
    and answer generation.
    """
    
    # Minimum average score to trigger graph expansion
    MIN_AVG_SCORE_FOR_GRAPH = 0.5
    
    def __init__(self):
        self.vector_search = VectorSearchService()
        self.graph_search = GraphSearchService()
        self.graph_expansion = GraphExpansionService()
        self.answer_generation = AnswerGenerationService()
    
    def retrieve(
        self,
        query: str,
        search_type: str = "hybrid",
        collection: str | None = None,
        space: str | None = None,
        top_k: int = 10,
        expand_graph: bool = True,
        graph_depth: int = 2,
        use_llm: bool = False,
    ) -> RetrievalResponse:
        """
        Perform retrieval using specified strategy.
        
        Args:
            query: User query
            search_type: "hybrid", "vector", or "graph"
            collection: Vector collection name
            space: Graph space name
            top_k: Number of results to return
            expand_graph: Whether to expand graph context
            graph_depth: Depth of graph expansion
            use_llm: Whether to generate answer using LLM
        """
        settings = get_settings()
        collection = collection or settings.vector_store.qdrant_collection
        space = space or settings.nebula.space
        
        total_start = time.perf_counter()
        timing = TimingInfo()
        
        response = RetrievalResponse(
            success=True,
            query=query,
        )
        
        # Step 1: Search
        if search_type in ("hybrid", "vector"):
            try:
                start = time.perf_counter()
                results, sources = self.vector_search.search(query, collection, top_k)
                timing.vector_search_ms = (time.perf_counter() - start) * 1000
                response.results.extend(results)
                response.sources.extend(sources)
                logger.info(f"Vector search returned {len(results)} results above threshold")
            except Exception as e:
                response.errors.append(f"Vector search error: {e}")
                logger.error(f"Vector search failed: {e}")
        
        if search_type == "graph":
            try:
                start = time.perf_counter()
                results = self.graph_search.search(query, space)
                timing.graph_search_ms = (time.perf_counter() - start) * 1000
                response.results.extend(results)
                expand_graph = True  # Force graph expansion for graph mode
            except Exception as e:
                response.errors.append(f"Graph search error: {e}")
                logger.error(f"Graph search failed: {e}")
        
        # Step 2: Graph expansion (with quality check)
        should_expand_graph = expand_graph and self._should_expand_graph(response.results, search_type)
        
        if should_expand_graph:
            try:
                start = time.perf_counter()
                # Collect entity IDs
                entity_ids = []
                id_to_name = {}
                
                for r in response.results:
                    if r.is_entity or r.id.startswith("e_"):
                        entity_ids.append(r.id)
                        if r.name:
                            id_to_name[r.id] = r.name
                
                # If no entities found, try to find from chunks
                if len(entity_ids) < 3:
                    chunk_ids = [r.id for r in response.results if r.id.startswith("chunk_")]
                    entity_ids.extend(
                        self._find_entities_from_chunks(chunk_ids, space)
                    )
                
                # If still no entities, try name-based search
                if not entity_ids:
                    for r in response.results[:5]:
                        if r.name and not r.name.endswith(".txt"):
                            found = self._find_entities_by_name(r.name, space)
                            entity_ids.extend(found)
                
                if entity_ids:
                    response.graph_context = self.graph_expansion.expand(
                        entity_ids, space, graph_depth, id_to_name
                    )
                timing.graph_expansion_ms = (time.perf_counter() - start) * 1000
            
            except Exception as e:
                response.errors.append(f"Graph expansion error: {e}")
                logger.error(f"Graph expansion failed: {e}")
        else:
            logger.info(f"Skipping graph expansion: expand_graph={expand_graph}, results_quality_check={self._should_expand_graph(response.results, search_type) if response.results else False}")
        
        # Step 3: Answer generation
        if use_llm and (response.results or response.graph_context):
            try:
                start = time.perf_counter()
                response.answer = self.answer_generation.generate_answer(
                    query, response.results, response.graph_context
                )
                timing.llm_ms = (time.perf_counter() - start) * 1000
            except Exception as e:
                response.errors.append(f"LLM error: {e}")
                logger.error(f"Answer generation failed: {e}")
        
        timing.total_ms = (time.perf_counter() - total_start) * 1000
        response.timing = timing
        
        response.success = len(response.errors) == 0 or len(response.results) > 0
        return response
    
    def _should_expand_graph(self, results: list[RetrievalResult], search_type: str) -> bool:
        """
        Determine if graph expansion should be performed based on result quality.
        
        Args:
            results: Vector search results
            search_type: Type of search being performed
        
        Returns:
            True if graph expansion should proceed
        """
        # Always expand for explicit graph search
        if search_type == "graph":
            return True
        
        # No results, no expansion
        if not results:
            return False
        
        # Check if we have high-quality results
        # Calculate average score of top results
        top_scores = [r.score for r in results[:5]]
        if not top_scores:
            return False
        
        avg_score = sum(top_scores) / len(top_scores)
        max_score = max(top_scores)
        
        # Require either a high max score or decent average
        if max_score >= 0.6 or avg_score >= self.MIN_AVG_SCORE_FOR_GRAPH:
            logger.info(f"Graph expansion approved: max_score={max_score:.3f}, avg_score={avg_score:.3f}")
            return True
        
        logger.info(f"Graph expansion skipped: max_score={max_score:.3f}, avg_score={avg_score:.3f} (threshold: {self.MIN_AVG_SCORE_FOR_GRAPH})")
        return False
    
    def _find_entities_from_chunks(self, chunk_ids: list[str], space: str) -> list[str]:
        """Find entities extracted from chunks."""
        entity_ids = []
        graph_service = self.graph_expansion.graph_service
        
        for chunk_id in chunk_ids[:5]:
            query = f'''
                GO FROM "{chunk_id}" OVER extracted_from REVERSELY
                YIELD dst(edge) AS entity_id | LIMIT 10
            '''
            try:
                result = graph_service.execute(query, space)
                if result["success"] and result["data"]:
                    for row in result["data"]:
                        eid = row.get("entity_id")
                        if eid and str(eid) not in entity_ids:
                            entity_ids.append(str(eid))
            except Exception as e:
                logger.debug(f"Chunk->entity lookup failed: {e}")
        
        return entity_ids
    
    def _find_entities_by_name(self, name: str, space: str) -> list[str]:
        """Find entities by name in graph."""
        entity_ids = []
        graph_service = self.graph_expansion.graph_service
        
        query = f'''
            MATCH (v) WHERE v.person.name == "{name}" 
                OR v.entity.name == "{name}" 
                OR v.organization.name == "{name}"
            RETURN id(v) as vid LIMIT 5
        '''
        try:
            result = graph_service.execute(query, space)
            if result["success"] and result["data"]:
                for row in result["data"]:
                    vid = row.get("vid")
                    if vid:
                        entity_ids.append(str(vid))
        except Exception as e:
            logger.debug(f"MATCH by name failed: {e}")
        
        return entity_ids


# Singleton instance
_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    """Get singleton retrieval service instance."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
