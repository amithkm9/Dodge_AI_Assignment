import logging
from fastapi import APIRouter, HTTPException
from app.services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])

VALID_NODE_LABELS = {
    "Customer", "SalesOrder", "SalesOrderItem",
    "Delivery", "DeliveryItem",
    "BillingDocument", "BillingItem",
    "JournalEntry", "Payment",
    "Material", "Plant", "Address",
}


def _validate_node_id(node_id: str) -> str:
    """Validate node_id format and return the label portion."""
    parts = node_id.split("_", 1)
    if len(parts) != 2 or parts[0] not in VALID_NODE_LABELS:
        raise HTTPException(status_code=400, detail=f"Invalid node ID: '{node_id}'")
    return parts[0]


@router.get("/overview")
async def get_overview():
    """Get high-level overview graph for initial visualization."""
    try:
        return neo4j_service.get_overview_graph()
    except Exception:
        logger.exception("Failed to fetch overview graph")
        raise HTTPException(status_code=500, detail="Failed to fetch graph overview")


@router.get("/node/{node_id}")
async def get_node(node_id: str):
    """Get detailed information about a specific node."""
    _validate_node_id(node_id)
    try:
        return neo4j_service.get_node_detail(node_id)
    except Exception:
        logger.exception("Failed to fetch node detail for %s", node_id)
        raise HTTPException(status_code=500, detail="Failed to fetch node details")


@router.get("/expand/{node_id}")
async def expand_node(node_id: str):
    """Expand a node to see its connected nodes."""
    _validate_node_id(node_id)
    try:
        return neo4j_service.expand_node(node_id)
    except Exception:
        logger.exception("Failed to expand node %s", node_id)
        raise HTTPException(status_code=500, detail="Failed to expand node")


@router.get("/search")
async def search_nodes(q: str = ""):
    """Search nodes by property values."""
    if not q or len(q) < 2:
        return []
    try:
        return neo4j_service.search_nodes(q)
    except Exception:
        logger.exception("Failed to search nodes for query '%s'", q)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/stats")
async def get_stats():
    """Get graph statistics."""
    try:
        stats = {}
        for label in VALID_NODE_LABELS - {"SalesOrderItem", "DeliveryItem", "BillingItem", "Address"}:
            result = neo4j_service.run_query(f"MATCH (n:{label}) RETURN count(n) AS count")
            stats[label] = result[0]["count"] if result else 0
        rel_count = neo4j_service.run_query("MATCH ()-[r]->() RETURN count(r) AS count")
        stats["totalRelationships"] = rel_count[0]["count"] if rel_count else 0
        return stats
    except Exception:
        logger.exception("Failed to fetch graph stats")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")
