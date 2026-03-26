# Dodge AI - SAP Order-to-Cash Graph Explorer

A graph-based data modeling and query system that allows users to explore SAP Order-to-Cash (O2C) data through natural language queries and interactive graph visualization.

## Live Demo

🔗 **Demo URL**: *Deploy using instructions below to create your own instance*

> **Note**: This application requires an OpenAI API key and Neo4j database. See [Deployment](#deployment) section for hosting options.

## Table of Contents

- [Overview](#overview)
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

### Key Features

| Feature | Description |
|---------|-------------|
| **Interactive Graph** | Visual exploration with node expansion and relationship inspection |
| **NL → Cypher** | Natural language queries translated to Cypher in real-time |
| **Streaming Responses** | LLM responses streamed for better UX |
| **Node Highlighting** | Query results highlight relevant nodes in the graph |
| **Conversation Memory** | Context maintained across multiple queries |
| **Guardrails** | Off-topic queries rejected with helpful messages |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DODGE AI SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────────────┐      ┌─────────────────┐      ┌─────────────────┐     │
│   │   Streamlit    │      │    FastAPI      │      │     Neo4j       │     │
│   │   Frontend     │─────▶│    Backend      │─────▶│   Graph DB      │     │
│   │  (Port 8501)   │◀─────│  (Port 8000)    │◀─────│  (Port 7687)    │     │
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
| **Frontend** | Streamlit | Rapid prototyping, built-in components, easy deployment |
| **LLM** | GPT-4o | Best-in-class for code generation (Cypher) with low latency |
| **Graph Viz** | streamlit-agraph | Interactive graph visualization within Streamlit |

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
│   ├── streamlit_app.py         # Streamlit UI application
│   └── requirements.txt
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

### Node Types

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

### Relationships

| Relationship | From | To | Description |
|--------------|------|-----|-------------|
| PLACED | Customer | SalesOrder | Customer places an order |
| HAS_ITEM | SalesOrder/Delivery/Billing | Item nodes | Header contains line items |
| REFERENCES_MATERIAL | SalesOrderItem | Material | Item references a product |
| PRODUCED_AT | SalesOrderItem | Plant | Production plant assignment |
| FULFILLED_BY | SalesOrder | Delivery | Order fulfilled by delivery |
| SHIPPED_FROM | Delivery | Plant | Shipping point |
| BILLED_IN | Delivery | BillingDocument | Delivery billed in invoice |
| POSTED_AS | BillingDocument | JournalEntry | Invoice posted to accounting |
| PAID_VIA | JournalEntry | Payment | Journal entry cleared by payment |
| SOLD_TO | BillingDocument | Customer | Invoice sold-to party |

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
3. **Few-Shot Examples**: 10+ curated examples covering common query patterns
4. **Edge Case Handling**: Instructions for generic queries (return samples, not placeholders)

```python
SYSTEM_PROMPT = """You are a database assistant that translates natural language 
questions into Cypher queries for a Neo4j graph database containing SAP O2C data.

{GRAPH_SCHEMA}

IMPORTANT RULES:
1. ONLY generate read-only Cypher queries (MATCH, RETURN, WITH, WHERE, ORDER BY, LIMIT)
2. NEVER use CREATE, DELETE, SET, REMOVE, MERGE, DROP, or DETACH
3. Always use the exact property names from the schema
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
    ...
]

def is_query_relevant(query: str) -> tuple[bool, str | None]:
    query_lower = query.lower()
    if any(kw in query_lower for kw in DOMAIN_KEYWORDS):
        return True, None
    if len(query.split()) <= 3:  # Short queries might be IDs
        return True, None
    return False, "This system is designed to answer questions related to the provided dataset only."
```

### Layer 2: LLM Classification

For queries that fail keyword check, a lightweight LLM call classifies relevance:

```python
def classify_relevance(question: str) -> bool:
    messages = [
        {"role": "system", "content": "Classify if question is related to business data. Reply 'RELEVANT' or 'IRRELEVANT'."},
        {"role": "user", "content": question}
    ]
    response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0)
    return "RELEVANT" in response.choices[0].message.content.upper()
```

### Layer 3: Cypher Validation

```python
DESTRUCTIVE_PATTERNS = [
    r"\bDELETE\b", r"\bDROP\b", r"\bDETACH\b", r"\bREMOVE\b",
    r"\bSET\b", r"\bCREATE\b", r"\bMERGE\b", r"\bCALL\b",
]

def validate_cypher(cypher: str) -> tuple[bool, str | None]:
    # Check for destructive operations
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, cypher, re.IGNORECASE):
            return False, "Query contains forbidden operation."
    
    # Check for LLM refusals disguised as queries
    refusal_indicators = ["sorry", "cannot", "can't", "unable"]
    if any(indicator in cypher.lower() for indicator in refusal_indicators):
        return False, "Query outside dataset scope."
    
    # Must be a valid read query
    if not re.search(r"\bMATCH\b|\bRETURN\b", cypher, re.IGNORECASE):
        return False, "Invalid query format."
    
    return True, None
```

### Rejection Examples

| User Query | Layer | Response |
|------------|-------|----------|
| "Write me a poem" | 1 | "This system is designed to answer questions related to the provided dataset only." |
| "What's the weather today?" | 2 | "This system is designed to answer questions related to the provided dataset only." |
| "DELETE all customers" | 3 | "Query contains forbidden operation." |

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/dodge-ai.git
cd dodge-ai
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

### 3. Start Neo4j

```bash
docker-compose up -d neo4j
```

### 4. Seed the Database

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m app.data.seed --data-dir ../sap-o2c-data
```

### 5. Start the Backend

```bash
uvicorn app.main:app --reload
```

### 6. Start the Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### 7. Access the Application

- **Frontend**: http://localhost:8501
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

### Option 4: Streamlit Cloud + External Backend

1. Deploy backend to any cloud provider (Railway, Render, Fly.io)
2. Deploy frontend to Streamlit Cloud:
   - Connect GitHub repository
   - Set `API_BASE` secret to your backend URL
   - Main file: `frontend/streamlit_app.py`

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
| "Trace the full flow of billing document 90001234" | Shows complete O2C path for specific invoice |
| "Identify orders with broken flows" | Finds delivered-but-not-billed or billed-without-delivery |
| "Which materials appear most frequently?" | Product popularity analysis |
| "Show cancelled invoices" | Lists all cancelled billing documents |

### Graph Interaction

1. **Click nodes** to inspect properties
2. **Expand nodes** to see connected entities
3. **Search** by ID or name in sidebar
4. **Highlighted nodes** show query results

---

## API Reference

### Chat Endpoints

#### POST /api/chat
Streaming chat endpoint for natural language queries.

```json
{
  "message": "Show me all customers",
  "conversation_history": []
}
```

Response: Server-Sent Events stream

#### POST /api/chat/simple
Non-streaming chat endpoint.

Response:
```json
{
  "answer": "Here are the customers...",
  "cypher_query": "MATCH (c:Customer) RETURN c.customerName LIMIT 25",
  "highlighted_nodes": ["Customer_1000001", "Customer_1000002"]
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

## License

MIT License - See LICENSE file for details.
