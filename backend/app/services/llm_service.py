from openai import OpenAI
from app.config import settings
from app.models.graph_models import GRAPH_SCHEMA

SYSTEM_PROMPT = f"""You are a database assistant that translates natural language questions into Cypher queries for a Neo4j graph database containing SAP Order-to-Cash (O2C) business data.

{GRAPH_SCHEMA}

IMPORTANT RULES:
1. ONLY generate read-only Cypher queries (MATCH, RETURN, WITH, WHERE, ORDER BY, LIMIT).
2. NEVER use CREATE, DELETE, SET, REMOVE, MERGE, DROP, or DETACH.
3. Always use the exact property names and labels from the schema above.
4. For amounts/quantities, use toFloat() for comparisons.
5. Return meaningful fields, not just counts (unless specifically asked for counts).
6. Use LIMIT to cap results at 25 unless the user asks for more.
7. When joining Customer to SalesOrder, match on Customer.businessPartner = SalesOrder.soldToParty.
8. Delivery items link to sales orders via DeliveryItem.referenceSdDocument = SalesOrder.salesOrder.
9. Billing items link to deliveries via BillingItem.referenceSdDocument = Delivery.deliveryDocument.
10. BillingDocument links to JournalEntry via BillingDocument.accountingDocument = JournalEntry.accountingDocument.
11. JournalEntry links to Payment via the PAID_VIA relationship.
12. CRITICAL: If the user asks a generic question like "trace a flow" or "show a billing document" WITHOUT specifying an ID, return SAMPLE data by NOT filtering on a specific ID. Show multiple examples instead.
13. NEVER use placeholder values like 'YOUR_ID_HERE' or 'GIVEN_ID'. Either use a specific ID if provided, or return sample data.
14. ALWAYS include entity IDs in the RETURN clause for graph highlighting: c.businessPartner AS customerId, so.salesOrder, d.deliveryDocument AS delivery, b.billingDocument, j.accountingDocument AS journalEntry, p.accountingDocument AS payment, m.product AS material.

FEW-SHOT EXAMPLES:

Q: "Show me all customers and their total order amounts"
CYPHER: MATCH (c:Customer)-[:PLACED]->(so:SalesOrder) RETURN c.businessPartner AS customerId, c.customerName AS customer, count(so) AS orderCount, sum(toFloat(so.totalNetAmount)) AS totalAmount ORDER BY totalAmount DESC

Q: "Which orders have not been delivered yet?"
CYPHER: MATCH (so:SalesOrder) WHERE so.overallDeliveryStatus <> 'C' RETURN so.salesOrder, so.soldToParty AS customerId, so.totalNetAmount AS amount, so.creationDate AS date, so.overallDeliveryStatus AS deliveryStatus ORDER BY so.creationDate DESC LIMIT 25

Q: "Show me the complete order-to-cash flow for sales order 740506"
CYPHER: MATCH (c:Customer)-[:PLACED]->(so:SalesOrder {{salesOrder: '740506'}}) OPTIONAL MATCH (so)-[:FULFILLED_BY]->(d:Delivery) OPTIONAL MATCH (d)-[:BILLED_IN]->(b:BillingDocument) OPTIONAL MATCH (b)-[:POSTED_AS]->(j:JournalEntry) OPTIONAL MATCH (j)-[:PAID_VIA]->(p:Payment) RETURN c.businessPartner AS customerId, c.customerName AS customer, so.salesOrder, so.totalNetAmount AS orderAmount, d.deliveryDocument AS delivery, b.billingDocument, b.totalNetAmount AS invoiceAmount, j.accountingDocument AS journalEntry, p.accountingDocument AS payment, p.clearingDate AS paymentDate

Q: "Trace the full flow of a billing document" (generic - no specific ID given)
CYPHER: MATCH (c:Customer)-[:PLACED]->(so:SalesOrder)-[:FULFILLED_BY]->(d:Delivery)-[:BILLED_IN]->(b:BillingDocument) OPTIONAL MATCH (b)-[:POSTED_AS]->(j:JournalEntry) OPTIONAL MATCH (j)-[:PAID_VIA]->(p:Payment) RETURN c.businessPartner AS customerId, c.customerName AS customer, so.salesOrder, d.deliveryDocument AS delivery, b.billingDocument, b.totalNetAmount AS amount, j.accountingDocument AS journalEntry, p.accountingDocument AS payment LIMIT 10

Q: "Show complete O2C flows"
CYPHER: MATCH (c:Customer)-[:PLACED]->(so:SalesOrder)-[:FULFILLED_BY]->(d:Delivery)-[:BILLED_IN]->(b:BillingDocument)-[:POSTED_AS]->(j:JournalEntry)-[:PAID_VIA]->(p:Payment) RETURN c.businessPartner AS customerId, c.customerName AS customer, so.salesOrder, so.totalNetAmount AS orderAmount, d.deliveryDocument AS delivery, b.billingDocument, j.accountingDocument AS journalEntry, p.accountingDocument AS payment, p.clearingDate AS paymentDate LIMIT 10

Q: "What is the total revenue by customer?"
CYPHER: MATCH (c:Customer)-[:PLACED]->(so:SalesOrder) RETURN c.businessPartner AS customerId, c.customerName AS customer, count(so) AS orders, sum(toFloat(so.totalNetAmount)) AS totalRevenue ORDER BY totalRevenue DESC

Q: "Show cancelled invoices"
CYPHER: MATCH (b:BillingDocument) WHERE b.billingDocumentIsCancelled = true RETURN b.billingDocument, b.soldToParty AS customerId, b.totalNetAmount AS amount, b.billingDocumentDate AS date ORDER BY b.billingDocumentDate DESC LIMIT 25

Q: "Identify orders with broken or incomplete flows (delivered but not billed)"
CYPHER: MATCH (so:SalesOrder)-[:FULFILLED_BY]->(d:Delivery) WHERE NOT (d)-[:BILLED_IN]->(:BillingDocument) RETURN so.salesOrder, so.soldToParty AS customerId, so.totalNetAmount AS orderAmount, d.deliveryDocument AS delivery, so.overallDeliveryStatus AS deliveryStatus LIMIT 25

Q: "Which materials appear most frequently in sales orders?"
CYPHER: MATCH (soi:SalesOrderItem)-[:REFERENCES_MATERIAL]->(m:Material) RETURN m.product AS material, m.productDescription AS description, count(soi) AS frequency ORDER BY frequency DESC LIMIT 10
"""


class LLMService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def generate_cypher(self, question: str, conversation_history: list[dict] = None) -> str:
        """Step 1: Generate a Cypher query from a natural language question."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        messages.append({
            "role": "user",
            "content": f"Generate a Cypher query for this question. Return ONLY the Cypher query, no explanation:\n\n{question}",
        })

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0,
            max_tokens=500,
        )
        cypher = response.choices[0].message.content.strip()
        # Clean up markdown code blocks if present
        if cypher.startswith("```"):
            lines = cypher.split("\n")
            cypher = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        cypher = cypher.strip()
        # Remove "CYPHER:" prefix if present (from few-shot format)
        if cypher.upper().startswith("CYPHER:"):
            cypher = cypher[7:].strip()
        return cypher

    def generate_response(self, question: str, cypher: str, results: list[dict]) -> str:
        """Step 2: Generate a natural language response from query results."""
        if not results:
            return "No matching data was found for your query."

        # Truncate results for the prompt
        results_str = str(results[:50])
        if len(results_str) > 3000:
            results_str = results_str[:3000] + "... (truncated)"

        messages = [
            {
                "role": "system",
                "content": "You are a helpful business data analyst. Given a user question, the Cypher query that was executed, and the raw results, provide a clear, concise natural language answer. Format numbers nicely. Use tables for tabular data (markdown). Be factual - only state what the data shows.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nCypher Query: {cypher}\n\nResults ({len(results)} rows):\n{results_str}\n\nProvide a clear answer:",
            },
        ]

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()

    def stream_response(self, question: str, cypher: str, results: list[dict]):
        """Step 2 (streaming): Generate a streamed natural language response."""
        if not results:
            yield "No matching data was found for your query."
            return

        results_str = str(results[:50])
        if len(results_str) > 3000:
            results_str = results_str[:3000] + "... (truncated)"

        messages = [
            {
                "role": "system",
                "content": "You are a helpful business data analyst. Given a user question, the Cypher query that was executed, and the raw results, provide a clear, concise natural language answer. Format numbers nicely. Use tables for tabular data (markdown). Be factual - only state what the data shows.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nCypher Query: {cypher}\n\nResults ({len(results)} rows):\n{results_str}\n\nProvide a clear answer:",
            },
        ]

        stream = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def classify_relevance(self, question: str) -> bool:
        """Layer 2: LLM-based relevance classification."""
        messages = [
            {
                "role": "system",
                "content": """You are a strict classifier. Determine if a question is SPECIFICALLY about SAP Order-to-Cash business data.

RELEVANT topics (reply 'RELEVANT'):
- Sales orders, deliveries, invoices, billing documents
- Payments, journal entries, accounting documents  
- Customers, materials/products, plants
- Business flows, transactions, amounts, quantities

IRRELEVANT topics (reply 'IRRELEVANT'):
- General knowledge (geography, history, science)
- Creative writing (poems, stories, jokes)
- Personal questions, greetings, chitchat
- Anything not about SAP O2C business data

Reply with ONLY 'RELEVANT' or 'IRRELEVANT'.""",
            },
            {"role": "user", "content": question},
        ]
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=10,
        )
        return "RELEVANT" in response.choices[0].message.content.upper()


llm_service = LLMService()
