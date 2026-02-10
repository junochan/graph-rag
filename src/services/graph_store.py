"""
NebulaGraph service for graph database operations.
"""

from typing import Any

from nebula3.Config import Config as NebulaConfig
from nebula3.gclient.net import ConnectionPool

from src.config import get_settings


class NebulaGraphService:
    """NebulaGraph database service."""

    def __init__(
        self,
        hosts: list[str] | None = None,
        username: str = "root",
        password: str = "nebula",
        space: str = "graph_rag",
        max_connection_pool_size: int = 10,
    ):
        self.hosts = hosts or ["127.0.0.1:9669"]
        self.username = username
        self.password = password
        self.space = space
        self.max_connection_pool_size = max_connection_pool_size

        self._pool: ConnectionPool | None = None
        self._initialized = False

    def _parse_hosts(self) -> list[tuple[str, int]]:
        """Parse host strings to (host, port) tuples."""
        result = []
        for host_str in self.hosts:
            if ":" in host_str:
                host, port = host_str.split(":")
                result.append((host, int(port)))
            else:
                result.append((host_str, 9669))
        return result

    def connect(self) -> None:
        """Initialize connection pool."""
        if self._initialized:
            return

        config = NebulaConfig()
        config.max_connection_pool_size = self.max_connection_pool_size

        self._pool = ConnectionPool()
        hosts = self._parse_hosts()

        if not self._pool.init(hosts, config):
            raise ConnectionError(f"Failed to connect to NebulaGraph at {hosts}")

        self._initialized = True

    def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            self._pool.close()
            self._pool = None
            self._initialized = False

    def _get_session(self):
        """Get a session from the pool."""
        if not self._initialized:
            self.connect()
        return self._pool.get_session(self.username, self.password)

    def execute(self, query: str, space: str | None = None) -> dict[str, Any]:
        """Execute a nGQL query."""
        session = self._get_session()
        try:
            # Use specified space or default
            use_space = space or self.space
            if use_space:
                session.execute(f"USE {use_space}")

            result = session.execute(query)

            if not result.is_succeeded():
                return {
                    "success": False,
                    "error": result.error_msg(),
                    "data": None,
                }

            # Parse result
            data = []
            if result.row_size() > 0:
                columns = result.keys()
                for row_idx in range(result.row_size()):
                    row_data = {}
                    for col_idx, col_name in enumerate(columns):
                        value = result.row_values(row_idx)[col_idx]
                        row_data[col_name] = self._parse_value(value)
                    data.append(row_data)

            return {
                "success": True,
                "error": None,
                "data": data,
            }
        finally:
            session.release()

    def _parse_value(self, value) -> Any:
        """Parse NebulaGraph value to Python type."""
        if value.is_null():
            return None
        elif value.is_bool():
            return value.as_bool()
        elif value.is_int():
            return value.as_int()
        elif value.is_double():
            return value.as_double()
        elif value.is_string():
            return value.as_string()
        elif value.is_list():
            return [self._parse_value(v) for v in value.as_list()]
        elif value.is_map():
            return {k: self._parse_value(v) for k, v in value.as_map().items()}
        elif value.is_vertex():
            vertex = value.as_node()
            return {
                "type": "vertex",
                "vid": vertex.get_id().as_string() if vertex.get_id().is_string() else str(vertex.get_id().as_int()),
                "tags": list(vertex.tags()),
                "properties": {
                    tag: dict(vertex.properties(tag)) for tag in vertex.tags()
                },
            }
        elif value.is_edge():
            edge = value.as_relationship()
            return {
                "type": "edge",
                "src": str(edge.start_vertex_id()),
                "dst": str(edge.end_vertex_id()),
                "edge_type": edge.edge_name(),
                "rank": edge.ranking(),
                "properties": dict(edge.properties()),
            }
        elif value.is_path():
            path = value.as_path()
            return {
                "type": "path",
                "nodes": [self._parse_value(n) for n in path.nodes()],
            }
        else:
            return str(value)

    def create_space_if_not_exists(
        self,
        space_name: str | None = None,
        partition_num: int = 10,
        replica_factor: int = 1,
        vid_type: str = "FIXED_STRING(256)",
    ) -> dict[str, Any]:
        """Create a graph space if it doesn't exist."""
        space = space_name or self.space
        query = f"""
        CREATE SPACE IF NOT EXISTS {space} (
            partition_num = {partition_num},
            replica_factor = {replica_factor},
            vid_type = {vid_type}
        )
        """
        return self.execute(query, space=None)

    def create_tag(
        self,
        tag_name: str,
        properties: dict[str, str],
        space: str | None = None,
    ) -> dict[str, Any]:
        """Create a tag (vertex type) with properties."""
        props_str = ", ".join([f"{k} {v}" for k, v in properties.items()])
        query = f"CREATE TAG IF NOT EXISTS {tag_name}({props_str})"
        return self.execute(query, space)

    def create_edge_type(
        self,
        edge_name: str,
        properties: dict[str, str] | None = None,
        space: str | None = None,
    ) -> dict[str, Any]:
        """Create an edge type with optional properties."""
        if properties:
            props_str = ", ".join([f"{k} {v}" for k, v in properties.items()])
            query = f"CREATE EDGE IF NOT EXISTS {edge_name}({props_str})"
        else:
            query = f"CREATE EDGE IF NOT EXISTS {edge_name}()"
        return self.execute(query, space)

    def insert_vertex(
        self,
        tag_name: str,
        vid: str,
        properties: dict[str, Any],
        space: str | None = None,
    ) -> dict[str, Any]:
        """Insert a vertex."""
        prop_names = ", ".join(properties.keys())
        prop_values = ", ".join([self._format_value(v) for v in properties.values()])
        query = f'INSERT VERTEX {tag_name}({prop_names}) VALUES "{vid}":({prop_values})'
        return self.execute(query, space)

    def insert_edge(
        self,
        edge_type: str,
        src_vid: str,
        dst_vid: str,
        properties: dict[str, Any] | None = None,
        rank: int = 0,
        space: str | None = None,
    ) -> dict[str, Any]:
        """Insert an edge."""
        if properties:
            prop_names = ", ".join(properties.keys())
            prop_values = ", ".join([self._format_value(v) for v in properties.values()])
            query = f'INSERT EDGE {edge_type}({prop_names}) VALUES "{src_vid}"->"{dst_vid}"@{rank}:({prop_values})'
        else:
            query = f'INSERT EDGE {edge_type}() VALUES "{src_vid}"->"{dst_vid}"@{rank}:()'
        return self.execute(query, space)

    def _format_value(self, value: Any) -> str:
        """Format Python value for nGQL query."""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Escape quotes in string
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(value, list):
            items = ", ".join([self._format_value(v) for v in value])
            return f"[{items}]"
        else:
            return f'"{str(value)}"'

    def get_neighbors(
        self,
        vid: str,
        edge_types: list[str] | None = None,
        direction: str = "BOTH",
        limit: int = 100,
        space: str | None = None,
    ) -> dict[str, Any]:
        """Get neighboring vertices."""
        edge_clause = ""
        if edge_types:
            edge_clause = ", ".join(edge_types)

        query = f"""
        GO FROM "{vid}" OVER {edge_clause or "*"} {direction}
        YIELD properties($$) AS props, type(edge) AS edge_type, dst(edge) AS neighbor_id
        LIMIT {limit}
        """
        return self.execute(query, space)

    def find_path(
        self,
        src_vid: str,
        dst_vid: str,
        edge_types: list[str] | None = None,
        max_depth: int = 5,
        space: str | None = None,
    ) -> dict[str, Any]:
        """Find shortest path between two vertices."""
        edge_clause = ", ".join(edge_types) if edge_types else "*"
        query = f"""
        FIND SHORTEST PATH FROM "{src_vid}" TO "{dst_vid}"
        OVER {edge_clause} YIELD path AS p
        """
        return self.execute(query, space)

    def match_pattern(
        self,
        pattern: str,
        where_clause: str | None = None,
        return_clause: str = "*",
        limit: int = 100,
        space: str | None = None,
    ) -> dict[str, Any]:
        """Execute a MATCH query with given pattern."""
        query = f"MATCH {pattern}"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" RETURN {return_clause} LIMIT {limit}"
        return self.execute(query, space)


def get_graph_service() -> NebulaGraphService:
    """Factory function to get configured NebulaGraph service."""
    settings = get_settings()
    nebula_config = settings.nebula

    return NebulaGraphService(
        hosts=nebula_config.hosts,
        username=nebula_config.username,
        password=nebula_config.password,
        space=nebula_config.space,
        max_connection_pool_size=nebula_config.max_connection_pool_size,
    )
