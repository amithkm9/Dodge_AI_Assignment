# Dodge AI - SAP Order-to-Cash Graph Explorer

A graph-based data modeling and query system that allows users to explore SAP Order-to-Cash (O2C) data through natural language queries and interactive graph visualization.

## Live Demo

🔗 **Demo URL**: *Deploy using instructions below to create your own instance*

> **Note**: This application requires an OpenAI API key and Neo4j database. See [Deployment](#deployment) section for hosting options.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [LLM Prompting Strategy](#llm-prompting-strategy)
- [Guardrails](#guardrails)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [API Reference](#api-reference)

---

## Overview

Dodge AI transforms fragmented SAP O2C transactional data into an interconnected graph, enabling users to:

- **Explore relationships** between orders, deliveries, invoices, and payments visually
- **Query data naturally** using plain English questions
- **Trace document flows** from sales order to payment
- **Identify anomalies** like broken or incomplete business flows

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Interactive Graph** | Force-directed 2D graph visualization with node expansion and relationship inspection |
| **NL → Cypher** | Natural language queries translated to Cypher in real-time |
| **Focus Mode** | Automatically filters graph to show only query-relevant nodes and edges |
| **Node Highlighting** | Query results highlight relevant nodes in red with visual emphasis |
| **Conversation Memory** | Context maintained across last 6 messages for follow-up queries |
| **Guardrails** | Three-layer protection rejects off-topic queries with helpful messages |

### Graph Visualization Features

| Feature | Description |
|---------|-------------|
| **Node Expansion** | Click any node to see its properties and expand to neighbors |
| **Color-Coded Entities** | 12 distinct colors for different entity types (Customer, Order, Delivery, etc.) |
| **Focus Mode Toggle** | Filter graph to show only highlighted nodes from query results |
| **Auto-Zoom** | Graph automatically zooms to fit focused nodes after query |
| **Clear Highlights** | One-click button to clear all highlights and return to full graph |

### Chat Interface Features

| Feature | Description |
|---------|-------------|
| **Suggested Questions** | Pre-built queries to help users get started |
| **Cypher Query Disclosure** | Expandable view to see the generated Cypher query |
| **Markdown Tables** | Results displayed in formatted tables |
| **Loading Indicators** | Visual feedback during query processing |
| **Stop Generation** | Ability to cancel in-progress queries |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DODGE AI SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────────────┐      ┌─────────────────┐      ┌─────────────────┐     │
│   │    Next.js     │      │    FastAPI      │      │     Neo4j       │     │
│   │   Frontend     │─────▶│    Backend      │─────▶│   Graph DB      │     │
│   │  (Port 3000)   │◀─────│  (Port 8000)    │◀─────│  (Port 7687)    │     │
│   └────────────────┘      └────────┬────────┘      └─────────────────┘     │
│                                    │                                        │
│                                    ▼                                        │
│                           ┌─────────────────┐                               │
│                           │   OpenAI API    │                               │
│                           │   (GPT-4o)      │                               │
│                           └─────────────────┘                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Graph Database** | Neo4j | Native graph storage with Cypher query language; ideal for traversing O2C relationships |
| **Backend** | FastAPI | Async support, automatic OpenAPI docs, Pydantic validation |
| **Frontend** | Next.js 16 + React 19 | Modern React framework with App Router, server components |
| **Graph Viz** | react-force-graph-2d | High-performance 2D force-directed graph on canvas |
| **Styling** | Tailwind CSS v4 | Utility-first CSS for rapid UI development |
| **LLM** | GPT-4o | Best-in-class for code generation (Cypher) with low latency |

### Project Structure

```
dodge-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Environment configuration
│   │   ├── routers/
│   │   │   ├── chat.py          # /api/chat endpoints (NL query)
│   │   │   └── graph.py         # /api/graph endpoints (CRUD)
│   │   ├── services/
│   │   │   ├── neo4j_service.py # Graph database operations
│   │   │   ├── llm_service.py   # OpenAI integration
│   │   │   └── guardrails.py    # Query validation & safety
│   │   ├── models/
│   │   │   ├── schemas.py       # Pydantic request/response models
│   │   │   └── graph_models.py  # Graph schema definition
│   │   └── data/
│   │       ├── ingestion.py     # JSONL data loading
│   │       └── seed.py          # Neo4j database seeding
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout
│   │   │   ├── page.tsx         # Main application page
│   │   │   └── globals.css      # Global styles
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx    # Chat interface component
│   │   │   ├── GraphVisualization.tsx  # Force graph component
│   │   │   └── NodePopup.tsx    # Node detail popup
│   │   └── lib/
│   │       └── api.ts           # API client functions
│   ├── package.json
│   └── next.config.ts
├── sap-o2c-data/                 # Dataset (JSONL files)
├── docker-compose.yml            # Neo4j orchestration
└── README.md
```

---

## Data Model

### Graph Schema

The SAP O2C data is modeled as a property graph with the following structure:

```
                        ┌─────────────┐
                        │   Customer  │
                        │  (BP ID)    │
                        └──────┬──────┘
                               │ PLACED
                               ▼
    ┌─────────┐         ┌─────────────┐         ┌─────────────┐
    │ Material│◀────────│ SalesOrder  │────────▶│   Plant     │
    │         │ REF_MAT │  (SO ID)    │ PROD_AT │             │
    └─────────┘         └──────┬──────┘         └─────────────┘
                               │ FULFILLED_BY
                               ▼
                        ┌─────────────┐
                        │  Delivery   │──────────▶ Plant (SHIPPED_FROM)
                        │  (DL ID)    │
                        └──────┬──────┘
                               │ BILLED_IN
                               ▼
                        ┌─────────────┐
                        │  Billing    │──────────▶ Customer (SOLD_TO)
                        │  Document   │
                        └──────┬──────┘
                               │ POSTED_AS
                               ▼
                        ┌─────────────┐
                        │ JournalEntry│
                        │  (Acct Doc) │
                        └──────┬──────┘
                               │ PAID_VIA
                               ▼
                        ┌─────────────┐
                        │   Payment   │
                        │  (Clear Doc)│
                        └─────────────┘
```

### Node Types (12 Entity Types)

| Node Label | Primary Key | Key Properties |
|------------|-------------|----------------|
| Customer | businessPartner | customerName, category, isBlocked |
| SalesOrder | salesOrder | soldToParty, totalNetAmount, overallDeliveryStatus |
| SalesOrderItem | salesOrder + salesOrderItem | material, requestedQuantity, netAmount |
| Delivery | deliveryDocument | shippingPoint, overallGoodsMovementStatus |
| DeliveryItem | deliveryDocument + deliveryDocumentItem | actualDeliveryQuantity, plant |
| BillingDocument | billingDocument | totalNetAmount, billingDocumentIsCancelled |
| BillingItem | billingDocument + billingDocumentItem | billingQuantity, netAmount |
| JournalEntry | accountingDocument | postingDate, amountInTransactionCurrency |
| Payment | accountingDocument | clearingDate, amountInTransactionCurrency |
| Material | product | productDescription, productType |
| Plant | plant | plantName, salesOrganization |
| Address | businessPartner + addressId | cityName, country, region |

### Relationships (17 Relationship Types)

| Relationship | From | To | Description |
|--------------|------|-----|-------------|
| PLACED | Customer | SalesOrder | Customer places an order |
| HAS_ITEM | SalesOrder/Delivery/Billing | Item nodes | Header contains line items |
| REFERENCES_MATERIAL | SalesOrderItem | Material | Item references a product |
| PRODUCED_AT | SalesOrderItem | Plant | Production plant assignment |
| FULFILLED_BY | SalesOrder | Delivery | Order fulfilled by delivery |
| FULFILLS_ITEM | DeliveryItem | SalesOrderItem | Line-item level fulfillment |
| SHIPPED_FROM | Delivery | Plant | Shipping point |
| STORED_AT | DeliveryItem | Plant | Storage location |
| BILLED_IN | Delivery | BillingDocument | Delivery billed in invoice |
| BILLS_ITEM | BillingItem | DeliveryItem | Line-item level billing |
| POSTED_AS | BillingDocument | JournalEntry | Invoice posted to accounting |
| PAID_VIA | JournalEntry | Payment | Journal entry cleared by payment |
| SOLD_TO | BillingDocument | Customer | Invoice sold-to party |
| LOCATED_AT | Customer | Address | Customer address |

---

## LLM Prompting Strategy

### Two-Stage Architecture

The system uses a **two-stage LLM pipeline**:

```
User Question → [Stage 1: Cypher Generation] → Cypher Query
                                                    ↓
                                              Neo4j Execution
                                                    ↓
Query Results → [Stage 2: Response Generation] → Natural Language Answer
```

### Stage 1: Cypher Generation

**System Prompt Design:**

1. **Schema Context**: Full graph schema provided (node labels, properties, relationships)
2. **Safety Rules**: Only read-only operations (MATCH, RETURN, WITH, WHERE)
3. **Few-Shot Examples**: 15+ curated examples covering common query patterns
4. **Edge Case Handling**: Instructions for generic queries (return samples, not placeholders)
5. **Date Handling**: Special rules for date-based queries using string comparison

```python
SYSTEM_PROMPT = """You are a database assistant that translates natural language 
questions into Cypher queries for a Neo4j graph database containing SAP O2C data.

{GRAPH_SCHEMA}

IMPORTANT RULES:
1. ONLY generate read-only Cypher queries (MATCH, RETURN, WITH, WHERE, ORDER BY, LIMIT)
2. NEVER use CREATE, DELETE, SET, REMOVE, MERGE, DROP, or DETACH
3. Always use the exact property names from the schema
4. For amounts/quantities, use toFloat() for comparisons
5. DATE HANDLING: Dates are stored as strings in format 'YYYY-MM-DD'. 
   For "recent" queries, order by date DESC and limit results.
...

FEW-SHOT EXAMPLES:
Q: "Show me all customers and their total order amounts"
CYPHER: MATCH (c:Customer)-[:PLACED]->(so:SalesOrder) 
        RETURN c.businessPartner AS customerId, c.customerName AS customer, 
               count(so) AS orderCount, sum(toFloat(so.totalNetAmount)) AS totalAmount 
        ORDER BY totalAmount DESC
...
"""
```

### Stage 2: Response Generation

The second LLM call takes:
- Original user question
- Generated Cypher query
- Raw query results (truncated to 50 rows / 3000 chars)

And produces a natural language answer with:
- Factual statements grounded in data
- Formatted tables for tabular results
- Numeric formatting for amounts

### Key Prompting Decisions

| Decision | Rationale |
|----------|-----------|
| **Temperature 0 for Cypher** | Deterministic query generation |
| **Temperature 0.2 for Response** | Slight creativity for natural phrasing |
| **Few-shot over fine-tuning** | Faster iteration, no training data needed |
| **Schema in prompt** | Model always has current schema context |
| **Entity ID aliasing** | Consistent field names for node highlighting |

---

## Guardrails

### Three-Layer Protection

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│  Layer 1: Keyword Check (Fast)      │  ← Domain keywords present?
└─────────────────────────────────────┘
    │ No match
    ▼
┌─────────────────────────────────────┐
│  Layer 2: LLM Classification        │  ← Is query business-related?
└─────────────────────────────────────┘
    │ Irrelevant
    ▼
┌─────────────────────────────────────┐
│  Layer 3: Cypher Validation         │  ← Safe query? No mutations?
└─────────────────────────────────────┘
    │
    ▼
Execute Query
```

### Layer 1: Fast Keyword Check

```python
DOMAIN_KEYWORDS = [
    "order", "sales", "delivery", "invoice", "billing", "payment", "customer",
    "material", "product", "plant", "journal", "amount", "quantity", "shipped",
    "cancelled", "total", "revenue", "net", "gross", "outstanding", "overdue",
    "fulfilled", "pending", "status", "created", "sap", "o2c", "order-to-cash",
    "trace", "flow", "document", "incomplete", "broken", "unpaid", "cleared",
    ...
]

OFF_TOPIC_KEYWORDS = [
    "poem", "story", "joke", "movie", "song", "recipe", "game", "sport",
    "capital of", "president of", "weather", "celebrity", "news", "politics",
    ...
]
```

### Layer 2: LLM Classification

For queries that pass keyword check but seem ambiguous, a lightweight LLM call (gpt-4o-mini) classifies relevance.

### Layer 3: Cypher Validation

```python
DESTRUCTIVE_PATTERNS = [
    r"\bDELETE\b", r"\bDROP\b", r"\bDETACH\b", r"\bREMOVE\b",
    r"\bSET\b", r"\bCREATE\b", r"\bMERGE\b", r"\bCALL\b",
]
```

### Rejection Examples

| User Query | Layer | Response |
|------------|-------|----------|
| "Write me a poem" | 1 | "I can only answer questions about the SAP Order-to-Cash dataset..." |
| "How do I cook pasta?" | 1 | "I can only answer questions about the SAP Order-to-Cash dataset..." |
| "What's the weather today?" | 1 | "I can only answer questions about the SAP Order-to-Cash dataset..." |

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- OpenAI API key

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/dodge-ai.git
cd dodge-ai
```

### 2. Start Neo4j

```bash
docker-compose up -d neo4j
```

### 3. Configure Backend Environment

```bash
cd backend
cp .env.example .env
# Edit .env with your configuration:
# - OPENAI_API_KEY=your-key-here
# - NEO4J_URI=bolt://localhost:7687
# - NEO4J_USER=neo4j
# - NEO4J_PASSWORD=your-password
# - DATA_DIR=../sap-o2c-data
```

### 4. Install Backend Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 5. Seed the Database

```bash
python -m app.data.seed --data-dir ../sap-o2c-data
```

### 6. Start the Backend

```bash
uvicorn app.main:app --reload
```

### 7. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 8. Configure Frontend Environment

```bash
# Create .env.local
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
```

### 9. Start the Frontend

```bash
npm run dev
```

### 10. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474

---

## Deployment

### Option 1: Docker Compose (Recommended for VMs)

Deploy all services with a single command:

```bash
# Set environment variables
export OPENAI_API_KEY=your-key-here
export NEO4J_PASSWORD=your-secure-password

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Seed the database (first time only)
docker-compose -f docker-compose.prod.yml exec backend python -m app.data.seed --data-dir /app/data/raw
```

### Option 2: Render

1. Fork this repository
2. Connect to Render
3. Use the `render.yaml` blueprint
4. Set environment variables:
   - `OPENAI_API_KEY`
   - `NEO4J_URI` (use Aura or hosted Neo4j)
   - `NEO4J_PASSWORD`

### Option 3: Railway

1. Connect repository to Railway
2. Add Neo4j plugin or use external Neo4j (Aura)
3. Set environment variables in Railway dashboard
4. Deploy using `railway.toml` configuration

### Neo4j Hosting Options

- **Neo4j Aura** (Recommended): Free tier available at https://neo4j.com/cloud/aura/
- **Self-hosted**: Use the included docker-compose configuration
- **Cloud providers**: AWS, GCP, Azure all offer Neo4j marketplace images

---

## Usage

### Example Queries

| Query | What it does |
|-------|--------------|
| "Show me all customers and their total order amounts" | Aggregates revenue by customer |
| "Which orders have not been delivered yet?" | Finds orders with incomplete delivery status |
| "Trace the full flow of sales order 740506" | Shows complete O2C path for specific order |
| "Identify orders with broken flows" | Finds delivered-but-not-billed or billed-without-delivery |
| "Which products are associated with the highest number of billing documents?" | Product billing frequency analysis |
| "Show cancelled invoices" | Lists all cancelled billing documents |
| "Find payments that cleared recently" | Shows recent payment activity |
| "Which plant handles the most deliveries?" | Plant workload analysis |

### Graph Interaction

1. **Click nodes** to inspect properties in the popup
2. **Expand nodes** to see connected entities
3. **Focus Mode** automatically activates when query returns ≤20 nodes
4. **Toggle Focus Mode** to switch between filtered and full graph view
5. **Clear button** removes all highlights and returns to full graph

### Focus Mode

When you ask a query like "Trace the flow for sales order 740506":
- The graph automatically filters to show only the relevant nodes (Customer → Order → Delivery → etc.)
- Non-relevant nodes are hidden
- The view auto-zooms to fit the focused subgraph
- Click "Show All" to see the full graph while keeping highlights
- Click "Clear" to remove all highlights

---

## API Reference

### Chat Endpoints

#### POST /api/chat
Streaming chat endpoint for natural language queries (SSE).

```json
{
  "message": "Show me all customers",
  "conversation_history": []
}
```

Response: Server-Sent Events stream with events:
- `cypher`: The generated Cypher query
- `result_count`: Number of results
- `highlights`: Node IDs to highlight
- `text`: Response text chunks
- `done`: Stream complete

#### POST /api/chat/simple
Non-streaming chat endpoint.

Request:
```json
{
  "message": "Show me all customers",
  "conversation_history": []
}
```

Response:
```json
{
  "answer": "Here are the customers...",
  "cypher_query": "MATCH (c:Customer) RETURN c.customerName LIMIT 25",
  "raw_results": [...],
  "highlighted_nodes": ["Customer_310000108", "Customer_310000109"]
}
```

### Graph Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/graph/overview | GET | Get graph overview for visualization |
| /api/graph/node/{id} | GET | Get node details and neighbors |
| /api/graph/expand/{id} | GET | Expand node to get connected nodes |
| /api/graph/search?q={query} | GET | Search nodes by name/ID |
| /api/graph/stats | GET | Get node and relationship counts |

### Health Check

#### GET /api/health
```json
{
  "status": "healthy",
  "neo4j": "connected"
}
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Backend Unavailable" | Ensure backend is running: `cd backend && uvicorn app.main:app --reload` |
| "Neo4j not connected" | Check Neo4j is running: `docker-compose up -d neo4j` |
| OpenAI "proxies" error | Downgrade httpx: `pip install httpx==0.27.2` |
| Empty graph | Run database seed: `python -m app.data.seed --data-dir ../sap-o2c-data` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | Yes | Your OpenAI API key |
| NEO4J_URI | Yes | Neo4j connection URI (e.g., bolt://localhost:7687) |
| NEO4J_USER | Yes | Neo4j username (default: neo4j) |
| NEO4J_PASSWORD | Yes | Neo4j password |
| DATA_DIR | No | Path to SAP O2C data (default: ../sap-o2c-data) |
| OPENAI_MODEL | No | OpenAI model to use (default: gpt-4o) |

---

## License

MIT License - See LICENSE file for details.
