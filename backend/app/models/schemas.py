from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    cypher_query: str | None = None
    raw_results: list[dict] | None = None
    highlighted_nodes: list[str] = []


class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict
    color: str = "#6366f1"


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class NodeDetail(BaseModel):
    id: str
    label: str
    properties: dict
    neighbors: list[dict] = []
