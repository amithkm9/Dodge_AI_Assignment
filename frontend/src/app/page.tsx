"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import ChatPanel from "@/components/ChatPanel";
import NodePopup from "@/components/NodePopup";
import {
  fetchGraphOverview,
  expandNode,
  sendChatMessage,
  checkHealth,
  GraphNode,
  GraphEdge,
} from "@/lib/api";

const GraphVisualization = dynamic(
  () => import("@/components/GraphVisualization"),
  { ssr: false }
);

interface Message {
  role: "user" | "assistant";
  content: string;
  cypher?: string | null;
}

export default function Home() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [highlightedNodes, setHighlightedNodes] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [nodePopupPosition, setNodePopupPosition] = useState({ x: 0, y: 0 });
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! I can help you analyze the **Order to Cash** process.",
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [graphDimensions, setGraphDimensions] = useState({
    width: 800,
    height: 600,
  });
  const [isHealthy, setIsHealthy] = useState(true);
  const [healthError, setHealthError] = useState("");
  const [showOverlay, setShowOverlay] = useState(true);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isChatCollapsed, setIsChatCollapsed] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const graphRef = useRef<{ zoomToFit: () => void } | null>(null);

  useEffect(() => {
    checkHealth()
      .then((health) => {
        setIsHealthy(
          health.status === "healthy" && health.neo4j === "connected"
        );
        if (health.neo4j !== "connected") {
          setHealthError("Neo4j database is not connected");
        }
      })
      .catch(() => {
        setIsHealthy(false);
        setHealthError("Backend API is not available");
      });
  }, []);

  useEffect(() => {
    if (isHealthy) {
      fetchGraphOverview().then((data) => {
        setNodes(data.nodes);
        setEdges(data.edges);
      });
    }
  }, [isHealthy]);

  useEffect(() => {
    const updateDimensions = () => {
      const container = document.getElementById("graph-container");
      if (container) {
        setGraphDimensions({
          width: container.clientWidth,
          height: container.clientHeight,
        });
      }
    };
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, [isChatCollapsed]);

  const handleNodeClick = useCallback(
    (nodeId: string, position: { x: number; y: number }) => {
      setSelectedNode(nodeId);
      setNodePopupPosition(position);
    },
    []
  );

  const handleClosePopup = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleExpandNode = useCallback(
    async (nodeId: string) => {
      const expansion = await expandNode(nodeId);
      if (expansion.nodes.length > 0) {
        const existingIds = new Set(nodes.map((n) => n.id));
        const newNodes = expansion.nodes.filter((n) => !existingIds.has(n.id));
        setNodes((prev) => [...prev, ...newNodes]);
        setEdges((prev) => [...prev, ...expansion.edges]);
      }
    },
    [nodes]
  );

  const handleSendMessage = useCallback(
    async (message: string) => {
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setIsLoading(true);
      const userMessage: Message = { role: "user", content: message };
      setMessages((prev) => [...prev, userMessage]);

      const history = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const response = await sendChatMessage(message, history, controller.signal);
        const assistantMessage: Message = {
          role: "assistant",
          content: response.answer,
          cypher: response.cypher_query,
        };
        setMessages((prev) => [...prev, assistantMessage]);

        if (response.highlighted_nodes?.length > 0) {
          setHighlightedNodes(response.highlighted_nodes);

          const existingIds = new Set(nodes.map((n) => n.id));
          const newNodes: GraphNode[] = [];
          for (const nodeId of response.highlighted_nodes.slice(0, 30)) {
            if (!existingIds.has(nodeId)) {
              const parts = nodeId.split("_");
              newNodes.push({
                id: nodeId,
                label: parts[0] || "Node",
                name: parts.slice(1).join("_") || nodeId,
              });
            }
          }
          if (newNodes.length > 0) {
            setNodes((prev) => [...prev, ...newNodes]);
          }

          if (response.highlighted_nodes.length <= 20) {
            setFocusMode(true);
            setTimeout(() => {
              graphRef.current?.zoomToFit();
            }, 500);
          }
        } else {
          setFocusMode(false);
        }
      } catch (err) {
        if ((err as { name?: string }).name !== "AbortError") {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "Sorry, something went wrong." },
          ]);
        }
      } finally {
        abortControllerRef.current = null;
        setIsLoading(false);
      }
    },
    [messages, nodes]
  );

  const handleStopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "Response stopped." },
    ]);
  }, []);

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  const handleToggleOverlay = () => {
    setShowOverlay(!showOverlay);
  };

  const handleToggleChat = () => {
    setIsChatCollapsed(!isChatCollapsed);
    setTimeout(() => {
      const container = document.getElementById("graph-container");
      if (container) {
        setGraphDimensions({
          width: container.clientWidth,
          height: container.clientHeight,
        });
      }
    }, 300);
  };

  const handleToggleFocusMode = useCallback(() => {
    setFocusMode((prev) => !prev);
    setTimeout(() => {
      graphRef.current?.zoomToFit();
    }, 100);
  }, []);

  const handleClearFocus = useCallback(() => {
    setHighlightedNodes([]);
    setFocusMode(false);
  }, []);

  const focusedNodes = useMemo(() => {
    if (!focusMode || highlightedNodes.length === 0) return nodes;
    const highlightSet = new Set(highlightedNodes);
    return nodes.filter((n) => highlightSet.has(n.id));
  }, [nodes, highlightedNodes, focusMode]);

  const focusedEdges = useMemo(() => {
    if (!focusMode || highlightedNodes.length === 0) return edges;
    const highlightSet = new Set(highlightedNodes);
    return edges.filter(
      (e) => highlightSet.has(e.source) && highlightSet.has(e.target)
    );
  }, [edges, highlightedNodes, focusMode]);

  if (!isHealthy) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-2xl shadow-lg max-w-md text-center border border-gray-100">
          <div className="w-14 h-14 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h1 className="text-lg font-semibold text-gray-900 mb-2">Backend Unavailable</h1>
          <p className="text-gray-500 text-sm mb-4">{healthError}</p>
          <div className="bg-gray-900 p-3 rounded-lg text-left">
            <code className="text-xs text-green-400 font-mono">
              cd backend && uvicorn app.main:app --reload
            </code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-white flex flex-col overflow-hidden">
      {/* Header — split to mirror the 60/40 panel layout below */}
      <header className="h-12 border-b border-gray-200 flex items-center bg-white flex-shrink-0">

        {/* Left 60% — sidebar toggle + breadcrumb */}
        <div className="flex items-center gap-3 px-4" style={{ width: "60%" }}>
          <button
            onClick={handleToggleChat}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100 transition-colors flex-shrink-0"
            title={isChatCollapsed ? "Show Chat" : "Hide Chat"}
          >
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a1 1 0 011-1h14a1 1 0 011 1v12a1 1 0 01-1 1H5a1 1 0 01-1-1V6z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 7v10" />
            </svg>
          </button>
          <div className="flex items-center gap-1.5 text-sm">
            <span className="text-gray-400">Mapping</span>
            <span className="text-gray-300">/</span>
            <span className="text-gray-900 font-semibold">Order to Cash</span>
          </div>
        </div>

        {/* Right 40% — Dodge AI info, aligned above chat panel */}
        {!isChatCollapsed && (
          <div className="flex items-center gap-2.5 px-5 border-l border-gray-200 h-full" style={{ width: "40%" }}>
            <div className="w-7 h-7 rounded-full bg-gray-900 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              D
            </div>
            <div className="leading-none">
              <p className="text-sm font-semibold text-gray-900">Dodge AI</p>
              <p className="text-xs text-gray-400 mt-0.5">Graph Agent</p>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isLoading ? "bg-amber-400 animate-pulse" : "bg-emerald-500"}`} />
              <span className="text-xs text-gray-500">{isLoading ? "Thinking…" : "Online"}</span>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph Panel — 60% */}
        <div className={`relative transition-all duration-300 ${isMinimized ? "opacity-80" : ""}`} style={{ width: "60%" }}>
          {/* Graph Controls */}
          <div className="absolute top-4 left-4 z-20 flex gap-2">
            <button
              onClick={handleMinimize}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all shadow-sm ${
                isMinimized
                  ? 'bg-blue-500 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {isMinimized ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                )}
              </svg>
              {isMinimized ? 'Expand' : 'Minimize'}
            </button>
            <button
              onClick={handleToggleOverlay}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all shadow-sm ${
                showOverlay
                  ? "bg-gray-900 text-white shadow-md"
                  : "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
              </svg>
              {showOverlay ? "Hide" : "Show"} Granular Overlay
            </button>
            {highlightedNodes.length > 0 && (
              <>
                <button
                  onClick={handleToggleFocusMode}
                  className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all shadow-sm ${
                    focusMode
                      ? "bg-red-500 text-white shadow-md"
                      : "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50"
                  }`}
                  title={focusMode ? "Show full graph" : "Focus on query results"}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    {focusMode ? (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
                    )}
                  </svg>
                  {focusMode ? "Show All" : "Focus Mode"}
                </button>
                <button
                  onClick={handleClearFocus}
                  className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all shadow-sm bg-white text-gray-700 border border-gray-200 hover:bg-gray-50"
                  title="Clear highlights"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Clear
                </button>
              </>
            )}
          </div>

          {/* Graph Container */}
          <div
            id="graph-container"
            className={`w-full h-full transition-opacity duration-300 ${showOverlay ? 'opacity-100' : 'opacity-70'}`}
            style={{ background: "#f5f5f5" }}
          >
            {!isMinimized && (
              <GraphVisualization
                ref={graphRef}
                nodes={focusedNodes}
                edges={focusedEdges}
                highlightedNodes={highlightedNodes}
                onNodeClick={handleNodeClick}
                width={graphDimensions.width}
                height={graphDimensions.height}
                focusMode={focusMode}
              />
            )}

            {isMinimized && (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <div className="w-16 h-16 bg-white rounded-2xl shadow-lg flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-sm">Graph minimized</p>
                  <button 
                    onClick={handleMinimize}
                    className="mt-3 text-blue-500 text-sm font-medium hover:text-blue-600"
                  >
                    Click to expand
                  </button>
                </div>
              </div>
            )}

            {/* Node Popup */}
            {selectedNode && !isMinimized && (
              <NodePopup
                nodeId={selectedNode}
                position={nodePopupPosition}
                onClose={handleClosePopup}
                onExpand={handleExpandNode}
              />
            )}
          </div>
        </div>

        {/* Chat Panel — 40% */}
        <div
          className={`shrink-0 border-l border-gray-200 bg-white flex flex-col transition-all duration-300 ease-in-out ${
            isChatCollapsed
              ? "w-0 opacity-0 overflow-hidden"
              : "opacity-100"
          }`}
          style={{ width: isChatCollapsed ? 0 : "40%" }}
        >
          {!isChatCollapsed && (
            <ChatPanel
              messages={messages}
              onSendMessage={handleSendMessage}
              onStop={handleStopGeneration}
              isLoading={isLoading}
            />
          )}
        </div>

        {/* Collapsed Chat Toggle */}
        {isChatCollapsed && (
          <button
            onClick={handleToggleChat}
            className="absolute right-4 bottom-4 w-12 h-12 bg-gray-900 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-800 transition-colors z-20"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
