"use client";

import { useState, useCallback, useEffect } from "react";
import { Search, RefreshCw, Filter, ZoomIn } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
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
          graph_depth: 3,
          use_llm: false,
        });

        if (response.graph_context) {
          setNodes(response.graph_context.nodes);
          setEdges(response.graph_context.edges);
          setStats({
            nodes: response.graph_context.nodes.length,
            edges: response.graph_context.edges.length,
          });
        }
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
  }, []);

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

  // Filter nodes by type
  const filteredNodes = nodes.filter((node) =>
    selectedTypes.includes(node.type.toLowerCase())
  );

  // Filter edges to only include those connecting visible nodes
  const filteredEdges = edges.filter(
    (edge) =>
      filteredNodes.some((n) => n.id === edge.source) &&
      filteredNodes.some((n) => n.id === edge.target)
  );

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
