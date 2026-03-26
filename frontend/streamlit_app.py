"""
Dodge AI - Streamlit Frontend
SAP Order-to-Cash Graph Explorer with Natural Language Query Interface
"""

import streamlit as st
import requests
import json
import os
from streamlit_agraph import agraph, Node, Edge, Config

# Configuration - support environment variable for deployment
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Dodge AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Clean white theme CSS
st.markdown("""
<style>
    /* Global white background */
    .stApp { background-color: #ffffff; }
    .main .block-container { 
        padding: 1rem 2rem; 
        max-width: 100%;
        background-color: #ffffff;
    }
    
    /* Header */
    .app-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }
    .app-logo {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 20px;
    }
    .app-title { font-size: 1.4rem; font-weight: 700; color: #111827; margin: 0; }
    .app-subtitle { font-size: 0.8rem; color: #6b7280; margin: 0; }
    
    /* Panel headers */
    .panel-header {
        font-size: 0.9rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Legend */
    .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        padding: 8px 12px;
        background: #f9fafb;
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid #e5e7eb;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.75rem;
        color: #4b5563;
    }
    .legend-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    
    /* Graph container */
    .graph-container {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 12px;
    }
    
    /* Chat container */
    .chat-container {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        height: 480px;
        overflow-y: auto;
    }
    
    /* Chat messages */
    .message-user {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 12px;
    }
    .message-user-bubble {
        background: #6366f1;
        color: white;
        padding: 10px 14px;
        border-radius: 16px 16px 4px 16px;
        max-width: 85%;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .message-assistant {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 12px;
    }
    .message-assistant-bubble {
        background: #ffffff;
        color: #1f2937;
        padding: 10px 14px;
        border-radius: 16px 16px 16px 4px;
        max-width: 85%;
        font-size: 0.9rem;
        line-height: 1.5;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* Chat input area */
    .chat-input-area {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid #e5e7eb;
    }
    
    /* Node detail card */
    .node-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 14px;
        margin-top: 12px;
    }
    .node-card-header {
        font-weight: 600;
        color: #6366f1;
        font-size: 0.9rem;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px solid #f3f4f6;
    }
    .node-property {
        font-size: 0.8rem;
        color: #4b5563;
        padding: 3px 0;
    }
    .node-property-key {
        color: #6b7280;
        font-weight: 500;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        color: #374151;
        transition: all 0.15s;
    }
    .stButton > button:hover {
        background: #f9fafb;
        border-color: #d1d5db;
    }
    .stButton > button[kind="primary"] {
        background: #6366f1;
        color: white;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #4f46e5;
    }
    
    /* Text input */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        padding: 10px 14px;
        font-size: 0.9rem;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-size: 0.85rem;
        font-weight: 500;
        color: #6b7280;
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Example query buttons */
    .example-btn {
        background: #f3f4f6;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 0.75rem;
        color: #4b5563;
        cursor: pointer;
        transition: all 0.15s;
    }
    .example-btn:hover {
        background: #e5e7eb;
    }
    
    /* Streaming cursor animation */
    .streaming-cursor {
        animation: blink 1s infinite;
        color: #6366f1;
    }
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    .streaming-indicator {
        color: #9ca3af;
        font-style: italic;
    }
    
    /* Stats panel */
    .stats-panel {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
    }
    .stat-item {
        text-align: center;
        padding: 8px;
        background: white;
        border-radius: 6px;
        border: 1px solid #e5e7eb;
    }
    .stat-value {
        font-size: 1.2rem;
        font-weight: 700;
        color: #6366f1;
    }
    .stat-label {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Node colors
NODE_COLORS = {
    "Customer": "#3b82f6",
    "SalesOrder": "#8b5cf6",
    "Delivery": "#10b981",
    "BillingDocument": "#ef4444",
    "JournalEntry": "#f59e0b",
    "Payment": "#eab308",
    "Material": "#06b6d4",
    "Plant": "#84cc16",
}

NODE_SIZES = {
    "Customer": 28,
    "SalesOrder": 24,
    "Delivery": 24,
    "BillingDocument": 24,
    "JournalEntry": 20,
    "Payment": 20,
    "Material": 20,
    "Plant": 20,
}


def init_session_state():
    defaults = {
        "messages": [],
        "highlighted_nodes": [],
        "selected_node": None,
        "graph_data": {"nodes": [], "edges": []},
        "last_cypher": None,
        "streaming_active": False,
        "streaming_message": None,
        "streaming_history": None,
        "graph_stats": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def check_api_health() -> dict:
    try:
        return requests.get(f"{API_BASE}/api/health", timeout=5).json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def fetch_graph_overview() -> dict:
    try:
        resp = requests.get(f"{API_BASE}/api/graph/overview", timeout=30)
        return resp.json() if resp.ok else {"nodes": [], "edges": []}
    except:
        return {"nodes": [], "edges": []}


def fetch_node_detail(node_id: str) -> dict:
    try:
        resp = requests.get(f"{API_BASE}/api/graph/node/{node_id}", timeout=10)
        return resp.json() if resp.ok else {}
    except:
        return {}


def expand_node_api(node_id: str) -> dict:
    try:
        resp = requests.get(f"{API_BASE}/api/graph/expand/{node_id}", timeout=10)
        return resp.json() if resp.ok else {"nodes": [], "edges": []}
    except:
        return {"nodes": [], "edges": []}


def search_nodes(query: str) -> list:
    try:
        resp = requests.get(f"{API_BASE}/api/graph/search", params={"q": query}, timeout=10)
        return resp.json() if resp.ok else []
    except:
        return []


def chat_simple(message: str, history: list) -> dict:
    try:
        resp = requests.post(
            f"{API_BASE}/api/chat/simple",
            json={"message": message, "conversation_history": history},
            timeout=60,
        )
        return resp.json() if resp.ok else {"answer": "Request failed", "cypher_query": None, "highlighted_nodes": []}
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "cypher_query": None, "highlighted_nodes": []}


def chat_streaming(message: str, history: list):
    """
    Stream chat response using SSE from /api/chat endpoint.
    Yields tuples of (event_type, content) for real-time updates.
    """
    try:
        with requests.post(
            f"{API_BASE}/api/chat",
            json={"message": message, "conversation_history": history},
            stream=True,
            timeout=120,
        ) as response:
            if not response.ok:
                yield ("error", "Request failed")
                return
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        try:
                            data = json.loads(line_str[6:])
                            event_type = data.get("type", "unknown")
                            content = data.get("content", "")
                            yield (event_type, content)
                            
                            if event_type == "done":
                                return
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield ("error", f"Connection error: {str(e)}")


def fetch_graph_stats() -> dict:
    """Fetch graph statistics from the backend."""
    try:
        resp = requests.get(f"{API_BASE}/api/graph/stats", timeout=10)
        return resp.json() if resp.ok else {}
    except:
        return {}


def build_agraph_data(graph_data: dict, highlighted: list = None):
    highlighted = set(highlighted or [])
    nodes, edges, seen = [], [], set()
    
    for node in graph_data.get("nodes", []):
        nid = node["id"]
        if nid in seen:
            continue
        seen.add(nid)
        
        label = node.get("label", "Unknown")
        name = node.get("name", nid)
        color = NODE_COLORS.get(label, "#6366f1")
        size = NODE_SIZES.get(label, 20)
        
        # Highlight nodes from query results - make them red and larger
        is_highlighted = nid in highlighted
        if is_highlighted:
            color = "#dc2626"  # Bright red
            size = int(size * 1.5)
        
        nodes.append(Node(
            id=nid,
            label=name[:12] + "..." if len(name) > 12 else name,
            size=size,
            color=color,
            title=f"{'⭐ ' if is_highlighted else ''}{label}: {name}",
            shape="dot",
        ))
    
    for edge in graph_data.get("edges", []):
        src = edge["source"] if isinstance(edge["source"], str) else edge["source"]["id"]
        tgt = edge["target"] if isinstance(edge["target"], str) else edge["target"]["id"]
        if src in seen and tgt in seen:
            # Highlight edges connected to highlighted nodes
            edge_color = "#ef4444" if (src in highlighted or tgt in highlighted) else "#d1d5db"
            edges.append(Edge(source=src, target=tgt, color=edge_color))
    
    return nodes, edges


def render_header():
    st.markdown("""
    <div class="app-header">
        <div class="app-logo">⚡</div>
        <div>
            <div class="app-title">Dodge AI</div>
            <div class="app-subtitle">SAP Order-to-Cash Graph Explorer</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_legend():
    items = "".join([
        f'<span class="legend-item"><span class="legend-dot" style="background:{c}"></span>{l.replace("BillingDocument","Invoice").replace("JournalEntry","Journal")}</span>'
        for l, c in NODE_COLORS.items()
    ])
    # Add highlighted indicator
    items += '<span class="legend-item"><span class="legend-dot" style="background:#dc2626"></span>Highlighted</span>'
    st.markdown(f'<div class="legend">{items}</div>', unsafe_allow_html=True)


def render_graph_stats():
    """Render graph statistics panel showing node and relationship counts."""
    # Fetch stats if not cached or refresh requested
    if st.session_state.graph_stats is None:
        st.session_state.graph_stats = fetch_graph_stats()
    
    stats = st.session_state.graph_stats
    if not stats:
        return
    
    node_counts = stats.get("node_counts", {})
    rel_count = stats.get("relationship_count", 0)
    
    # Calculate total nodes
    total_nodes = sum(node_counts.values())
    
    # Display key stats in a compact grid
    with st.expander("📊 Graph Statistics", expanded=False):
        # Summary row
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Nodes", f"{total_nodes:,}")
        with col2:
            st.metric("Relationships", f"{rel_count:,}")
        
        # Node breakdown
        st.markdown("**Node counts by type:**")
        cols = st.columns(4)
        sorted_counts = sorted(node_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (label, count) in enumerate(sorted_counts):
            with cols[i % 4]:
                display_label = label.replace("BillingDocument", "Invoice").replace("JournalEntry", "Journal")
                color = NODE_COLORS.get(label, "#6366f1")
                st.markdown(
                    f'<div style="text-align:center; padding:4px;">'
                    f'<span style="color:{color}; font-weight:600;">{count:,}</span><br>'
                    f'<span style="font-size:0.7rem; color:#6b7280;">{display_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )


def render_graph_panel():
    st.markdown('<div class="panel-header">🔗 Knowledge Graph</div>', unsafe_allow_html=True)
    
    # Show highlighted count if any
    if st.session_state.highlighted_nodes:
        st.markdown(
            f'<div style="background:#fef2f2; border:1px solid #fecaca; border-radius:6px; padding:8px 12px; margin-bottom:10px; font-size:0.85rem;">'
            f'🔴 <strong>{len(st.session_state.highlighted_nodes)}</strong> nodes highlighted from your query (shown in red)'
            f'</div>',
            unsafe_allow_html=True
        )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("↻ Reload", use_container_width=True):
            st.session_state.graph_data = fetch_graph_overview()
            st.session_state.graph_stats = None  # Refresh stats too
            st.rerun()
    with col2:
        if st.button("✕ Clear", use_container_width=True):
            st.session_state.selected_node = None
            st.session_state.highlighted_nodes = []
            st.rerun()
    with col3:
        search = st.text_input("Search", placeholder="Search nodes...", label_visibility="collapsed")
    
    if search and len(search) >= 2:
        results = search_nodes(search)
        if results:
            for r in results[:3]:
                if st.button(f"→ {r['name'][:25]} ({r['label']})", key=f"s_{r['id']}"):
                    st.session_state.selected_node = r["id"]
                    st.rerun()
    
    render_legend()
    render_graph_stats()
    
    if not st.session_state.graph_data.get("nodes"):
        with st.spinner("Loading graph..."):
            st.session_state.graph_data = fetch_graph_overview()
    
    data = st.session_state.graph_data
    if data.get("nodes"):
        nodes, edges = build_agraph_data(data, st.session_state.highlighted_nodes)
        
        config = Config(
            width="100%",
            height=380,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#ef4444",
        )
        
        # Use a key based on highlighted nodes to force re-render when highlights change
        graph_key = f"graph_{len(st.session_state.highlighted_nodes)}_{hash(tuple(sorted(st.session_state.highlighted_nodes[:5]))) if st.session_state.highlighted_nodes else 0}"
        
        selected = agraph(nodes=nodes, edges=edges, config=config, key=graph_key)
        if selected and selected != st.session_state.selected_node:
            st.session_state.selected_node = selected
            st.rerun()
    
    # Node detail
    if st.session_state.selected_node:
        detail = fetch_node_detail(st.session_state.selected_node)
        if detail:
            label = detail.get('label', 'Node')
            raw_id = st.session_state.selected_node.split('_', 1)[-1]
            
            st.markdown(f'<div class="node-card"><div class="node-card-header">📋 {label}: {raw_id}</div>', unsafe_allow_html=True)
            
            props = detail.get("properties", {})
            for k, v in list(props.items())[:6]:
                if v is not None:
                    st.markdown(f'<div class="node-property"><span class="node-property-key">{k}:</span> {v}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            neighbors = detail.get("neighbors", [])
            if neighbors:
                with st.expander(f"Connected nodes ({len(neighbors)})"):
                    for n in neighbors[:5]:
                        dir_icon = "→" if n["direction"] == "outgoing" else "←"
                        if st.button(f"{dir_icon} {n['relationship']}: {n['name'][:20]}", key=f"nb_{n['id']}"):
                            st.session_state.selected_node = n["id"]
                            st.rerun()
            
            if st.button("🔍 Expand this node"):
                expansion = expand_node_api(st.session_state.selected_node)
                if expansion.get("nodes"):
                    existing = {n["id"] for n in st.session_state.graph_data.get("nodes", [])}
                    for new in expansion["nodes"]:
                        if new["id"] not in existing:
                            st.session_state.graph_data["nodes"].append(new)
                    st.session_state.graph_data["edges"].extend(expansion.get("edges", []))
                    st.rerun()


def render_chat_panel():
    st.markdown('<div class="panel-header">💬 Chat with your data</div>', unsafe_allow_html=True)
    
    # Example queries
    examples = [
        "Show all customers with order totals",
        "Which orders are not delivered?",
        "Trace complete O2C flows",
        "Find broken/incomplete flows",
        "Top products by billing count",
    ]
    
    with st.expander("💡 Example queries"):
        cols = st.columns(2)
        for i, ex in enumerate(examples):
            with cols[i % 2]:
                if st.button(ex, key=f"ex_{i}", use_container_width=True):
                    send_message(ex)
    
    # Chat messages container
    chat_container = st.container()
    
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        if not st.session_state.messages and not st.session_state.get("streaming_active"):
            st.markdown("""
            <div style="text-align:center; padding:40px; color:#9ca3af;">
                <div style="font-size:2rem; margin-bottom:10px;">💬</div>
                <div>Ask questions about your SAP O2C data</div>
                <div style="font-size:0.8rem; margin-top:5px;">Try: "Show all customers" or "Find unpaid invoices"</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Render existing messages
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'''
                    <div class="message-user">
                        <div class="message-user-bubble">{msg["content"]}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown(f'''
                    <div class="message-assistant">
                        <div class="message-assistant-bubble">{msg["content"]}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                    if msg.get("cypher"):
                        with st.expander("View Cypher query"):
                            st.code(msg["cypher"], language="cypher")
            
            # Handle streaming response
            if st.session_state.get("streaming_active"):
                process_streaming_response()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Input
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "Message",
            placeholder="Ask about orders, deliveries, invoices, payments...",
            key="chat_input",
            label_visibility="collapsed",
            disabled=st.session_state.get("streaming_active", False),
        )
    with col2:
        send_disabled = st.session_state.get("streaming_active", False)
        if st.button("Send", type="primary", use_container_width=True, disabled=send_disabled):
            if user_input:
                send_message(user_input)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.highlighted_nodes = []
            st.session_state.streaming_active = False
            st.rerun()
    with col2:
        if st.session_state.highlighted_nodes:
            st.markdown(f"<small>🔴 {len(st.session_state.highlighted_nodes)} nodes in graph</small>", unsafe_allow_html=True)
    
    # Show highlighted nodes as clickable list
    if st.session_state.highlighted_nodes:
        with st.expander(f"📍 View highlighted nodes ({len(st.session_state.highlighted_nodes)})"):
            for node_id in st.session_state.highlighted_nodes[:10]:
                parts = node_id.split("_", 1)
                label = parts[0] if len(parts) > 1 else "Node"
                display_id = parts[1] if len(parts) > 1 else node_id
                if st.button(f"{label}: {display_id}", key=f"hl_{node_id}"):
                    st.session_state.selected_node = node_id
                    st.rerun()
            if len(st.session_state.highlighted_nodes) > 10:
                st.caption(f"...and {len(st.session_state.highlighted_nodes) - 10} more")


def send_message(message: str, use_streaming: bool = True):
    st.session_state.messages.append({"role": "user", "content": message})
    
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-6:]]
    
    if use_streaming:
        # Use streaming endpoint for real-time response
        st.session_state.streaming_active = True
        st.session_state.streaming_message = message
        st.session_state.streaming_history = history[:-1]
    else:
        # Fallback to simple endpoint
        with st.spinner(""):
            response = chat_simple(message, history[:-1])
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.get("answer", "No response"),
            "cypher": response.get("cypher_query"),
        })
        st.session_state.highlighted_nodes = response.get("highlighted_nodes", [])
    
    st.rerun()


def process_streaming_response():
    """Process a streaming response and update the UI in real-time."""
    if not st.session_state.get("streaming_active"):
        return
    
    message = st.session_state.streaming_message
    history = st.session_state.streaming_history
    
    # Create placeholder for streaming content
    response_placeholder = st.empty()
    cypher_query = None
    highlighted_nodes = []
    full_response = ""
    
    with response_placeholder.container():
        st.markdown("""
        <div class="message-assistant">
            <div class="message-assistant-bubble">
                <span class="streaming-indicator">Thinking...</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    for event_type, content in chat_streaming(message, history):
        if event_type == "cypher":
            cypher_query = content
        elif event_type == "highlights":
            highlighted_nodes = content if isinstance(content, list) else []
        elif event_type == "text":
            full_response += content
            with response_placeholder.container():
                st.markdown(f'''
                <div class="message-assistant">
                    <div class="message-assistant-bubble">{full_response}<span class="streaming-cursor">▌</span></div>
                </div>
                ''', unsafe_allow_html=True)
        elif event_type == "error":
            full_response = content
            break
        elif event_type == "done":
            break
    
    # Clear streaming state
    st.session_state.streaming_active = False
    st.session_state.streaming_message = None
    st.session_state.streaming_history = None
    
    # Add final message to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response or "No response received",
        "cypher": cypher_query,
    })
    st.session_state.highlighted_nodes = highlighted_nodes
    
    # Final render without cursor
    with response_placeholder.container():
        st.markdown(f'''
        <div class="message-assistant">
            <div class="message-assistant-bubble">{full_response}</div>
        </div>
        ''', unsafe_allow_html=True)
        if cypher_query:
            with st.expander("View Cypher query"):
                st.code(cypher_query, language="cypher")


def main():
    init_session_state()
    render_header()
    
    # Health check
    health = check_api_health()
    if health.get("status") == "error":
        st.error(f"Backend unavailable: {health.get('message')}")
        st.code("cd backend && uvicorn app.main:app --reload")
        return
    if health.get("neo4j") != "connected":
        st.warning(f"Neo4j: {health.get('neo4j')}")
    
    # Main layout: Graph (left 60%) | Chat (right 40%)
    graph_col, chat_col = st.columns([3, 2], gap="large")
    
    with graph_col:
        render_graph_panel()
    
    with chat_col:
        render_chat_panel()


if __name__ == "__main__":
    main()
