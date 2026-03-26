const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeDetail {
  id: string;
  label: string;
  properties: Record<string, unknown>;
  neighbors: {
    id: string;
    label: string;
    name: string;
    relationship: string;
    direction: "incoming" | "outgoing";
  }[];
}

export interface ChatResponse {
  answer: string;
  cypher_query: string | null;
  raw_results: unknown[] | null;
  highlighted_nodes: string[];
}

export interface HealthStatus {
  status: string;
  neo4j: string;
}

export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
  return res.json();
}

export async function fetchGraphOverview(): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/api/graph/overview`, { cache: "no-store" });
  if (!res.ok) return { nodes: [], edges: [] };
  return res.json();
}

export async function fetchNodeDetail(nodeId: string): Promise<NodeDetail | null> {
  const res = await fetch(`${API_BASE}/api/graph/node/${nodeId}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function expandNode(nodeId: string): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/api/graph/expand/${nodeId}`, { cache: "no-store" });
  if (!res.ok) return { nodes: [], edges: [] };
  return res.json();
}

export async function sendChatMessage(
  message: string,
  conversationHistory: { role: string; content: string }[],
  signal?: AbortSignal
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat/simple`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
    }),
    signal,
  });
  if (!res.ok) {
    return {
      answer: "Request failed. Please try again.",
      cypher_query: null,
      raw_results: null,
      highlighted_nodes: [],
    };
  }
  return res.json();
}
