"use client";

import { useState } from "react";
import {
  Database,
  Network,
  ChevronDown,
  ChevronUp,
  FileText,
  ExternalLink,
  ArrowRight,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { RetrievalResult, GraphContext, GraphEdge, GraphNode, TimingInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

// Maximum edges to show inline
const MAX_INLINE_EDGES = 5;

interface SourcePanelProps {
  results: RetrievalResult[];
  graphContext: GraphContext | null;
  searchType: "hybrid" | "vector" | "graph";
  timing?: TimingInfo;
}

// Format milliseconds to human readable string
function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

export function SourcePanel({
  results,
  graphContext,
  searchType,
  timing,
}: SourcePanelProps) {
  const [isVectorOpen, setIsVectorOpen] = useState(false);
  const [isGraphOpen, setIsGraphOpen] = useState(false);

  // Separate vector results (chunks) and entity results
  const vectorResults = results.filter((r) => !r.is_entity);
  const entityResults = results.filter((r) => r.is_entity);
  const edges = graphContext?.edges || [];
  const nodes = graphContext?.nodes || [];

  const hasVectorData = vectorResults.length > 0;
  const hasGraphData = entityResults.length > 0 || edges.length > 0;

  if (!hasVectorData && !hasGraphData) {
    return null;
  }

  return (
    <div className="mt-4 space-y-2 bg-muted/30 rounded-lg p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <FileText className="h-3.5 w-3.5" />
        <span className="font-medium">数据来源</span>
        <Badge variant="outline" className="ml-auto text-xs h-5">
          {searchType === "hybrid"
            ? "混合检索"
            : searchType === "vector"
            ? "向量检索"
            : "图检索"}
        </Badge>
      </div>

      {/* Vector Search Results */}
      {hasVectorData && (
        <Collapsible open={isVectorOpen} onOpenChange={setIsVectorOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between px-2 py-1.5 h-auto"
            >
              <div className="flex items-center gap-2">
                <Database className="h-3.5 w-3.5 text-blue-500" />
                <span className="text-sm">向量检索</span>
                <Badge variant="secondary" className="text-xs h-5">
                  {vectorResults.length} 条
                </Badge>
                {timing && timing.vector_search_ms > 0 && (
                  <span className="text-xs text-muted-foreground flex items-center gap-0.5">
                    <Clock className="h-3 w-3" />
                    {formatDuration(timing.vector_search_ms)}
                  </span>
                )}
              </div>
              {isVectorOpen ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ScrollArea className="max-h-40">
              <div className="space-y-1.5 px-2 py-1.5">
                {vectorResults.slice(0, 3).map((result, index) => (
                  <div
                    key={`${result.id}-${index}`}
                    className="rounded border bg-muted/30 p-2 text-xs"
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-xs h-4 px-1",
                          result.score >= 0.8
                            ? "border-green-500 text-green-600"
                            : result.score >= 0.6
                            ? "border-yellow-500 text-yellow-600"
                            : "border-gray-400"
                        )}
                      >
                        {(result.score * 100).toFixed(0)}%
                      </Badge>
                      <span className="text-muted-foreground truncate">
                        {result.name || result.id}
                      </span>
                    </div>
                    <p className="text-muted-foreground line-clamp-2">
                      {result.text}
                    </p>
                  </div>
                ))}
                {vectorResults.length > 3 && (
                  <p className="text-xs text-muted-foreground text-center py-1">
                    还有 {vectorResults.length - 3} 条结果
                  </p>
                )}
              </div>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Graph Context Results */}
      {hasGraphData && (
        <Collapsible open={isGraphOpen} onOpenChange={setIsGraphOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between px-2 py-1.5 h-auto"
            >
              <div className="flex items-center gap-2">
                <Network className="h-3.5 w-3.5 text-orange-500" />
                <span className="text-sm">图谱推理</span>
                <Badge variant="secondary" className="text-xs h-5">
                  {nodes.length || entityResults.length} 实体 / {edges.length} 关系
                </Badge>
                {timing && (timing.graph_search_ms > 0 || timing.graph_expansion_ms > 0) && (
                  <span className="text-xs text-muted-foreground flex items-center gap-0.5">
                    <Clock className="h-3 w-3" />
                    {formatDuration(timing.graph_search_ms + timing.graph_expansion_ms)}
                  </span>
                )}
              </div>
              {isGraphOpen ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="space-y-2 px-2 py-1.5">
              {/* Entity Tags */}
              {(nodes.length > 0 || entityResults.length > 0) && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1.5">
                    相关实体
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {(nodes.length > 0 ? nodes : entityResults).slice(0, 10).map((entity, index) => {
                      const entityType = 'type' in entity 
                        ? entity.type 
                        : (entity as RetrievalResult).properties?.entity_type as string | undefined;
                      return (
                        <Badge
                          key={`${entity.id}-${index}`}
                          variant="outline"
                          className="text-xs h-5 gap-1"
                        >
                          <span
                            className={cn(
                              "w-1.5 h-1.5 rounded-full",
                              getEntityColor(entityType)
                            )}
                          />
                          {entity.name}
                        </Badge>
                      );
                    })}
                    {(nodes.length > 10 || entityResults.length > 10) && (
                      <Badge variant="outline" className="text-xs h-5 text-muted-foreground">
                        +{Math.max(nodes.length, entityResults.length) - 10}
                      </Badge>
                    )}
                  </div>
                </div>
              )}

              {/* Relationship Preview */}
              {edges.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-xs text-muted-foreground">关系路径</p>
                    {edges.length > MAX_INLINE_EDGES && (
                      <RelationshipDialog edges={edges} />
                    )}
                  </div>
                  <div className="space-y-1">
                    {edges.slice(0, MAX_INLINE_EDGES).map((edge, index) => (
                      <CompactRelationshipEdge key={index} edge={edge} />
                    ))}
                    {edges.length > MAX_INLINE_EDGES && (
                      <p className="text-xs text-muted-foreground text-center py-0.5">
                        还有 {edges.length - MAX_INLINE_EDGES} 条关系...
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

// Helper function to get entity color
function getEntityColor(type?: string): string {
  switch (type?.toLowerCase()) {
    case "person":
      return "bg-blue-500";
    case "organization":
      return "bg-green-500";
    case "location":
      return "bg-orange-500";
    case "concept":
      return "bg-purple-500";
    case "technology":
      return "bg-cyan-500";
    case "product":
      return "bg-pink-500";
    case "event":
      return "bg-amber-500";
    default:
      return "bg-gray-500";
  }
}

// Compact relationship edge for inline display
function CompactRelationshipEdge({ edge }: { edge: GraphEdge }) {
  const sourceName = edge.source_name || edge.source;
  const targetName = edge.target_name || edge.target;
  const edgeType = edge.type.replace(/_/g, " ");

  return (
    <div className="flex items-center gap-1 text-xs py-1 px-2 rounded bg-muted/40 overflow-hidden">
      <span className="font-medium truncate max-w-[80px]" title={sourceName}>
        {sourceName}
      </span>
      <span className="text-muted-foreground flex items-center gap-0.5 shrink-0">
        <ArrowRight className="h-3 w-3" />
        <span className="text-[10px] bg-muted px-1 rounded">{edgeType}</span>
        <ArrowRight className="h-3 w-3" />
      </span>
      <span className="font-medium truncate max-w-[80px]" title={targetName}>
        {targetName}
      </span>
    </div>
  );
}

// Full relationship edge for dialog
function FullRelationshipEdge({ edge }: { edge: GraphEdge }) {
  const sourceName = edge.source_name || edge.source;
  const targetName = edge.target_name || edge.target;
  const edgeType = edge.type.replace(/_/g, " ");

  return (
    <div className="flex items-center gap-2 text-sm py-2 px-3 rounded-lg bg-muted/30 border">
      <span className="font-medium text-foreground">{sourceName}</span>
      <span className="text-muted-foreground flex items-center gap-1.5 shrink-0">
        <ArrowRight className="h-4 w-4" />
        <Badge variant="secondary" className="text-xs">
          {edgeType}
        </Badge>
        <ArrowRight className="h-4 w-4" />
      </span>
      <span className="font-medium text-foreground">{targetName}</span>
    </div>
  );
}

// Dialog for viewing all relationships
function RelationshipDialog({ edges }: { edges: GraphEdge[] }) {
  // Group edges by relationship type
  const groupedEdges = edges.reduce((acc, edge) => {
    const type = edge.type;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(edge);
    return acc;
  }, {} as Record<string, GraphEdge[]>);

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-5 px-1.5 text-xs gap-1">
          <ExternalLink className="h-3 w-3" />
          查看全部
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Network className="h-5 w-5 text-orange-500" />
            关系路径详情
            <Badge variant="secondary">{edges.length} 条关系</Badge>
          </DialogTitle>
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] pr-4">
          <div className="space-y-4">
            {Object.entries(groupedEdges).map(([type, typeEdges]) => (
              <div key={type}>
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline" className="capitalize">
                    {type.replace(/_/g, " ")}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {typeEdges.length} 条
                  </span>
                </div>
                <div className="space-y-1.5 pl-2">
                  {typeEdges.map((edge, index) => (
                    <FullRelationshipEdge key={index} edge={edge} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
