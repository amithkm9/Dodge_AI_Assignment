"""Data models for Dodge AI."""

from app.models.schemas import ChatRequest
from app.models.graph_models import NODE_COLORS, GRAPH_SCHEMA

__all__ = [
    "ChatRequest",
    "NODE_COLORS",
    "GRAPH_SCHEMA",
]
