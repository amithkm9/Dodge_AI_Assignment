"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

interface GraphNode {
  id: string;
  label: string;
  name: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

interface GraphVisualizationProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  highlightedNodes: string[];
  onNodeClick: (nodeId: string, position: { x: number; y: number }) => void;
  width: number;
  height: number;
}

const NODE_COLORS: Record<string, string> = {
  Customer: "#3b82f6",
  SalesOrder: "#6366f1",
  SalesOrderItem: "#818cf8",
  Delivery: "#0ea5e9",
  DeliveryItem: "#38bdf8",
  BillingDocument: "#ef4444",
  BillingItem: "#f87171",
  JournalEntry: "#f59e0b",
  Payment: "#22c55e",
  Material: "#06b6d4",
  Plant: "#8b5cf6",
  Address: "#ec4899",
};

const NODE_SIZES: Record<string, number> = {
  Customer: 6,
  SalesOrder: 5,
  SalesOrderItem: 3,
  Delivery: 5,
  DeliveryItem: 3,
  BillingDocument: 5,
  BillingItem: 3,
  JournalEntry: 4,
  Payment: 4,
  Material: 4,
  Plant: 4,
  Address: 4,
};

export default function GraphVisualization({
  nodes,
  edges,
  highlightedNodes,
  onNodeClick,
  width,
  height,
}: GraphVisualizationProps) {
  const fgRef = useRef<any>(null);
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({
    nodes: [],
    links: [],
  });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const highlightSet = new Set(highlightedNodes);

  useEffect(() => {
    const processedNodes = nodes.map((node) => ({
      id: node.id,
      label: node.label,
      name: node.name,
      color: highlightSet.has(node.id)
        ? "#dc2626"
        : NODE_COLORS[node.label] || "#64748b",
      size: highlightSet.has(node.id)
        ? (NODE_SIZES[node.label] || 4) * 1.8
        : NODE_SIZES[node.label] || 4,
      isHighlighted: highlightSet.has(node.id),
    }));

    const processedLinks = edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      relationship: edge.relationship,
    }));

    setGraphData({ nodes: processedNodes, links: processedLinks });
  }, [nodes, edges, highlightedNodes]);

  const handleNodeClick = useCallback(
    (node: any, event: MouseEvent) => {
      if (node?.id) {
        onNodeClick(node.id, { x: event.clientX, y: event.clientY });
      }
    },
    [onNodeClick]
  );

  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node?.id || null);
    document.body.style.cursor = node ? "pointer" : "default";
  }, []);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const baseSize = node.size || 4;
      const isHighlighted = node.isHighlighted;
      const isHovered = node.id === hoveredNode;
      const size = isHovered ? baseSize * 1.3 : baseSize;

      ctx.save();

      if (isHighlighted || isHovered) {
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isHighlighted ? 15 : 10;
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = node.color;
      ctx.fill();

      if (isHighlighted) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.strokeStyle = "#dc2626";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else if (isHovered) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      ctx.restore();

      if ((globalScale > 1.2 && isHovered) || isHighlighted) {
        const label = node.name?.substring(0, 12) || node.label || "";
        const fontSize = Math.max(10 / globalScale, 4);
        ctx.font = `500 ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        
        const textWidth = ctx.measureText(label).width;
        const padding = 3;
        const bgHeight = fontSize + padding * 2;
        const bgY = node.y + size + 3;
        
        ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
        ctx.beginPath();
        ctx.roundRect(
          node.x - textWidth / 2 - padding,
          bgY - padding,
          textWidth + padding * 2,
          bgHeight,
          3
        );
        ctx.fill();
        
        ctx.fillStyle = isHighlighted ? "#dc2626" : "#334155";
        ctx.fillText(label, node.x, bgY);
      }
    },
    [hoveredNode]
  );

  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D) => {
      const start = link.source;
      const end = link.target;
      
      if (!start.x || !end.x) return;

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.strokeStyle = "#93c5fd";
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.6;
      ctx.stroke();
      ctx.restore();
    },
    []
  );

  return (
    <div className="w-full h-full relative overflow-hidden">
      {typeof window !== "undefined" && (
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={width}
          height={height}
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            ctx.beginPath();
            ctx.arc(node.x, node.y, (node.size || 4) + 5, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          linkCanvasObject={linkCanvasObject}
          linkDirectionalArrowLength={0}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          cooldownTicks={200}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 100)}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          enablePanInteraction={true}
          backgroundColor="transparent"
          minZoom={0.3}
          maxZoom={8}
        />
      )}

      <div className="absolute bottom-4 left-4 flex items-center gap-3 bg-white/90 backdrop-blur-sm px-4 py-2.5 rounded-lg shadow-sm border border-slate-200/50">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-blue-500"></div>
          <span className="text-xs text-slate-600 font-medium">{nodes.length} nodes</span>
        </div>
        <div className="w-px h-3 bg-slate-300"></div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-blue-300 rounded"></div>
          <span className="text-xs text-slate-600 font-medium">{edges.length} edges</span>
        </div>
      </div>
    </div>
  );
}
