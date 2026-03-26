import re

DOMAIN_KEYWORDS = [
    "order", "sales", "delivery", "invoice", "billing", "payment", "customer",
    "material", "product", "plant", "journal", "amount", "quantity", "shipped",
    "cancelled", "total", "revenue", "net", "gross", "outstanding", "overdue",
    "fulfilled", "pending", "status", "created", "sap", "o2c", "order-to-cash", 
    "trace", "flow", "document", "incomplete", "broken", "unpaid", "cleared", 
    "posted", "billed", "sold", "purchased", "transaction", "account",
]

OFF_TOPIC_KEYWORDS = [
    # Creative/entertainment
    "poem", "story", "joke", "movie", "song", "recipe", "game", "sport",
    # General knowledge
    "capital of", "president of", "weather", "celebrity", "news", "politics",
    "religion", "philosophy", "history of", "population of", "currency of",
    # Educational
    "explain how", "teach me", "how to cook", "translate", "define",
    # Creative requests
    "write me", "create a", "generate a", "compose", "make up",
    # General questions
    "what is the meaning", "who invented", "who is the", "what year was",
    "where is the country", "which country", "how old is",
    # Greetings
    "hello", "hi there", "good morning", "good evening", "how are you",
    # Math/science
    "calculate", "solve", "equation", "formula",
]

DESTRUCTIVE_PATTERNS = [
    r"\bDELETE\b", r"\bDROP\b", r"\bDETACH\b", r"\bREMOVE\b",
    r"\bSET\b", r"\bCREATE\b", r"\bMERGE\b", r"\bCALL\b",
]

OFF_TOPIC_RESPONSE = (
    "I can only answer questions about the SAP Order-to-Cash dataset. "
    "This includes sales orders, deliveries, billing documents, payments, "
    "customers, materials, and plants. Please ask a question related to this data."
)


def is_query_relevant(query: str) -> tuple[bool, str | None]:
    """Layer 1: Fast keyword-based relevance check."""
    query_lower = query.lower().strip()
    
    # Check for obvious off-topic queries first (higher priority)
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in query_lower:
            return False, OFF_TOPIC_RESPONSE
    
    # Check for domain keywords
    for kw in DOMAIN_KEYWORDS:
        if kw in query_lower:
            return True, None
    
    # Short queries with numbers might be IDs (e.g., "740506", "SO-123")
    if len(query.split()) <= 3 and any(c.isdigit() for c in query):
        return True, None
    
    # Queries asking about specific entities
    entity_patterns = ["customer", "order", "delivery", "invoice", "billing", "payment", "material", "plant"]
    if any(ep in query_lower for ep in entity_patterns):
        return True, None
    
    # Default: reject queries without domain context
    return False, OFF_TOPIC_RESPONSE


def validate_cypher(cypher: str) -> tuple[bool, str | None]:
    """Layer 3: Validate generated Cypher is safe to execute."""
    if not cypher or not cypher.strip():
        return False, "Empty query generated."

    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, cypher, re.IGNORECASE):
            return False, "Query contains forbidden operation."

    # Check if LLM returned a refusal/apology instead of Cypher
    refusal_indicators = ["sorry", "cannot", "can't", "unable", "i'm not able", "outside"]
    cypher_lower = cypher.lower()
    if any(indicator in cypher_lower for indicator in refusal_indicators):
        return False, "This system is designed to answer questions related to the SAP Order-to-Cash dataset only. Try asking about orders, deliveries, invoices, payments, customers, or materials."

    # Must contain MATCH or RETURN
    if not re.search(r"\bMATCH\b|\bRETURN\b", cypher, re.IGNORECASE):
        return False, "This system is designed to answer questions related to the SAP Order-to-Cash dataset only. Try asking about orders, deliveries, invoices, payments, customers, or materials."

    return True, None
