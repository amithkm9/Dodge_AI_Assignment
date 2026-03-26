from neo4j import GraphDatabase
from app.config import settings
from app.models.graph_models import NODE_COLORS


class Neo4jService:
    def __init__(self):
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()

    def run_query(self, cypher: str, params: dict = None) -> list[dict]:
        with self.driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]

    def get_overview_graph(self) -> dict:
        """Get a high-level overview graph with all main entities and relationships."""
        nodes = []
        edges = []
        seen_nodes = set()

        # Get customers with their order counts
        records = self.run_query("""
            MATCH (c:Customer)
            OPTIONAL MATCH (c)-[:PLACED]->(so:SalesOrder)
            RETURN c.businessPartner AS id, c.customerName AS name,
                   labels(c)[0] AS label, count(so) AS orderCount
        """)
        for r in records:
            nid = f"Customer_{r['id']}"
            if nid not in seen_nodes:
                nodes.append({
                    "id": nid, "label": "Customer",
                    "name": r["name"] or r["id"],
                    "properties": {"businessPartner": r["id"], "orders": r["orderCount"]},
                    "color": NODE_COLORS["Customer"],
                })
                seen_nodes.add(nid)

        # Get sales orders
        records = self.run_query("""
            MATCH (so:SalesOrder)
            RETURN so.salesOrder AS id, so.totalNetAmount AS amount,
                   so.soldToParty AS customer, so.creationDate AS date,
                   so.overallDeliveryStatus AS deliveryStatus
            LIMIT 200
        """)
        for r in records:
            nid = f"SalesOrder_{r['id']}"
            if nid not in seen_nodes:
                nodes.append({
                    "id": nid, "label": "SalesOrder",
                    "name": f"SO-{r['id']}",
                    "properties": {"salesOrder": r["id"], "amount": r["amount"], "date": r["date"]},
                    "color": NODE_COLORS["SalesOrder"],
                })
                seen_nodes.add(nid)
            cid = f"Customer_{r['customer']}"
            if cid in seen_nodes:
                edges.append({"source": cid, "target": nid, "relationship": "PLACED"})

        # Get deliveries linked to sales orders
        records = self.run_query("""
            MATCH (so:SalesOrder)-[:FULFILLED_BY]->(d:Delivery)
            RETURN d.deliveryDocument AS id, d.creationDate AS date,
                   d.overallGoodsMovementStatus AS status,
                   so.salesOrder AS salesOrder
            LIMIT 200
        """)
        for r in records:
            nid = f"Delivery_{r['id']}"
            if nid not in seen_nodes:
                nodes.append({
                    "id": nid, "label": "Delivery",
                    "name": f"DL-{r['id']}",
                    "properties": {"deliveryDocument": r["id"], "date": r["date"], "status": r["status"]},
                    "color": NODE_COLORS["Delivery"],
                })
                seen_nodes.add(nid)
            soid = f"SalesOrder_{r['salesOrder']}"
            if soid in seen_nodes:
                edges.append({"source": soid, "target": nid, "relationship": "FULFILLED_BY"})

        # Get billing documents linked to deliveries
        records = self.run_query("""
            MATCH (d:Delivery)-[:BILLED_IN]->(b:BillingDocument)
            RETURN b.billingDocument AS id, b.totalNetAmount AS amount,
                   b.billingDocumentIsCancelled AS cancelled,
                   d.deliveryDocument AS delivery
            LIMIT 200
        """)
        for r in records:
            nid = f"BillingDocument_{r['id']}"
            if nid not in seen_nodes:
                nodes.append({
                    "id": nid, "label": "BillingDocument",
                    "name": f"INV-{r['id']}",
                    "properties": {"billingDocument": r["id"], "amount": r["amount"], "cancelled": r["cancelled"]},
                    "color": NODE_COLORS["BillingDocument"],
                })
                seen_nodes.add(nid)
            did = f"Delivery_{r['delivery']}"
            if did in seen_nodes:
                edges.append({"source": did, "target": nid, "relationship": "BILLED_IN"})

        # Get journal entries linked to billing documents
        records = self.run_query("""
            MATCH (b:BillingDocument)-[:POSTED_AS]->(j:JournalEntry)
            RETURN j.accountingDocument AS id, j.amountInTransactionCurrency AS amount,
                   j.postingDate AS date, b.billingDocument AS billing
            LIMIT 200
        """)
        for r in records:
            nid = f"JournalEntry_{r['id']}"
            if nid not in seen_nodes:
                nodes.append({
                    "id": nid, "label": "JournalEntry",
                    "name": f"JE-{r['id']}",
                    "properties": {"accountingDocument": r["id"], "amount": r["amount"], "date": r["date"]},
                    "color": NODE_COLORS["JournalEntry"],
                })
                seen_nodes.add(nid)
            bid = f"BillingDocument_{r['billing']}"
            if bid in seen_nodes:
                edges.append({"source": bid, "target": nid, "relationship": "POSTED_AS"})

        # Get payments linked to journal entries
        records = self.run_query("""
            MATCH (j:JournalEntry)-[:PAID_VIA]->(p:Payment)
            RETURN p.accountingDocument AS id, p.amountInTransactionCurrency AS amount,
                   p.clearingDate AS date, j.accountingDocument AS journal
            LIMIT 200
        """)
        for r in records:
            nid = f"Payment_{r['id']}"
            if nid not in seen_nodes:
                nodes.append({
                    "id": nid, "label": "Payment",
                    "name": f"PAY-{r['id']}",
                    "properties": {"accountingDocument": r["id"], "amount": r["amount"], "date": r["date"]},
                    "color": NODE_COLORS["Payment"],
                })
                seen_nodes.add(nid)
            jid = f"JournalEntry_{r['journal']}"
            if jid in seen_nodes:
                edges.append({"source": jid, "target": nid, "relationship": "PAID_VIA"})

        return {"nodes": nodes, "edges": edges}

    def get_node_detail(self, node_id: str) -> dict:
        """Get a node and its immediate neighbors."""
        # node_id format: "Label_id"
        parts = node_id.split("_", 1)
        if len(parts) != 2:
            return {"id": node_id, "label": "Unknown", "properties": {}, "neighbors": []}

        label, raw_id = parts

        # Get node properties
        records = self.run_query(f"""
            MATCH (n:{label})
            WHERE n.{self._id_field(label)} = $id
            RETURN n, labels(n) AS labels
        """, {"id": raw_id})

        if not records:
            return {"id": node_id, "label": label, "properties": {}, "neighbors": []}

        props = dict(records[0]["n"])
        neighbors = []

        # Get connected nodes
        neighbor_records = self.run_query(f"""
            MATCH (n:{label})-[r]-(m)
            WHERE n.{self._id_field(label)} = $id
            RETURN type(r) AS relationship, labels(m)[0] AS neighborLabel, m AS neighbor,
                   CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END AS direction
            LIMIT 50
        """, {"id": raw_id})

        for nr in neighbor_records:
            n_props = dict(nr["neighbor"])
            n_label = nr["neighborLabel"]
            n_id_field = self._id_field(n_label)
            n_raw_id = str(n_props.get(n_id_field, "unknown"))
            neighbors.append({
                "id": f"{n_label}_{n_raw_id}",
                "label": n_label,
                "relationship": nr["relationship"],
                "direction": nr["direction"],
                "name": self._node_name(n_label, n_props),
                "color": NODE_COLORS.get(n_label, "#6366f1"),
            })

        return {
            "id": node_id,
            "label": label,
            "properties": props,
            "neighbors": neighbors,
        }

    def expand_node(self, node_id: str) -> dict:
        """Expand a node: return its neighbors as graph data."""
        detail = self.get_node_detail(node_id)
        nodes = []
        edges = []

        for n in detail["neighbors"]:
            nodes.append({
                "id": n["id"], "label": n["label"],
                "name": n["name"],
                "properties": {},
                "color": n["color"],
            })
            if n["direction"] == "outgoing":
                edges.append({"source": node_id, "target": n["id"], "relationship": n["relationship"]})
            else:
                edges.append({"source": n["id"], "target": node_id, "relationship": n["relationship"]})

        return {"nodes": nodes, "edges": edges}

    def search_nodes(self, query: str) -> list[dict]:
        """Search nodes by property values."""
        results = []
        searches = [
            ("Customer", "customerName", "businessPartner"),
            ("SalesOrder", "salesOrder", "salesOrder"),
            ("Delivery", "deliveryDocument", "deliveryDocument"),
            ("BillingDocument", "billingDocument", "billingDocument"),
            ("Material", "productDescription", "product"),
            ("Plant", "plantName", "plant"),
            ("Payment", "accountingDocument", "accountingDocument"),
        ]
        for label, search_field, id_field in searches:
            records = self.run_query(f"""
                MATCH (n:{label})
                WHERE toLower(toString(n.{search_field})) CONTAINS toLower($q)
                   OR toLower(toString(n.{id_field})) CONTAINS toLower($q)
                RETURN n.{id_field} AS id, n.{search_field} AS name, '{label}' AS label
                LIMIT 10
            """, {"q": query})
            for r in records:
                results.append({
                    "id": f"{label}_{r['id']}",
                    "label": label,
                    "name": str(r["name"] or r["id"]),
                    "color": NODE_COLORS.get(label, "#6366f1"),
                })
        return results[:20]

    def _id_field(self, label: str) -> str:
        return {
            "Customer": "businessPartner",
            "SalesOrder": "salesOrder",
            "SalesOrderItem": "salesOrder",
            "Delivery": "deliveryDocument",
            "DeliveryItem": "deliveryDocument",
            "BillingDocument": "billingDocument",
            "BillingItem": "billingDocument",
            "JournalEntry": "accountingDocument",
            "Payment": "accountingDocument",
            "Material": "product",
            "Plant": "plant",
            "Address": "businessPartner",
        }.get(label, "id")

    def _node_name(self, label: str, props: dict) -> str:
        name_map = {
            "Customer": "customerName",
            "SalesOrder": "salesOrder",
            "Delivery": "deliveryDocument",
            "BillingDocument": "billingDocument",
            "Material": "productDescription",
            "Plant": "plantName",
            "Payment": "accountingDocument",
            "JournalEntry": "accountingDocument",
        }
        field = name_map.get(label)
        if field and field in props:
            return str(props[field])
        return str(props.get(self._id_field(label), "unknown"))


neo4j_service = Neo4jService()
