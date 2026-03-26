import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.services.neo4j_service import neo4j_service
from app.services.llm_service import llm_service
from app.services.guardrails import is_query_relevant, validate_cypher

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(request: ChatRequest):
    """Process a natural language query and return a streamed response."""
    question = request.message

    # Layer 1: Fast keyword check - if clearly off-topic, reject immediately
    relevant, rejection = is_query_relevant(question)
    if not relevant:
        # Reject off-topic queries (Layer 1 is authoritative)
        return StreamingResponse(
            _stream_error(rejection),
            media_type="text/event-stream",
        )

    async def event_stream():
        cypher = ""
        results = []
        try:
            # Step 1: Generate Cypher
            cypher = llm_service.generate_cypher(question, request.conversation_history)

            # Send the cypher query as a metadata event
            yield f"data: {json.dumps({'type': 'cypher', 'content': cypher})}\n\n"

            # Layer 3: Validate Cypher
            valid, error = validate_cypher(cypher)
            if not valid:
                yield f"data: {json.dumps({'type': 'error', 'content': error})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Step 2: Execute Cypher
            try:
                results = neo4j_service.run_query(cypher)
            except Exception as e:
                error_msg = str(e)
                yield f"data: {json.dumps({'type': 'error', 'content': f'Query execution error: {error_msg}'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Send result count
            yield f"data: {json.dumps({'type': 'result_count', 'content': len(results)})}\n\n"

            # Extract node IDs for highlighting
            highlighted = _extract_node_ids(results)
            if highlighted:
                yield f"data: {json.dumps({'type': 'highlights', 'content': highlighted})}\n\n"

            # Step 3: Stream natural language response
            for chunk in llm_service.stream_response(question, cypher, results):
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/simple")
async def chat_simple(request: ChatRequest):
    """Non-streaming chat endpoint for simpler clients."""
    question = request.message

    # Layer 1: Fast keyword check - if clearly off-topic, reject immediately
    relevant, rejection = is_query_relevant(question)
    if not relevant:
        # Layer 2: LLM classification as second opinion (but trust Layer 1 more)
        try:
            if not llm_service.classify_relevance(question):
                return {"answer": rejection, "cypher_query": None, "raw_results": None, "highlighted_nodes": []}
            # Even if LLM says relevant, if Layer 1 strongly rejected, still reject
            # (LLM can be fooled by creative phrasing)
        except Exception:
            pass
        # If we get here, Layer 1 said no but LLM said yes - still reject for safety
        return {"answer": rejection, "cypher_query": None, "raw_results": None, "highlighted_nodes": []}

    try:
        cypher = llm_service.generate_cypher(question, request.conversation_history)
        valid, error = validate_cypher(cypher)
        if not valid:
            return {"answer": error, "cypher_query": cypher, "raw_results": None, "highlighted_nodes": []}

        results = neo4j_service.run_query(cypher)
        answer = llm_service.generate_response(question, cypher, results)
        highlighted = _extract_node_ids(results)

        return {
            "answer": answer,
            "cypher_query": cypher,
            "raw_results": results[:50],
            "highlighted_nodes": highlighted,
        }
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "cypher_query": None, "raw_results": None, "highlighted_nodes": []}


def _extract_node_ids(results: list[dict]) -> list[str]:
    """Extract node IDs from query results for graph highlighting.
    
    Maps result fields to graph node IDs in format: Label_id
    """
    ids = []
    
    # Fields that contain actual IDs (not names)
    # Include both simple names and qualified names (e.g., "so.salesOrder")
    id_fields = {
        # Sales Order IDs
        "salesOrder": "SalesOrder",
        "so.salesOrder": "SalesOrder",
        "order": "SalesOrder",
        "orderId": "SalesOrder",
        # Delivery IDs
        "delivery": "Delivery",
        "deliveryDocument": "Delivery",
        "d.deliveryDocument": "Delivery",
        "deliveryId": "Delivery",
        # Billing/Invoice IDs
        "invoice": "BillingDocument",
        "billingDocument": "BillingDocument",
        "b.billingDocument": "BillingDocument",
        "invoiceId": "BillingDocument",
        # Journal Entry IDs
        "journalEntry": "JournalEntry",
        "j.accountingDocument": "JournalEntry",
        "accountingDocument": "JournalEntry",
        # Payment IDs
        "payment": "Payment",
        "p.accountingDocument": "Payment",
        "paymentId": "Payment",
        "clearingDocument": "Payment",
        # Customer IDs (businessPartner is the actual ID)
        "customerId": "Customer",
        "c.businessPartner": "Customer",
        "businessPartner": "Customer",
        "soldToParty": "Customer",
        # Material IDs
        "product": "Material",
        "material": "Material",
        "m.product": "Material",
        "materialId": "Material",
        # Plant IDs
        "plant": "Plant",
        "plantId": "Plant",
        "productionPlant": "Plant",
        "shippingPoint": "Plant",
    }
    
    for row in results[:25]:
        for field, label in id_fields.items():
            if field in row and row[field]:
                value = row[field]
                # Skip if value looks like a name (contains spaces or commas) for Customer
                if label == "Customer" and (isinstance(value, str) and (" " in value or "," in value)):
                    continue
                ids.append(f"{label}_{value}")
    
    return list(set(ids))


async def _stream_error(message: str):
    yield f"data: {json.dumps({'type': 'text', 'content': message})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
