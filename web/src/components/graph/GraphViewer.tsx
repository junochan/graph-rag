"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Handle,
  Controls,
  Background,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  MarkerType,
  Position,
  ConnectionMode,
  getNodesBounds,
  getViewportForBounds,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { toPng } from "html-to-image";
import { Download, Loader2 } from "lucide-react";
import type { GraphNode as ApiGraphNode, GraphEdge as ApiGraphEdge } from "@/lib/types";
import { cn } from "@/lib/utils";

interface GraphViewerProps {
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
  onNodeClick?: (node: ApiGraphNode) => void;
}

// ============================================================================
// Node Colors
// ============================================================================

const NODE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  person:       { bg: "rgb(59, 130, 246)",  border: "rgb(37, 99, 235)",  text: "white" },
  organization: { bg: "rgb(34, 197, 94)",   border: "rgb(22, 163, 74)",  text: "white" },
  location:     { bg: "rgb(249, 115, 22)",  border: "rgb(234, 88, 12)",  text: "white" },
  concept:      { bg: "rgb(168, 85, 247)",  border: "rgb(147, 51, 234)", text: "white" },
  technology:   { bg: "rgb(6, 182, 212)",   border: "rgb(8, 145, 178)",  text: "white" },
  product:      { bg: "rgb(236, 72, 153)",  border: "rgb(219, 39, 119)", text: "white" },
  event:        { bg: "rgb(245, 158, 11)",  border: "rgb(217, 119, 6)",  text: "white" },
  entity:       { bg: "rgb(107, 114, 128)", border: "rgb(75, 85, 99)",   text: "white" },
};

function getNodeColor(type: string) {
  return NODE_COLORS[type.toLowerCase()] || NODE_COLORS.entity;
}

// ============================================================================
// Dark Mode Detection
// ============================================================================

function subscribeToTheme(callback: () => void) {
  const observer = new MutationObserver(callback);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
  return () => observer.disconnect();
}

function getIsDark() {
  return typeof document !== "undefined" && document.documentElement.classList.contains("dark");
}

function useIsDark() {
  return useSyncExternalStore(subscribeToTheme, getIsDark, () => false);
}

// ============================================================================
// Force-directed Layout
// ============================================================================

interface Vec2 { x: number; y: number; }

/**
 * Simple force-directed layout computed synchronously.
 * Produces stable positions without needing an animation loop.
 */
function forceLayout(
  nodeIds: string[],
  edgePairs: { source: string; target: string }[],
  iterations = 120,
): Map<string, Vec2> {
  const n = nodeIds.length;
  if (n === 0) return new Map();

  // Initialise positions in a grid so the starting state is already spread out
  const cols = Math.max(1, Math.ceil(Math.sqrt(n)));
  const spacing = 200;
  const positions = new Map<string, Vec2>();
  nodeIds.forEach((id, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    positions.set(id, { x: col * spacing, y: row * spacing });
  });

  if (n === 1) return positions;

  // Build adjacency index for fast edge lookup
  const idIndex = new Map<string, number>();
  nodeIds.forEach((id, i) => idIndex.set(id, i));

  const edgeIndices = edgePairs
    .map((e) => [idIndex.get(e.source), idIndex.get(e.target)] as const)
    .filter((pair): pair is [number, number] => pair[0] !== undefined && pair[1] !== undefined);

  // Simulation parameters
  const repulsionStrength = 8000;
  const attractionStrength = 0.005;
  const idealLength = 180;
  const damping = 0.9;
  const maxDisplacement = 50;

  const vx = new Float64Array(n);
  const vy = new Float64Array(n);
  const px = new Float64Array(n);
  const py = new Float64Array(n);

  // Copy initial positions to typed arrays
  nodeIds.forEach((id, i) => {
    const p = positions.get(id)!;
    px[i] = p.x;
    py[i] = p.y;
  });

  for (let iter = 0; iter < iterations; iter++) {
    const temperature = 1 - iter / iterations; // cool down

    // Repulsive forces (all pairs)
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let dx = px[j] - px[i];
        let dy = py[j] - py[i];
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsionStrength / (dist * dist);
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        vx[i] -= dx;
        vy[i] -= dy;
        vx[j] += dx;
        vy[j] += dy;
      }
    }

    // Attractive forces (edges)
    for (const [si, ti] of edgeIndices) {
      let dx = px[ti] - px[si];
      let dy = py[ti] - py[si];
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = attractionStrength * (dist - idealLength);
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      vx[si] += dx;
      vy[si] += dy;
      vx[ti] -= dx;
      vy[ti] -= dy;
    }

    // Apply velocities with damping & temperature
    const cap = maxDisplacement * temperature;
    for (let i = 0; i < n; i++) {
      vx[i] *= damping;
      vy[i] *= damping;
      const len = Math.sqrt(vx[i] * vx[i] + vy[i] * vy[i]) || 1;
      if (len > cap) {
        vx[i] = (vx[i] / len) * cap;
        vy[i] = (vy[i] / len) * cap;
      }
      px[i] += vx[i];
      py[i] += vy[i];
    }
  }

  // Write back
  nodeIds.forEach((id, i) => {
    positions.set(id, { x: Math.round(px[i]), y: Math.round(py[i]) });
  });

  return positions;
}

// ============================================================================
// Custom Node
// ============================================================================

function CustomNode({ data }: { data: { label: string; type: string; isSelected: boolean } }) {
  const colors = getNodeColor(data.type);

  return (
    <div
      className={cn(
        "px-4 py-2 rounded-lg shadow-md transition-shadow cursor-pointer relative",
        "border-2 min-w-[80px] text-center",
        data.isSelected && "ring-2 ring-primary ring-offset-2 dark:ring-offset-slate-900",
      )}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-gray-400 dark:!bg-gray-500" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-gray-400 dark:!bg-gray-500" />
      <div className="text-xs opacity-75 mb-0.5">{data.type}</div>
      <div className="font-medium text-sm truncate max-w-[120px]">{data.label}</div>
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

// ============================================================================
// Inner Graph (needs ReactFlowProvider context)
// ============================================================================

function GraphViewerInner({ nodes, edges, onNodeClick }: GraphViewerProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const { fitView } = useReactFlow();
  const isDark = useIsDark();

  // Keep a ref so we can update selected styling without recalculating layout
  const selectedRef = useRef<string | null>(null);

  // --- Deduplicate nodes ---
  const uniqueNodes = useMemo(() => {
    const seen = new Map<string, ApiGraphNode>();
    for (const node of nodes) {
      if (!seen.has(node.id)) seen.set(node.id, node);
    }
    return Array.from(seen.values());
  }, [nodes]);

  // --- Deduplicate edges ---
  const uniqueEdges = useMemo(() => {
    const seen = new Set<string>();
    const result: ApiGraphEdge[] = [];
    for (const edge of edges) {
      const key = `${edge.source}-${edge.type}-${edge.target}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(edge);
      }
    }
    return result;
  }, [edges]);

  // --- Compute layout only when graph data changes (NOT on selection) ---
  const layoutPositions = useMemo(
    () =>
      forceLayout(
        uniqueNodes.map((n) => n.id),
        uniqueEdges.map((e) => ({ source: e.source, target: e.target })),
      ),
    [uniqueNodes, uniqueEdges],
  );

  // --- Build React Flow nodes (layout-dependent, NOT selection-dependent) ---
  const flowNodes = useMemo(
    (): Node[] =>
      uniqueNodes.map((node) => {
        const pos = layoutPositions.get(node.id) || { x: 0, y: 0 };
        return {
          id: node.id,
          type: "custom",
          position: pos,
          data: {
            label: node.name,
            type: node.type,
            isSelected: false, // will be patched in effect
          },
        };
      }),
    [uniqueNodes, layoutPositions],
  );

  // --- Build React Flow edges (theme-aware) ---
  const edgeStroke = isDark ? "rgb(100, 116, 139)" : "rgb(156, 163, 175)";
  const edgeLabelFill = isDark ? "rgb(160, 174, 192)" : "rgb(107, 114, 128)";
  const edgeLabelBg = isDark ? "rgb(30, 41, 59)" : "white";

  const flowEdges = useMemo(
    (): Edge[] =>
      uniqueEdges.map((edge) => ({
        id: `${edge.source}-${edge.type}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        label: edge.type.replace(/_/g, " "),
        type: "smoothstep",
        animated: true,
        style: { stroke: edgeStroke },
        labelStyle: { fontSize: 10, fill: edgeLabelFill },
        labelBgStyle: { fill: edgeLabelBg, fillOpacity: 0.85 },
        markerEnd: { type: MarkerType.ArrowClosed, color: edgeStroke },
      })),
    [uniqueEdges, edgeStroke, edgeLabelFill, edgeLabelBg],
  );

  // --- React Flow state ---
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(flowNodes);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Sync when graph data changes → new layout
  useEffect(() => {
    setRfNodes(flowNodes);
    setRfEdges(flowEdges);
    // Fit viewport after layout recalculates
    requestAnimationFrame(() => fitView({ padding: 0.15 }));
  }, [flowNodes, flowEdges, setRfNodes, setRfEdges, fitView]);

  // Update selected highlight WITHOUT rebuilding all nodes
  useEffect(() => {
    if (selectedRef.current === selectedNodeId) return;
    selectedRef.current = selectedNodeId;

    setRfNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, isSelected: n.id === selectedNodeId },
      })),
    );
  }, [selectedNodeId, setRfNodes]);

  // --- Handle click ---
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
      const original = nodes.find((n) => n.id === node.id);
      if (original) onNodeClick?.(original);
    },
    [nodes, onNodeClick],
  );

  // --- Keyboard: Escape clears selection ---
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedNodeId(null);
      }
    },
    [],
  );

  // --- Export image ---
  const [isExporting, setIsExporting] = useState(false);

  const handleDownloadImage = useCallback(() => {
    const viewport = document.querySelector(".react-flow__viewport") as HTMLElement;
    if (!viewport || rfNodes.length === 0) return;

    setIsExporting(true);

    const nodesBounds = getNodesBounds(rfNodes);
    const padding = 60;
    const imageWidth = nodesBounds.width + padding * 2;
    const imageHeight = nodesBounds.height + padding * 2;
    const vp = getViewportForBounds(nodesBounds, imageWidth, imageHeight, 0.5, 2);

    toPng(viewport, {
      backgroundColor: isDark ? "rgb(15, 23, 42)" : "#ffffff",
      width: imageWidth,
      height: imageHeight,
      style: {
        width: String(imageWidth),
        height: String(imageHeight),
        transform: `translate(${vp.x + padding}px, ${vp.y + padding}px) scale(${vp.zoom})`,
      },
      filter: (node) =>
        !(
          node?.classList?.contains("react-flow__minimap") ||
          node?.classList?.contains("react-flow__controls") ||
          node?.classList?.contains("react-flow__panel")
        ),
    })
      .then((dataUrl) => {
        const now = new Date();
        const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(2, "0")}`;
        const a = document.createElement("a");
        a.download = `graph-rag_${ts}.png`;
        a.href = dataUrl;
        a.click();
      })
      .catch((err) => {
        console.error("Failed to export image:", err);
      })
      .finally(() => {
        setIsExporting(false);
      });
  }, [rfNodes, isDark]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        暂无图谱数据
      </div>
    );
  }

  return (
    <div className="w-full h-full" onKeyDown={handleKeyDown} tabIndex={0}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.05}
        maxZoom={3}
        proOptions={{ hideAttribution: true }}
        className={isDark ? "dark" : ""}
      >
        <Controls
          showInteractive={false}
          className={isDark ? "[&>button]:bg-slate-800 [&>button]:text-slate-200 [&>button]:border-slate-600 [&>button:hover]:bg-slate-700" : ""}
        />
        <Background color={isDark ? "rgb(51, 65, 85)" : undefined} />
        <MiniMap
          pannable
          zoomable
          nodeColor={(node) => {
            const type = (node.data?.type as string) || "entity";
            return getNodeColor(type).bg;
          }}
          maskColor={isDark ? "rgb(15, 23, 42, 0.7)" : "rgb(0, 0, 0, 0.1)"}
          style={isDark ? { backgroundColor: "rgb(30, 41, 59)" } : undefined}
        />
        <Panel position="top-right">
          <button
            onClick={handleDownloadImage}
            disabled={isExporting}
            title="导出图片"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium shadow-sm border transition-colors",
              isDark
                ? "bg-slate-800 text-slate-200 border-slate-600 hover:bg-slate-700"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50",
              isExporting && "opacity-60 cursor-not-allowed",
            )}
          >
            {isExporting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            导出图片
          </button>
        </Panel>
      </ReactFlow>
    </div>
  );
}

// ============================================================================
// Public Component (wraps with provider)
// ============================================================================

export function GraphViewer(props: GraphViewerProps) {
  return (
    <ReactFlowProvider>
      <GraphViewerInner {...props} />
    </ReactFlowProvider>
  );
}
