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
    page_title="Dodge AI - Order to Cash",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Modern UI CSS matching the reference design
st.markdown("""
<style>
    /* Global styling */
    .stApp { background-color: #f8fafc; }
    .main .block-container { 
        padding: 0.5rem 1rem; 
        max-width: 100%;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Top navigation bar */
    .top-nav {
        display: flex;
        align-items: center;
        padding: 8px 16px;
        background: white;
        border-bottom: 1px solid #e2e8f0;
        margin: -0.5rem -1rem 1rem -1rem;
        gap: 12px;
    }
    .nav-title {
        font-size: 0.9rem;
        color: #64748b;
    }
    .nav-title strong {
        color: #1e293b;
    }
    
    /* Main container */
    .main-container {
        display: flex;
        gap: 0;
        height: calc(100vh - 80px);
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Graph panel */
    .graph-panel {
        flex: 1;
        background: #f0f7ff;
        position: relative;
        min-height: 500px;
    }
    
    /* Graph controls */
    .graph-controls {
        position: absolute;
        top: 12px;
        left: 12px;
        display: flex;
        gap: 8px;
        z-index: 100;
    }
    .control-btn {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.8rem;
        color: #475569;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .control-btn:hover {
        background: #f8fafc;
    }
    
    /* Node detail popup */
    .node-popup {
        position: absolute;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        padding: 16px;
        min-width: 320px;
        max-width: 400px;
        z-index: 1000;
        max-height: 400px;
        overflow-y: auto;
    }
    .node-popup-header {
        font-weight: 600;
        font-size: 1rem;
        color: #1e293b;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e2e8f0;
    }
    .node-popup-row {
        display: flex;
        padding: 4px 0;
        font-size: 0.85rem;
        border-bottom: 1px solid #f1f5f9;
    }
    .node-popup-key {
        color: #64748b;
        min-width: 140px;
        font-weight: 500;
    }
    .node-popup-value {
        color: #1e293b;
        word-break: break-word;
    }
    .node-popup-footer {
        margin-top: 12px;
        padding-top: 8px;
        border-top: 1px solid #e2e8f0;
        font-size: 0.8rem;
        color: #94a3b8;
    }
    
    /* Chat panel */
    .chat-panel {
        width: 380px;
        background: white;
        border-left: 1px solid #e2e8f0;
        display: flex;
        flex-direction: column;
    }
    .chat-header {
        padding: 16px;
        border-bottom: 1px solid #e2e8f0;
    }
    .chat-header-title {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 8px;
    }
    .chat-agent {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .chat-agent-avatar {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .chat-agent-name {
        font-weight: 600;
        color: #1e293b;
    }
    .chat-agent-role {
        font-size: 0.8rem;
        color: #64748b;
    }
    
    /* Chat messages */
    .chat-messages {
        flex: 1;
        padding: 16px;
        overflow-y: auto;
        background: #fafafa;
    }
    .chat-message {
        margin-bottom: 16px;
    }
    .chat-message-user {
        display: flex;
        justify-content: flex-end;
    }
    .chat-message-user .bubble {
        background: #1e293b;
        color: white;
        padding: 10px 14px;
        border-radius: 12px 12px 4px 12px;
        max-width: 85%;
        font-size: 0.9rem;
    }
    .chat-message-assistant {
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }
    .chat-message-assistant .avatar {
        width: 28px;
        height: 28px;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 0.75rem;
        flex-shrink: 0;
    }
    .chat-message-assistant .bubble {
        background: white;
        color: #1e293b;
        padding: 10px 14px;
        border-radius: 12px 12px 12px 4px;
        max-width: 85%;
        font-size: 0.9rem;
        border: 1px solid #e2e8f0;
    }
    
    /* Chat input */
    .chat-input-area {
        padding: 16px;
        border-top: 1px solid #e2e8f0;
        background: white;
    }
    .chat-status {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 10px;
        font-size: 0.8rem;
        color: #22c55e;
    }
    .chat-status-dot {
        width: 8px;
        height: 8px;
        background: #22c55e;
        border-radius: 50%;
    }
    .chat-input-wrapper {
        display: flex;
        gap: 8px;
    }
    
    /* Streamlit overrides */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 10px 14px;
        font-size: 0.9rem;
        background: #f8fafc;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    .stTextInput > div > div > input::placeholder {
        color: #94a3b8;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 8px 16px;
    }
    .stButton > button[kind="primary"] {
        background: #1e293b;
        color: white;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #334155;
    }
    .stButton > button[kind="secondary"] {
        background: white;
        color: #475569;
        border: 1px solid #e2e8f0;
    }
    
    /* Legend */
    .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        padding: 10px 16px;
        background: white;
        border-bottom: 1px solid #e2e8f0;
        font-size: 0.8rem;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #475569;
    }
    .legend-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 0.85rem;
        font-weight: 500;
        color: #475569;
        background: #f8fafc;
        border-radius: 6px;
    }
    
    /* Node detail card in sidebar */
    .node-detail-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        margin-top: 8px;
    }
    .node-detail-header {
        font-weight: 600;
        font-size: 0.95rem;
        color: #1e293b;
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 1px solid #f1f5f9;
    }
    .node-detail-entity {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 4px;
    }
    .node-detail-row {
        display: flex;
        font-size: 0.8rem;
        padding: 3px 0;
    }
    .node-detail-key {
        color: #64748b;
        min-width: 120px;
    }
    .node-detail-value {
        color: #1e293b;
        font-weight: 500;
    }
    .node-detail-footer {
        margin-top: 8px;
        padding-top: 6px;
        border-top: 1px solid #f1f5f9;
        font-size: 0.75rem;
        color: #94a3b8;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# Node colors matching reference
NODE_COLORS = {
    "Customer": "#3b82f6",      # Blue
    "SalesOrder": "#8b5cf6",    # Purple
    "SalesOrderItem": "#a78bfa", # Light purple
    "Delivery": "#10b981",      # Green
    "DeliveryItem": "#34d399",  # Light green
    "BillingDocument": "#ef4444", # Red
    "BillingItem": "#f87171",   # Light red
    "JournalEntry": "#f59e0b",  # Orange
    "Payment": "#eab308",       # Yellow
    "Material": "#06b6d4",      # Cyan
    "Plant": "#84cc16",         # Lime
    "Address": "#6366f1",       # Indigo
}

NODE_SIZES = {
    "Customer": 30,
    "SalesOrder": 26,
    "SalesOrderItem": 18,
    "Delivery": 26,
    "DeliveryItem": 18,
    "BillingDocument": 26,
    "BillingItem": 18,
    "JournalEntry": 24,
    "Payment": 24,
    "Material": 22,
    "Plant": 22,
    "Address": 20,
}


def init_session_state():
    defaults = {
        "messages": [
            {"role": "assistant", "content": "Hi! I can help you analyze the **Order to Cash** process."}
        ],
        "highlighted_nodes": [],
        "selected_node": None,
        "graph_data": {"nodes": [], "edges": []},
        "last_cypher": None,
        "show_node_detail": False,
        "node_detail_data": None,
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
            timeout=90,
        )
        return resp.json() if resp.ok else {"answer": "Request failed", "cypher_query": None, "highlighted_nodes": []}
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "cypher_query": None, "highlighted_nodes": []}


def build_agraph_data(graph_data: dict, highlighted: list = None, focus_nodes: list = None):
    """Build nodes and edges for agraph visualization."""
    highlighted = set(highlighted or [])
    focus_nodes = set(focus_nodes or [])
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
        
        # Highlight nodes from query results
        is_highlighted = nid in highlighted
        is_focused = nid in focus_nodes
        
        if is_highlighted or is_focused:
            color = "#dc2626"  # Red for highlighted
            size = int(size * 1.4)
        
        # Create tooltip with node info
        tooltip = f"{label}\n{name}"
        
        nodes.append(Node(
            id=nid,
            label=name[:15] + "..." if len(name) > 15 else name,
            size=size,
            color=color,
            title=tooltip,
            shape="dot",
            font={"size": 10, "color": "#475569"},
        ))
    
    for edge in graph_data.get("edges", []):
        src = edge["source"] if isinstance(edge["source"], str) else edge["source"]["id"]
        tgt = edge["target"] if isinstance(edge["target"], str) else edge["target"]["id"]
        rel = edge.get("relationship", "")
        
        if src in seen and tgt in seen:
            # Highlight edges connected to highlighted nodes
            is_highlighted_edge = (src in highlighted or tgt in highlighted)
            edge_color = "#ef4444" if is_highlighted_edge else "#94a3b8"
            edge_width = 2 if is_highlighted_edge else 1
            
            edges.append(Edge(
                source=src, 
                target=tgt, 
                color=edge_color,
                width=edge_width,
                title=rel,
            ))
    
    return nodes, edges


def render_legend():
    """Render the node type legend."""
    legend_items = [
        ("Customer", NODE_COLORS["Customer"]),
        ("SalesOrder", NODE_COLORS["SalesOrder"]),
        ("Delivery", NODE_COLORS["Delivery"]),
        ("Invoice", NODE_COLORS["BillingDocument"]),
        ("Journal", NODE_COLORS["JournalEntry"]),
        ("Payment", NODE_COLORS["Payment"]),
        ("Material", NODE_COLORS["Material"]),
        ("Plant", NODE_COLORS["Plant"]),
    ]
    
    items_html = "".join([
        f'<span class="legend-item"><span class="legend-dot" style="background:{color}"></span>{name}</span>'
        for name, color in legend_items
    ])
    items_html += '<span class="legend-item"><span class="legend-dot" style="background:#dc2626"></span>Highlighted</span>'
    
    st.markdown(f'<div class="legend">{items_html}</div>', unsafe_allow_html=True)


def render_node_detail_popup(node_id: str):
    """Render detailed node information in a popup-style card."""
    detail = fetch_node_detail(node_id)
    if not detail:
        return
    
    label = detail.get('label', 'Node')
    props = detail.get("properties", {})
    neighbors = detail.get("neighbors", [])
    
    st.markdown(f"""
    <div class="node-detail-card">
        <div class="node-detail-header">{label}</div>
        <div class="node-detail-entity">Entity: {label}</div>
    """, unsafe_allow_html=True)
    
    # Show all properties
    for key, value in props.items():
        if value is not None and value != "":
            display_value = str(value)
            if len(display_value) > 50:
                display_value = display_value[:50] + "..."
            st.markdown(f"""
            <div class="node-detail-row">
                <span class="node-detail-key">{key}:</span>
                <span class="node-detail-value">{display_value}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Show connections count
    if neighbors:
        st.markdown(f"""
        <div class="node-detail-footer">Connections: {len(neighbors)}</div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Expand and navigate buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Expand", key="expand_node", use_container_width=True):
            expansion = expand_node_api(node_id)
            if expansion.get("nodes"):
                existing = {n["id"] for n in st.session_state.graph_data.get("nodes", [])}
                for new in expansion["nodes"]:
                    if new["id"] not in existing:
                        st.session_state.graph_data["nodes"].append(new)
                st.session_state.graph_data["edges"].extend(expansion.get("edges", []))
                st.rerun()
    
    with col2:
        if st.button("✕ Close", key="close_detail", use_container_width=True):
            st.session_state.selected_node = None
            st.rerun()
    
    # Show connected nodes
    if neighbors:
        with st.expander(f"Connected Nodes ({len(neighbors)})", expanded=False):
            for n in neighbors[:8]:
                dir_icon = "→" if n["direction"] == "outgoing" else "←"
                btn_label = f"{dir_icon} {n['relationship']}: {n['name'][:20]}"
                if st.button(btn_label, key=f"nav_{n['id']}", use_container_width=True):
                    st.session_state.selected_node = n["id"]
                    st.rerun()


def send_message(message: str):
    """Send a message and get response."""
    st.session_state.messages.append({"role": "user", "content": message})
    
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-6:]]
    
    with st.spinner(""):
        response = chat_simple(message, history[:-1])
    
    answer = response.get("answer", "No response")
    cypher = response.get("cypher_query")
    highlighted = response.get("highlighted_nodes", [])
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "cypher": cypher,
    })
    
    # Update highlighted nodes and refresh graph to show them
    st.session_state.highlighted_nodes = highlighted
    
    # If we have highlighted nodes, add them to the graph if not present
    if highlighted:
        existing_ids = {n["id"] for n in st.session_state.graph_data.get("nodes", [])}
        for node_id in highlighted[:20]:  # Limit to first 20
            if node_id not in existing_ids:
                # Fetch and add the node
                parts = node_id.split("_", 1)
                label = parts[0] if len(parts) > 1 else "Node"
                name = parts[1] if len(parts) > 1 else node_id
                st.session_state.graph_data["nodes"].append({
                    "id": node_id,
                    "label": label,
                    "name": name,
                })
    
    st.rerun()


def main():
    init_session_state()
    
    # Health check
    health = check_api_health()
    if health.get("status") == "error":
        st.error(f"Backend unavailable: {health.get('message')}")
        st.code("cd backend && uvicorn app.main:app --reload")
        return
    
    # Top navigation
    st.markdown("""
    <div class="top-nav">
        <span class="nav-title">🔗 Mapping / <strong>Order to Cash</strong></span>
    </div>
    """, unsafe_allow_html=True)
    
    # Legend
    render_legend()
    
    # Main layout
    graph_col, chat_col = st.columns([2, 1], gap="small")
    
    # Graph Panel
    with graph_col:
        # Graph controls
        ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1, 1, 1, 3])
        with ctrl_col1:
            if st.button("↻ Reload", use_container_width=True):
                st.session_state.graph_data = fetch_graph_overview()
                st.session_state.highlighted_nodes = []
                st.rerun()
        with ctrl_col2:
            if st.button("✕ Clear", use_container_width=True):
                st.session_state.selected_node = None
                st.session_state.highlighted_nodes = []
                st.rerun()
        with ctrl_col3:
            minimize = st.checkbox("Minimize", value=False)
        with ctrl_col4:
            search_query = st.text_input("Search", placeholder="Search nodes...", label_visibility="collapsed")
        
        # Search results
        if search_query and len(search_query) >= 2:
            results = search_nodes(search_query)
            if results:
                st.markdown("**Search Results:**")
                for r in results[:5]:
                    if st.button(f"→ {r['name'][:30]} ({r['label']})", key=f"search_{r['id']}"):
                        st.session_state.selected_node = r["id"]
                        st.session_state.highlighted_nodes = [r["id"]]
                        st.rerun()
        
        # Load graph data if empty
        if not st.session_state.graph_data.get("nodes"):
            with st.spinner("Loading graph..."):
                st.session_state.graph_data = fetch_graph_overview()
        
        # Render graph
        if not minimize and st.session_state.graph_data.get("nodes"):
            nodes, edges = build_agraph_data(
                st.session_state.graph_data, 
                st.session_state.highlighted_nodes
            )
            
            config = Config(
                width="100%",
                height=550,
                directed=True,
                physics=True,
                hierarchical=False,
                nodeHighlightBehavior=True,
                highlightColor="#dc2626",
                collapsible=False,
            )
            
            selected = agraph(nodes=nodes, edges=edges, config=config)
            
            if selected and selected != st.session_state.selected_node:
                st.session_state.selected_node = selected
                st.rerun()
        
        # Show node detail if selected
        if st.session_state.selected_node:
            render_node_detail_popup(st.session_state.selected_node)
        
        # Show highlighted nodes info
        if st.session_state.highlighted_nodes:
            with st.expander(f"📍 Highlighted Nodes ({len(st.session_state.highlighted_nodes)})", expanded=False):
                for node_id in st.session_state.highlighted_nodes[:15]:
                    parts = node_id.split("_", 1)
                    label = parts[0] if len(parts) > 1 else "Node"
                    display_id = parts[1] if len(parts) > 1 else node_id
                    if st.button(f"{label}: {display_id}", key=f"hl_{node_id}"):
                        st.session_state.selected_node = node_id
                        st.rerun()
    
    # Chat Panel
    with chat_col:
        # Chat header
        st.markdown("""
        <div class="chat-header">
            <div class="chat-header-title">Chat with Graph</div>
            <div class="chat-header-title" style="font-size: 0.75rem; color: #94a3b8;">Order to Cash</div>
            <div class="chat-agent">
                <div class="chat-agent-avatar">D</div>
                <div>
                    <div class="chat-agent-name">Dodge AI</div>
                    <div class="chat-agent-role">Graph Agent</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Chat messages
        chat_container = st.container(height=400)
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message chat-message-user">
                        <div class="bubble">{msg["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    content = msg["content"].replace("\n", "<br>")
                    st.markdown(f"""
                    <div class="chat-message chat-message-assistant">
                        <div class="avatar">D</div>
                        <div class="bubble">{content}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show Cypher query if available
                    if msg.get("cypher"):
                        with st.expander("View Cypher Query", expanded=False):
                            st.code(msg["cypher"], language="cypher")
        
        # Chat input
        st.markdown("""
        <div class="chat-status">
            <span class="chat-status-dot"></span>
            Dodge AI is awaiting instructions
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder="Analyze anything",
                key="chat_input",
                label_visibility="collapsed",
            )
        with col2:
            if st.button("Send", type="primary", use_container_width=True):
                if user_input:
                    send_message(user_input)
        
        # Quick actions
        with st.expander("💡 Example Queries", expanded=False):
            examples = [
                "Show all customers with their orders",
                "Which orders are not delivered?",
                "Trace complete O2C flows",
                "Find broken/incomplete flows",
                "Top products by billing count",
                "Show cancelled invoices",
            ]
            for ex in examples:
                if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
                    send_message(ex)
        
        # Clear chat button
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": "Hi! I can help you analyze the **Order to Cash** process."}
            ]
            st.session_state.highlighted_nodes = []
            st.rerun()


if __name__ == "__main__":
    main()
