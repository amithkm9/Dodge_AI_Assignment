# Cursor — Project Summary

**Project:** Dodge AI — SAP O2C Graph Explorer  
**Model:** claude--sonnet--4.6
**Exported:** 2026-03-26

---

## Session 1 — Data Exploration & Schema Design

### How tools were used

Used the shell to inspect raw JSONL records before writing any code. Ran `head -n 2` across the key files to read field names and understand how entities link together. The goal was to decide the graph schema from the data, not impose one upfront.

Cursor read the sample records and reasoned about which fields were join keys. The question was whether the SalesOrder → Delivery link existed at the header level or only at the item level.

Answer from the data: `DeliveryItem.referenceSdDocument = SalesOrder.salesOrder` — the link is item-level in SAP. Cursor suggested modelling both the derived header edge (`SalesOrder-[:FULFILLED_BY]->Delivery`) and the item-level edge (`DeliveryItem-[:FULFILLS_ITEM]->SalesOrderItem`) to support both high-level flow traversal and granular traceability.

### Key prompts / workflows

**Prompt:** "I have SAP O2C JSONL files — sales orders, deliveries, billing docs, journal entries, payments, customers, materials, plants. Where do I start?"

Cursor's approach: understand the join keys first, then define the schema. Key findings from inspecting the data:
- `SalesOrder.soldToParty` → matches `Customer.businessPartner`
- `DeliveryItem.referenceSdDocument` → matches `SalesOrder.salesOrder`
- `BillingItem.referenceSdDocument` → matches `Delivery.deliveryDocument`
- `BillingDocument.accountingDocument` → matches `JournalEntry.accountingDocument`
- `JournalEntry` → `Payment` via `PAID_VIA` relationship in the journal entries data

**Prompt:** "Should `soldToParty` on SalesOrder be a property or an edge to Customer?"

Decision: make it an edge — `(Customer)-[:PLACED]->(SalesOrder)`. Reasoning: as a property it's a string you can filter on, but as a relationship you can traverse the entire O2C chain from a customer node in a single Cypher path query. This makes customer-centric queries like "find all overdue invoices for this customer" trivial.

Same logic applied to `(BillingDocument)-[:SOLD_TO]->(Customer)` — useful for the reverse direction.

Final schema settled on:
- **12 node types:** Customer, SalesOrder, SalesOrderItem, Delivery, DeliveryItem, BillingDocument, BillingItem, JournalEntry, Payment, Material, Plant, Address
- **17 relationships** covering the full chain: `PLACED`, `HAS_ITEM`, `REFERENCES_MATERIAL`, `PRODUCED_AT`, `FULFILLED_BY`, `FULFILLS_ITEM`, `SHIPPED_FROM`, `STORED_AT`, `BILLED_IN`, `BILLS_ITEM`, `POSTED_AS`, `PAID_VIA`, `SOLD_TO`, `LOCATED_AT`

---

## Session 2 — Backend Build

### How tools were used

Cursor scaffolded the full directory structure, then wrote each file. Shell was used to start Neo4j via Docker, run the seed script, and test the FastAPI endpoints with `curl`. Each component was tested in isolation before wiring them together.

### Key prompts / workflows

**Prompt:** "Scaffold the FastAPI backend."

Directory structure proposed and created:
```
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   ├── chat.py        ← NL query endpoint
│   │   └── graph.py       ← graph data / viz endpoints
│   ├── services/
│   │   ├── neo4j_service.py
│   │   ├── llm_service.py
│   │   └── guardrails.py
│   ├── models/
│   │   ├── schemas.py
│   │   └── graph_models.py  ← schema string for LLM prompt
│   └── data/
│       ├── ingestion.py
│       └── seed.py
└── requirements.txt
```

Neo4j service used lazy initialization — the driver isn't created until first use, so import doesn't blow up if Neo4j isn't running yet. The `/api/health` endpoint calls `neo4j_service.run_query("RETURN 1")` to check connectivity and returns `{"status": "healthy", "neo4j": "connected"}` or `{"status": "degraded", ...}` with the error.

**Prompt:** "Make the seed script idempotent — running it twice shouldn't create duplicates."

Used `MERGE` on each node's unique identifier. Created indexes on the merge keys first:
```cypher
CREATE INDEX customer_bp IF NOT EXISTS FOR (c:Customer) ON (c.businessPartner)
CREATE INDEX salesorder_id IF NOT EXISTS FOR (s:SalesOrder) ON (s.salesOrder)
```
Without the indexes, `MERGE` does a full scan on each call — that's what caused the performance issue below.

### Debugging / iteration

**Issue — seed script took 45+ minutes:**  
Was doing one Cypher statement per row (one `session.run()` per record). Each call has network round-trip overhead to Neo4j. Fixed with `UNWIND` batching:
```python
session.run("UNWIND $rows AS row MERGE (so:SalesOrder {salesOrder: row.salesOrder}) SET so += row", rows=batch)
```
Batch size of 500. Total seeding time dropped from ~45 minutes to under 2 minutes.

**Prompt:** "How should I structure the LLM prompt for Cypher generation?"

Two-stage pipeline:
- **Stage 1 — Cypher generation:** System prompt with full schema + 15 few-shot examples. `temperature=0` for determinism — same question always produces the same query. User message is just the question. Return only the raw Cypher string.
- **Stage 2 — Response generation:** Different system prompt with a "data analyst" persona. Passes question + Cypher + raw results. `temperature=0.2` — slightly warmer so phrasing feels natural, but still grounded.

The schema is defined as a constant in `graph_models.py` and interpolated into the system prompt f-string. One node type change → one file update.

Key prompt rules that prevented most edge case failures:
1. Read-only only — never `CREATE`, `DELETE`, `MERGE`, `SET`, `DROP`, `DETACH`
2. Use exact property names from schema
3. Use `toFloat()` for numeric comparisons
4. Dates are stored as strings `'YYYY-MM-DD'` — use string comparison or `STARTS WITH`, never `date()` arithmetic
5. For generic queries without a specific ID, return sample data — never use placeholder IDs like `'YOUR_ID_HERE'`
6. Always include entity IDs in `RETURN` clause for graph highlighting (`c.businessPartner AS customerId`, `so.salesOrder`, etc.)

The few-shot examples cover: customer aggregations, path traversals, filter by status, date queries, "broken flow" detection (delivered but not billed), top products by billing count.

**Issue — date query failure:**  
For "show orders from last month", the model generated:
```cypher
WHERE so.creationDate >= date() - duration({months: 1})
```
Neo4j doesn't support that syntax for string-stored dates. Added explicit rule: "For 'recent' / 'last month' queries, order by date DESC and limit results. Do NOT use `date()` arithmetic." Added matching few-shot example. The pragmatic solution — returning the most recently created records — is actually what users want anyway.

**Issue — markdown code block in Cypher output:**  
The model sometimes returned:
```
```cypher
MATCH (so:SalesOrder) RETURN so
```
```
Added a post-processing cleanup step:
```python
if cypher.startswith("```"):
    lines = cypher.split("\n")
    cypher = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
# Also strip "CYPHER:" prefix that bleeds through from few-shot format
if cypher.upper().startswith("CYPHER:"):
    cypher = cypher[7:].strip()
```

**Prompt:** "Add 3-layer guardrails: fast keyword check, LLM classification, Cypher validation."

- **Layer 1 — keyword check:** `DOMAIN_KEYWORDS` list (order, delivery, invoice, billing, payment, etc.) vs `OFF_TOPIC_KEYWORDS` list (poem, joke, recipe, weather, etc.). Short queries with digits pass (likely document IDs). Fast — no LLM call needed.
- **Layer 2 — LLM classification:** Uses `gpt-4o-mini` (cheap, fast) — only invoked when Layer 1 is uncertain. Strict classifier prompt returns only `"RELEVANT"` or `"IRRELEVANT"`. Layer 1 result always wins for safety — LLM can be fooled by creative phrasing.
- **Layer 3 — Cypher validation:** Regex check for destructive keywords (`DELETE`, `DROP`, `MERGE`, `SET`, `CALL`, etc.). Also checks response isn't an LLM refusal ("sorry, I cannot..."). Must contain `MATCH` or `RETURN`.

---

## Session 3 — Frontend Build

### How tools were used

Cursor wrote the Next.js component structure and API client. Issues were surfaced through browser errors and console logs. The hydration error required two iterations to fully fix.

### Key prompts / workflows

**Prompt:** "What's the best library for the force-directed graph visualization?"

`react-force-graph-2d` — canvas-based (not SVG), handles hundreds of nodes without frame drops, built-in zoom/pan/drag, `forwardRef` support for imperative zoom control.

**Issue — SSR hydration error:**  
```
Error: Hydration failed because the initial UI does not match what was rendered on the server.
```
`react-force-graph-2d` accesses `window` on import. Adding `ssr: false` to the `ForceGraph2D` dynamic import wasn't enough — the parent component was still SSR-rendered. Fixed by dynamically importing the entire `GraphVisualization` component from `page.tsx`:
```tsx
const GraphVisualization = dynamic(
  () => import("@/components/GraphVisualization"),
  { ssr: false }
);
```
This ensures the whole component tree that touches `window` is client-only.

**Prompt:** "Write the `nodeCanvasObject` callback — different colors per node type, larger when highlighted, glow effect."

- Colors defined in a `NODE_COLORS` map (12 entries, one per label)
- `NODE_SIZES` map for base sizes per type (Customer = 6, items = 3, etc.)
- Glow effect via `ctx.shadowColor` + `ctx.shadowBlur` — wrapped in `ctx.save()` / `ctx.restore()` to prevent bleeding into adjacent nodes
- Labels shown only at `globalScale > 1.2` or when highlighted — keeps graph clean at default zoom
- White background pill behind labels using `ctx.roundRect()`

**Issue — highlighted nodes not turning red:**  
Nodes were glowing in their type color instead of red. The issue: `node.color` was set in a `useEffect` when building `processedNodes`, but was still using `NODE_COLORS[node.label]`. Fixed by checking `highlightSet.has(node.id)` during the map and assigning `"#dc2626"` directly:
```tsx
color: highlightSet.has(node.id) ? "#dc2626" : NODE_COLORS[node.label] || "#64748b",
size: highlightSet.has(node.id) ? baseSize * 1.8 : baseSize,
```
The `ctx.shadowColor = node.color` then naturally becomes red for highlighted nodes.

**Prompt:** "AI responses are showing as raw text — markdown tables aren't rendering."

Wrote a custom inline markdown renderer. Key parts:
- `renderInline(text)` — handles `**bold**` by splitting on the pattern and wrapping in `<strong>`
- `renderContent(content)` — line-by-line parser that detects table blocks (lines starting and ending with `|`) and renders them as styled HTML tables with striped rows
- Separator row detection: checks if second row matches `/^[\|\-\s:]+$/`

**Issue — collapsed table rows:**  
The backend sometimes returned table rows collapsed onto one line: `| A | B | | C | D |`. The table parser was treating it as one row. Fixed with a normalization step before parsing:
```tsx
const normalised = content
  .replace(/\| \|/g, "|\n|")
  .replace(/\|\s*\n\s*\|/g, "|\n|");
```

**Prompt:** "Implement focus mode — filter graph to only highlighted nodes, auto-zoom."

`focusedNodes` and `focusedEdges` computed with `useMemo`:
```tsx
const focusedNodes = useMemo(() => {
  if (!focusMode || highlightedNodes.length === 0) return nodes;
  const set = new Set(highlightedNodes);
  return nodes.filter((n) => set.has(n.id));
}, [nodes, highlightedNodes, focusMode]);
```
`forwardRef` + `useImperativeHandle` exposes `zoomToFit()` from `GraphVisualization` to the parent. Auto-zoom only triggers when `highlighted_nodes.length <= 20` — above that the view is too crowded.

**Issue — zoom doesn't re-expand when toggling focus off:**  
`zoomToFit()` was running before React had re-rendered with the full node set. Fixed:
```tsx
const handleToggleFocusMode = useCallback(() => {
  setFocusMode((prev) => !prev);
  setTimeout(() => graphRef.current?.zoomToFit(), 100);
}, []);
```

**Prompt:** "Switch to streaming SSE — response should appear word by word."

Consumed SSE stream with `ReadableStream` reader. Event types: `cypher`, `highlights`, `result_count`, `text` (chunks), `done`, `error`. Buffer incomplete lines across chunks using a rolling buffer. Each `text` chunk appended to `streamedText`, assistant message updated in place.

**Issue — streaming flicker:**  
A `"..."` placeholder message was briefly visible before the first chunk arrived. Checking `last.content !== "..."` to identify the message to update was fragile (unicode ellipsis vs three dots). Fixed with an `isStreaming: boolean` flag on the `Message` type. The streaming message is found with `findLastIndex(m => m.isStreaming)` and updated in place. On `done`, the flag is cleared.

**Prompt:** "Add a stop button to cancel the ongoing request."

`AbortController` ref in `abortControllerRef`. On stop: `abortControllerRef.current.abort()`. Fetch receives the `signal`. Error handler checks `err.name !== "AbortError"` before showing an error message — aborts are intentional and shouldn't show as errors.

---

## Session 4 — Node Highlighting & Polish

### How tools were used

Console logs to compare ID formats between graph nodes and backend response. Prompt additions for edge case query patterns. Iterative UI changes with hot reload.

### Debugging / iteration

**Issue — highlighting broken after query:**  
Backend returned `highlighted_nodes: ["Customer_310000108"]` but nothing highlighted. Added:
```tsx
console.log("Graph node IDs:", nodes.slice(0, 5).map(n => n.id));
console.log("Highlighted:", response.highlighted_nodes);
```
Graph had `"Customer_310000108"` but the backend list had `"Customer_310000108.0"`. Neo4j was returning `businessPartner` as a float. Fixed in `_extract_node_ids`:
```python
if isinstance(value, float) and value.is_integer():
    value = str(int(value))
else:
    value = str(value)
```
Also fixed upstream in the seed script to cast all ID fields to `str` when loading from JSONL.

**Issue — "what's going on with order 740506" only returns the SalesOrder node:**  
Model was generating `MATCH (so:SalesOrder {salesOrder: '740506'}) RETURN so` instead of a full flow trace. Added a few-shot example mapping "what's going on with / tell me about X" to a full `OPTIONAL MATCH` chain across all 6 entity types. Also added instruction: "When a user asks about a specific document by ID without specifying what they want, assume they want the full O2C flow trace."

**Key prompt / workflows**

**Prompt:** "Should I include Cypher queries in the conversation history passed to the LLM?"

Decision: no — only natural language content. Two reasons: (1) Cypher is verbose and burns token budget, (2) for follow-up query generation the model needs to know the prior topic, not the prior implementation. History slice:
```tsx
const history = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }));
```

**UI polish implemented:**
- Header split to mirror 60/40 layout — left breadcrumb, right Dodge AI identity with live status dot (green "Online" / amber pulsing "Thinking…")
- Suggested questions hidden after first user message: `messages.length <= 1 && !isLoading`
- "View Cypher Query" collapsible under each AI response — `openCypher: number | null` state, one expanded at a time, dark terminal style with green monospace font
- Node popup: fetches node detail on open, shows all properties, "Expand Node" button to load neighbors into graph

---

## Session 5 — Deployment & Code Review

### How tools were used

Read all config and deployment files to audit what was actually used. Ran linter after edits. Checked startup traceback to find the `__init__.py` import crash.

### Key prompts / workflows

**Prompt:** "Check all files — remove what's not necessary."

Read the full project tree and every config file. Files removed:
- `docker-compose.prod.yml` — broken (referenced non-existent `frontend/Dockerfile`, used Streamlit port 8501 from an earlier prototype)
- `render.yaml` — same issue (non-existent `frontend/Dockerfile`)
- `railway.toml` — Railway-specific, not needed for Vercel + Render deployment
- Root `.env.example` — duplicate of `backend/.env.example`, had outdated Streamlit `API_BASE` comment
- `frontend/public/next.svg` — default Next.js placeholder, Grep confirmed it wasn't imported anywhere
- `cursor-transcript.md` — added to `.gitignore` instead of deleting

**Prompt:** "Review all code files — check coding standards, readability."

Read all backend and frontend source files in parallel batches. Used Grep to confirm which exports were actually imported (found `searchNodes` in `api.ts` was exported but never imported anywhere — dead code). Ran linter after each batch of edits to catch regressions immediately.

**Security fixes:**
- `graph.py` was interpolating the `label` portion of a URL path parameter directly into Cypher strings: `f"MATCH (n:{label})"`. Added `VALID_NODE_LABELS` set and `_validate_node_id()` guard that returns HTTP 400 for any label not in the allowlist.
- All `HTTPException(500, detail=str(e))` calls were leaking internal error messages to clients. Replaced with generic messages + `logger.exception()` so the detail stays in server logs only.

**DRY / code quality fixes:**
- `generate_response` and `stream_response` in `llm_service.py` had identical 10-line message-building blocks copy-pasted. Extracted into `_build_analyst_messages(question, cypher, results)`.
- `guardrails.py` had a redundant `entity_patterns` check — every keyword in it was already in `DOMAIN_KEYWORDS`, so the second loop could never fire independently. Removed.
- `except Exception: pass` in `chat_simple` was silently swallowing LLM classification errors. Replaced with `logger.warning()`.
- `schemas.py` had 5 unused Pydantic models (`ChatResponse`, `GraphNode`, `GraphEdge`, `GraphData`, `NodeDetail`) never wired to any `response_model=`. Removed.
- `config.py` had `class Config` inner class (pydantic v1 style). Upgraded to `model_config = SettingsConfigDict(env_file=".env")`. Removed stale Streamlit ports (8501, 8502) and `"*"` wildcard from default `cors_origins`.

**Frontend fixes:**
- `Message` interface was copy-pasted identically in `page.tsx` and `ChatPanel.tsx`. Extracted to `src/types/index.ts`, both files import from there.
- `renderInline`, `parseRow`, `renderContent` were inside the `ChatPanel` component body with no dependency on state — recreated on every render. Moved to module level.
- `void isSep` was suppressing an unused-variable warning for a function that was never called. Removed both.
- `searchNodes` in `api.ts` exported but never imported — removed.
- `highlightSet` in `GraphVisualization.tsx` was `new Set(highlightedNodes)` on every render. Wrapped in `useMemo`.
- `useRef<any>` for `fgRef` replaced with `useRef<ForceGraphMethods | undefined>` using the library's exported type.
- Removed `typeof window !== "undefined"` guard around `ForceGraph2D` — the component is `"use client"` so it's always true.
- `handleMinimize` and `handleToggleOverlay` in `page.tsx` were plain arrow functions while every other handler used `useCallback`. Made consistent.

### Debugging / iteration

**Issue — backend crash after removing unused Pydantic models:**
```
ImportError: cannot import name 'ChatResponse' from 'app.models.schemas'
```
`models/__init__.py` was still re-exporting the deleted models. Fixed the `__init__.py` to only import `ChatRequest`. This was caught immediately from the startup traceback when restarting uvicorn.

**Issue — TypeScript error after fixing `fgRef` type:**  
`useRef<ForceGraphMethods | null>(null)` gave a type mismatch — `ForceGraph2D` expects `MutableRefObject<ForceGraphMethods | undefined>` but `useRef(null)` produces `RefObject<T | null>`. Fixed by switching the initializer from `null` to `undefined`:
```tsx
const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
```

**Issue — Next.js startup warnings after next.config.ts cleanup:**  
```
⚠ `eslint` configuration in next.config.ts is no longer supported.
⚠ Unrecognized key(s) in object: 'eslint'
```
The `eslint` and `typescript` keys in `next.config.ts` were removed in Next.js 16. Cleaned the config down to an empty `NextConfig` object.

**Final state — both services running:**
- Frontend: http://localhost:3000 (Next.js 16, Turbopack)
- Backend: http://localhost:8000 (FastAPI + uvicorn --reload)
- Neo4j: bolt://localhost:7687 (Docker)
- API docs: http://localhost:8000/docs

---

## Session 6 — Cloud Deployment

### Stack

| Layer | Service | URL |
|-------|---------|-----|
| Frontend (Next.js) | Vercel | https://dodge-ai-assignment-alpha.vercel.app |
| Backend (FastAPI) | Render (Free) | https://dodge-ai-backend-3y5k.onrender.com |
| Database (Neo4j) | Aura Free | `neo4j+s://9e5f3d2d.databases.neo4j.io` |

### How tools were used

Checked git remotes to confirm the repo was already on GitHub (`amithkm9/Dodge_AI_Assignment`). Inspected `render.yaml` and `railway.toml` to understand existing deployment config. Read `backend/app/config.py` and `backend/app/data/seed.py` to understand how credentials and data directory are consumed.

### Deployment steps

**Step 1 — Neo4j Aura (cloud database)**

Created a free AuraDB instance at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura). Wrote credentials into `backend/.env` (gitignored). Ran the seed script locally pointed at the cloud instance:

```bash
cd backend
python -m app.data.seed --data-dir ../sap-o2c-data
```

Seeding completed in ~5 seconds. Final node counts:
- BillingItem: 245, SalesOrderItem: 167, BillingDocument: 163
- DeliveryItem: 137, JournalEntry: 123, SalesOrder: 100
- Delivery: 86, Payment: 76, Material: 69, Plant: 44, Customer: 8, Address: 8

**Step 2 — Render (backend)**

Connected GitHub repo on [render.com](https://render.com). Set runtime to Docker, root directory to `backend`. Added 5 environment variables: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `OPENAI_API_KEY`, `CORS_ORIGINS=["*"]`. Render built the Dockerfile and deployed. Backend live in ~4 minutes.

**Step 3 — Vercel (frontend)**

Imported GitHub repo on [vercel.com](https://vercel.com). Set root directory to `frontend`. Added env var `NEXT_PUBLIC_API_BASE=https://dodge-ai-backend-3y5k.onrender.com`.

### Issues & fixes

**Issue — Vercel build failed: `Module not found: Can't resolve '@/lib/api'`**

`frontend/src/lib/api.ts` was never committed to git. Root cause: `.gitignore` had a bare `lib/` entry (copied from a Python boilerplate template) that matched `frontend/src/lib/`. Fixed by scoping it:

```diff
- lib/
- lib64/
+ backend/lib/
+ backend/lib64/
```

Committed `frontend/src/lib/api.ts` alongside the `.gitignore` fix and pushed.

**Issue — Vercel build failed: `No Output Directory named 'public' found`**

Vercel didn't auto-detect Next.js because the Application Preset was blank during project setup (root directory was set to `frontend`, which confused the detector). Fixed by adding `frontend/vercel.json`:

```json
{
  "framework": "nextjs"
}
```

Next deployment succeeded in 32 seconds.

### Notes

- Render free tier spins down after 15 minutes of inactivity — first request after idle takes 30–50 seconds (cold start). Acceptable for a demo.
- `CORS_ORIGINS=["*"]` is set on the backend for simplicity. For production, restrict to the Vercel domain.

---

*— End of transcript —*
