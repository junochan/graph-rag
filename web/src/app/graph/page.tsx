"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { Search, RefreshCw, Filter, ZoomIn, GitBranch } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { GraphViewer } from "@/components/graph/GraphViewer";
import { NodeDetail } from "@/components/graph/NodeDetail";
import { getGraphData, retrieve } from "@/lib/api";
import type { GraphNode, GraphEdge } from "@/lib/types";

const ENTITY_TYPES = [
  { value: "person", label: "人物", color: "bg-blue-500" },
  { value: "organization", label: "组织", color: "bg-green-500" },
  { value: "location", label: "地点", color: "bg-orange-500" },
  { value: "concept", label: "概念", color: "bg-purple-500" },
  { value: "technology", label: "技术", color: "bg-cyan-500" },
  { value: "product", label: "产品", color: "bg-pink-500" },
  { value: "event", label: "事件", color: "bg-amber-500" },
  { value: "entity", label: "实体", color: "bg-gray-500" },
];

export default function GraphPage() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>(
    ENTITY_TYPES.map((t) => t.value)
  );
  const [graphDepth, setGraphDepth] = useState(1);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });

  // Load initial data
  const loadGraphData = useCallback(async (query?: string) => {
    setIsLoading(true);
    try {
      if (query) {
        // Search with query to get graph context
        const response = await retrieve({
          query,
          search_type: "graph",
          expand_graph: true,
          graph_depth: graphDepth,
          use_llm: false,
        });

        // Merge: results contain the matched entities themselves (e.g. "张三"),
        // while graph_context only contains their *neighbours* from expansion.
        // We need both to show the full subgraph.
        const contextNodes = response.graph_context?.nodes ?? [];
        const contextEdges = response.graph_context?.edges ?? [];

        // Convert matched results into graph nodes (deduplicated by id)
        const seenIds = new Set(contextNodes.map((n) => n.id));
        const resultNodes: GraphNode[] = response.results
          .filter((r) => r.is_entity && !seenIds.has(r.id))
          .map((r) => ({
            id: r.id,
            name: r.name,
            type: r.properties?.entity_type as string || r.type,
            properties: r.properties,
          }));

        const allNodes = [...resultNodes, ...contextNodes];
        setNodes(allNodes);
        setEdges(contextEdges);
        setStats({
          nodes: allNodes.length,
          edges: contextEdges.length,
        });
      } else {
        // Load full graph data including nodes and edges
        const graphResponse = await getGraphData({ limit: 100 });
        
        if (graphResponse.success) {
          setNodes(graphResponse.nodes);
          setEdges(graphResponse.edges);
          setStats({
            nodes: graphResponse.stats.total_nodes,
            edges: graphResponse.stats.total_edges,
          });
        }
      }
    } catch (error) {
      console.error("Failed to load graph data:", error);
    } finally {
      setIsLoading(false);
    }
  }, [graphDepth]);

  // Initial load
  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  // Handle search
  const handleSearch = useCallback(() => {
    if (searchQuery.trim()) {
      loadGraphData(searchQuery.trim());
    }
  }, [searchQuery, loadGraphData]);

  // Handle key press
  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        handleSearch();
      }
    },
    [handleSearch]
  );

  // Filter nodes by type (memoized to avoid re-filtering on every render)
  const filteredNodes = useMemo(
    () => nodes.filter((node) => selectedTypes.includes(node.type.toLowerCase())),
    [nodes, selectedTypes],
  );

  // Filter edges to only include those connecting visible nodes
  const filteredEdges = useMemo(() => {
    const visibleIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));
  }, [edges, filteredNodes]);

  // Toggle type filter
  const toggleType = useCallback((type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type)
        ? prev.filter((t) => t !== type)
        : [...prev, type]
    );
  }, []);

  return (
    <div className="h-full flex">
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h1 className="text-xl font-semibold">知识图谱</h1>
            <p className="text-sm text-muted-foreground">
              {stats.nodes} 个节点 · {stats.edges} 条关系
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Search */}
            <div className="flex items-center gap-2">
              <Input
                placeholder="搜索实体..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyPress}
                className="w-64"
              />
              <Button onClick={handleSearch} disabled={isLoading}>
                <Search className="h-4 w-4" />
              </Button>
            </div>

            {/* Graph Depth */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <GitBranch className="h-4 w-4 mr-2" />
                  {graphDepth} 跳
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>图扩展深度</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuRadioGroup
                  value={graphDepth.toString()}
                  onValueChange={(v) => setGraphDepth(parseInt(v))}
                >
                  <DropdownMenuRadioItem value="1">1 跳 (直接关联)</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="2">2 跳</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="3">3 跳</DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Type Filter */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <Filter className="h-4 w-4 mr-2" />
                  筛选
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>实体类型</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {ENTITY_TYPES.map((type) => (
                  <DropdownMenuCheckboxItem
                    key={type.value}
                    checked={selectedTypes.includes(type.value)}
                    onCheckedChange={() => toggleType(type.value)}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${type.color} mr-2`}
                    />
                    {type.label}
                  </DropdownMenuCheckboxItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Refresh */}
            <Button
              variant="outline"
              onClick={() => loadGraphData()}
              disabled={isLoading}
            >
              <RefreshCw
                className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
              />
            </Button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 px-4 py-2 border-b bg-muted/30">
          <span className="text-xs text-muted-foreground">图例:</span>
          {ENTITY_TYPES.map((type) => (
            <div key={type.value} className="flex items-center gap-1">
              <span className={`w-3 h-3 rounded ${type.color}`} />
              <span className="text-xs">{type.label}</span>
            </div>
          ))}
        </div>

        {/* Graph Viewer */}
        <div className="flex-1 relative">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <ZoomIn className="h-12 w-12 mb-4 opacity-50" />
              <p>暂无图谱数据</p>
              <p className="text-sm">尝试搜索实体或上传文档构建知识图谱</p>
            </div>
          ) : (
            <GraphViewer
              nodes={filteredNodes}
              edges={filteredEdges}
              onNodeClick={setSelectedNode}
            />
          )}
        </div>
      </div>

      {/* Node Detail Sidebar */}
      {selectedNode && (
        <div className="w-80">
          <NodeDetail
            node={selectedNode}
            edges={edges}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      )}
    </div>
  );
}
