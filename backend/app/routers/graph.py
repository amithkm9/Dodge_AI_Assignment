from fastapi import APIRouter, HTTPException
from app.services.neo4j_service import neo4j_service

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/overview")
async def get_overview():
    """Get high-level overview graph for initial visualization."""
    try:
        data = neo4j_service.get_overview_graph()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/{node_id}")
async def get_node(node_id: str):
    """Get detailed information about a specific node."""
    try:
        detail = neo4j_service.get_node_detail(node_id)
        return detail
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expand/{node_id}")
async def expand_node(node_id: str):
    """Expand a node to see its connected nodes."""
    try:
        data = neo4j_service.expand_node(node_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_nodes(q: str = ""):
    """Search nodes by property values."""
    if not q or len(q) < 2:
        return []
    try:
        results = neo4j_service.search_nodes(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get graph statistics."""
    try:
        stats = {}
        labels = ["Customer", "SalesOrder", "Delivery", "BillingDocument", "JournalEntry", "Payment", "Material", "Plant"]
        for label in labels:
            result = neo4j_service.run_query(f"MATCH (n:{label}) RETURN count(n) AS count")
            stats[label] = result[0]["count"] if result else 0
        rel_count = neo4j_service.run_query("MATCH ()-[r]->() RETURN count(r) AS count")
        stats["totalRelationships"] = rel_count[0]["count"] if rel_count else 0
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
