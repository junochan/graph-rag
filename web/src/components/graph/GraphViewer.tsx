"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Handle,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  ConnectionMode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphNode as ApiGraphNode, GraphEdge as ApiGraphEdge } from "@/lib/types";
import { cn } from "@/lib/utils";

interface GraphViewerProps {
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
  onNodeClick?: (node: ApiGraphNode) => void;
}

// Node type color mapping
const NODE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  person: {
    bg: "rgb(59, 130, 246)",  // blue-500
    border: "rgb(37, 99, 235)", // blue-600
    text: "white",
  },
  organization: {
    bg: "rgb(34, 197, 94)",   // green-500
    border: "rgb(22, 163, 74)", // green-600
    text: "white",
  },
  location: {
    bg: "rgb(249, 115, 22)",  // orange-500
    border: "rgb(234, 88, 12)", // orange-600
    text: "white",
  },
  concept: {
    bg: "rgb(168, 85, 247)",  // purple-500
    border: "rgb(147, 51, 234)", // purple-600
    text: "white",
  },
  technology: {
    bg: "rgb(6, 182, 212)",   // cyan-500
    border: "rgb(8, 145, 178)", // cyan-600
    text: "white",
  },
  product: {
    bg: "rgb(236, 72, 153)",  // pink-500
    border: "rgb(219, 39, 119)", // pink-600
    text: "white",
  },
  event: {
    bg: "rgb(245, 158, 11)",  // amber-500
    border: "rgb(217, 119, 6)", // amber-600
    text: "white",
  },
  entity: {
    bg: "rgb(107, 114, 128)", // gray-500
    border: "rgb(75, 85, 99)",  // gray-600
    text: "white",
  },
};

function getNodeColor(type: string) {
  return NODE_COLORS[type.toLowerCase()] || NODE_COLORS.entity;
}

// Custom node component - must include Handle for edges to connect
function CustomNode({ data }: { data: { label: string; type: string; isSelected: boolean } }) {
  const colors = getNodeColor(data.type);
  
  return (
    <div
      className={cn(
        "px-4 py-2 rounded-lg shadow-md transition-all cursor-pointer relative",
        "border-2 min-w-[80px] text-center",
        data.isSelected && "ring-2 ring-primary ring-offset-2"
      )}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-gray-400" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-gray-400" />
      <div className="text-xs opacity-75 mb-0.5">{data.type}</div>
      <div className="font-medium text-sm truncate max-w-[120px]">
        {data.label}
      </div>
    </div>
  );
}

const nodeTypes = {
  custom: CustomNode,
};

export function GraphViewer({ nodes, edges, onNodeClick }: GraphViewerProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Deduplicate nodes by ID
  const uniqueNodes = useMemo(() => {
    const seen = new Map<string, ApiGraphNode>();
    for (const node of nodes) {
      if (!seen.has(node.id)) {
        seen.set(node.id, node);
      }
    }
    return Array.from(seen.values());
  }, [nodes]);

  // Convert API nodes to React Flow nodes
  const flowNodes = useMemo(() => {
    const nodeCount = uniqueNodes.length;
    const radius = Math.max(200, nodeCount * 30);
    
    return uniqueNodes.map((node, index): Node => {
      // Arrange nodes in a circle
      const angle = (2 * Math.PI * index) / nodeCount;
      const x = radius * Math.cos(angle) + radius;
      const y = radius * Math.sin(angle) + radius;

      return {
        id: node.id,
        type: "custom",
        position: { x, y },
        data: {
          label: node.name,
          type: node.type,
          isSelected: node.id === selectedNodeId,
          originalData: node,
        },
      };
    });
  }, [uniqueNodes, selectedNodeId]);

  // Convert API edges to React Flow edges (deduplicated)
  const flowEdges = useMemo(() => {
    const seen = new Set<string>();
    const uniqueEdges: Edge[] = [];
    
    for (const edge of edges) {
      const edgeKey = `${edge.source}-${edge.type}-${edge.target}`;
      if (seen.has(edgeKey)) continue;
      seen.add(edgeKey);
      
      uniqueEdges.push({
        id: edgeKey,
        source: edge.source,
        target: edge.target,
        label: edge.type.replace(/_/g, " "),
        type: "smoothstep",
        animated: true,
        style: { stroke: "rgb(156, 163, 175)" },
        labelStyle: { fontSize: 10, fill: "rgb(107, 114, 128)" },
        labelBgStyle: { fill: "white", fillOpacity: 0.8 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "rgb(156, 163, 175)",
        },
      });
    }
    
    return uniqueEdges;
  }, [edges]);

  const [reactFlowNodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [reactFlowEdges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Update nodes when data changes
  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  // Handle node click
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
      const originalNode = nodes.find((n) => n.id === node.id);
      if (originalNode && onNodeClick) {
        onNodeClick(originalNode);
      }
    },
    [nodes, onNodeClick]
  );

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        暂无图谱数据
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={reactFlowNodes}
        edges={reactFlowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
      >
        <Controls />
        <Background />
        <MiniMap
          nodeColor={(node) => {
            const type = (node.data?.type as string) || "entity";
            return getNodeColor(type).bg;
          }}
          maskColor="rgb(0, 0, 0, 0.1)"
        />
      </ReactFlow>
    </div>
  );
}
