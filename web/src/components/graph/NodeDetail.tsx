"use client";

import { X, User, Building, MapPin, Tag, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { GraphNode as ApiGraphNode, GraphEdge as ApiGraphEdge } from "@/lib/types";
import { cn } from "@/lib/utils";

interface NodeDetailProps {
  node: ApiGraphNode | null;
  edges: ApiGraphEdge[];
  onClose: () => void;
}

const TYPE_ICONS: Record<string, typeof User> = {
  person: User,
  organization: Building,
  location: MapPin,
  concept: Tag,
  entity: Info,
};

const TYPE_COLORS: Record<string, string> = {
  person: "text-blue-500 bg-blue-500/10",
  organization: "text-green-500 bg-green-500/10",
  location: "text-orange-500 bg-orange-500/10",
  concept: "text-purple-500 bg-purple-500/10",
  entity: "text-gray-500 bg-gray-500/10",
};

export function NodeDetail({ node, edges, onClose }: NodeDetailProps) {
  if (!node) return null;

  const nodeType = node.type?.toLowerCase() || "entity";
  const Icon = TYPE_ICONS[nodeType] || Info;
  const colorClass = TYPE_COLORS[nodeType] || TYPE_COLORS.entity;

  // Find related edges
  const outgoingEdges = edges.filter((e) => e.source === node.id);
  const incomingEdges = edges.filter((e) => e.target === node.id);

  return (
    <div className="h-full flex flex-col border-l bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold">节点详情</h3>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Node Info */}
          <div className="flex items-start gap-3">
            <div className={cn("p-3 rounded-lg", colorClass)}>
              <Icon className="h-6 w-6" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-lg truncate">{node.name}</h4>
              <Badge variant="secondary" className="mt-1">
                {node.type}
              </Badge>
            </div>
          </div>

          {/* Properties */}
          {node.properties && Object.keys(node.properties).length > 0 && (
            <>
              <Separator />
              <div>
                <h5 className="text-sm font-medium mb-2">属性</h5>
                <div className="space-y-2">
                  {Object.entries(node.properties).map(([key, value]) => {
                    // Skip internal properties
                    if (key.startsWith("_")) return null;
                    
                    return (
                      <div
                        key={key}
                        className="flex justify-between text-sm py-1"
                      >
                        <span className="text-muted-foreground">{key}</span>
                        <span className="font-medium truncate max-w-[60%]">
                          {String(value)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {/* Outgoing Relationships */}
          {outgoingEdges.length > 0 && (
            <>
              <Separator />
              <div>
                <h5 className="text-sm font-medium mb-2">
                  出向关系 ({outgoingEdges.length})
                </h5>
                <div className="space-y-2">
                  {outgoingEdges.map((edge, i) => (
                    <div
                      key={i}
                      className="text-sm p-2 rounded-md bg-muted/50"
                    >
                      <span className="text-muted-foreground">
                        {edge.type.replace(/_/g, " ")}
                      </span>
                      <span className="mx-2">→</span>
                      <span className="font-medium">
                        {edge.target_name || edge.target}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Incoming Relationships */}
          {incomingEdges.length > 0 && (
            <>
              <Separator />
              <div>
                <h5 className="text-sm font-medium mb-2">
                  入向关系 ({incomingEdges.length})
                </h5>
                <div className="space-y-2">
                  {incomingEdges.map((edge, i) => (
                    <div
                      key={i}
                      className="text-sm p-2 rounded-md bg-muted/50"
                    >
                      <span className="font-medium">
                        {edge.source_name || edge.source}
                      </span>
                      <span className="mx-2">→</span>
                      <span className="text-muted-foreground">
                        {edge.type.replace(/_/g, " ")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Node ID */}
          <Separator />
          <div className="text-xs text-muted-foreground">
            <p>ID: {node.id}</p>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
