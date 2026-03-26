"""Seed Neo4j with SAP O2C data."""
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from neo4j import GraphDatabase
from app.data.ingestion import load_all_data
from app.config import settings


def get_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def clear_database(driver):
    print("Clearing existing data...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("  Done.")


def create_indexes(driver):
    print("Creating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (c:Customer) ON (c.businessPartner)",
        "CREATE INDEX IF NOT EXISTS FOR (so:SalesOrder) ON (so.salesOrder)",
        "CREATE INDEX IF NOT EXISTS FOR (soi:SalesOrderItem) ON (soi.salesOrder, soi.salesOrderItem)",
        "CREATE INDEX IF NOT EXISTS FOR (d:Delivery) ON (d.deliveryDocument)",
        "CREATE INDEX IF NOT EXISTS FOR (di:DeliveryItem) ON (di.deliveryDocument, di.deliveryDocumentItem)",
        "CREATE INDEX IF NOT EXISTS FOR (b:BillingDocument) ON (b.billingDocument)",
        "CREATE INDEX IF NOT EXISTS FOR (bi:BillingItem) ON (bi.billingDocument, bi.billingDocumentItem)",
        "CREATE INDEX IF NOT EXISTS FOR (j:JournalEntry) ON (j.accountingDocument)",
        "CREATE INDEX IF NOT EXISTS FOR (p:Payment) ON (p.accountingDocument)",
        "CREATE INDEX IF NOT EXISTS FOR (m:Material) ON (m.product)",
        "CREATE INDEX IF NOT EXISTS FOR (pl:Plant) ON (pl.plant)",
        "CREATE INDEX IF NOT EXISTS FOR (a:Address) ON (a.businessPartner, a.addressId)",
    ]
    with driver.session() as session:
        for idx in indexes:
            session.run(idx)
    print("  Done.")


def seed_customers(driver, data):
    """Create Customer nodes from business_partners."""
    records = data["business_partners"]
    print(f"Seeding {len(records)} Customer nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (c:Customer {businessPartner: r.businessPartner})
            SET c.customerName = r.businessPartnerName,
                c.fullName = r.businessPartnerFullName,
                c.category = r.businessPartnerCategory,
                c.isBlocked = r.businessPartnerIsBlocked,
                c.creationDate = r.creationDate
        """, {"records": records})
    print("  Done.")


def seed_addresses(driver, data):
    """Create Address nodes and link to Customers."""
    records = data["business_partner_addresses"]
    print(f"Seeding {len(records)} Address nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (a:Address {businessPartner: r.businessPartner, addressId: r.addressId})
            SET a.cityName = r.cityName,
                a.country = r.country,
                a.region = r.region,
                a.streetName = r.streetName,
                a.postalCode = r.postalCode
        """, {"records": records})
        # Link to customers
        session.run("""
            MATCH (c:Customer), (a:Address)
            WHERE c.businessPartner = a.businessPartner
            MERGE (c)-[:LOCATED_AT]->(a)
        """)
    print("  Done.")


def seed_sales_orders(driver, data):
    """Create SalesOrder and SalesOrderItem nodes."""
    headers = data["sales_order_headers"]
    items = data["sales_order_items"]
    print(f"Seeding {len(headers)} SalesOrder nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (so:SalesOrder {salesOrder: r.salesOrder})
            SET so.salesOrderType = r.salesOrderType,
                so.salesOrganization = r.salesOrganization,
                so.soldToParty = r.soldToParty,
                so.creationDate = r.creationDate,
                so.totalNetAmount = r.totalNetAmount,
                so.transactionCurrency = r.transactionCurrency,
                so.overallDeliveryStatus = r.overallDeliveryStatus,
                so.requestedDeliveryDate = r.requestedDeliveryDate,
                so.distributionChannel = r.distributionChannel,
                so.customerPaymentTerms = r.customerPaymentTerms
        """, {"records": headers})

        # Link SalesOrders to Customers
        session.run("""
            MATCH (c:Customer), (so:SalesOrder)
            WHERE c.businessPartner = so.soldToParty
            MERGE (c)-[:PLACED]->(so)
        """)

    print(f"Seeding {len(items)} SalesOrderItem nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (soi:SalesOrderItem {salesOrder: r.salesOrder, salesOrderItem: r.salesOrderItem})
            SET soi.material = r.material,
                soi.requestedQuantity = r.requestedQuantity,
                soi.netAmount = r.netAmount,
                soi.materialGroup = r.materialGroup,
                soi.productionPlant = r.productionPlant,
                soi.transactionCurrency = r.transactionCurrency
        """, {"records": items})

        # Link to SalesOrder
        session.run("""
            MATCH (so:SalesOrder), (soi:SalesOrderItem)
            WHERE so.salesOrder = soi.salesOrder
            MERGE (so)-[:HAS_ITEM]->(soi)
        """)
    print("  Done.")


def seed_materials(driver, data):
    """Create Material nodes."""
    products = data["products"]
    descriptions = data["product_descriptions"]
    print(f"Seeding {len(products)} Material nodes...")

    # Build description lookup
    desc_map = {}
    for d in descriptions:
        desc_map[d["product"]] = d.get("productDescription", "")

    for p in products:
        p["productDescription"] = desc_map.get(p["product"], "")

    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (m:Material {product: r.product})
            SET m.productType = r.productType,
                m.productDescription = r.productDescription,
                m.grossWeight = r.grossWeight,
                m.netWeight = r.netWeight,
                m.baseUnit = r.baseUnit,
                m.productGroup = r.productGroup
        """, {"records": products})

        # Link SalesOrderItems to Materials
        session.run("""
            MATCH (soi:SalesOrderItem), (m:Material)
            WHERE soi.material = m.product
            MERGE (soi)-[:REFERENCES_MATERIAL]->(m)
        """)
    print("  Done.")


def seed_plants(driver, data):
    """Create Plant nodes."""
    records = data["plants"]
    print(f"Seeding {len(records)} Plant nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (p:Plant {plant: r.plant})
            SET p.plantName = r.plantName,
                p.salesOrganization = r.salesOrganization
        """, {"records": records})

        # Link SalesOrderItems to Plants
        session.run("""
            MATCH (soi:SalesOrderItem), (p:Plant)
            WHERE soi.productionPlant = p.plant
            MERGE (soi)-[:PRODUCED_AT]->(p)
        """)
    print("  Done.")


def _normalize_item_number(item_num: str) -> str:
    """Normalize item numbers by stripping leading zeros for consistent matching."""
    if item_num is None:
        return None
    return str(int(item_num)) if item_num.isdigit() else item_num


def seed_deliveries(driver, data):
    """Create Delivery and DeliveryItem nodes."""
    headers = data["outbound_delivery_headers"]
    items = data["outbound_delivery_items"]
    
    # Normalize item numbers for consistent matching across entities
    for item in items:
        if item.get("referenceSdDocumentItem"):
            item["referenceSdDocumentItemNormalized"] = _normalize_item_number(item["referenceSdDocumentItem"])
        if item.get("deliveryDocumentItem"):
            item["deliveryDocumentItemNormalized"] = _normalize_item_number(item["deliveryDocumentItem"])
    
    print(f"Seeding {len(headers)} Delivery nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (d:Delivery {deliveryDocument: r.deliveryDocument})
            SET d.creationDate = r.creationDate,
                d.shippingPoint = r.shippingPoint,
                d.overallGoodsMovementStatus = r.overallGoodsMovementStatus,
                d.overallPickingStatus = r.overallPickingStatus
        """, {"records": headers})

    print(f"Seeding {len(items)} DeliveryItem nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (di:DeliveryItem {deliveryDocument: r.deliveryDocument, deliveryDocumentItem: r.deliveryDocumentItem})
            SET di.actualDeliveryQuantity = r.actualDeliveryQuantity,
                di.plant = r.plant,
                di.referenceSdDocument = r.referenceSdDocument,
                di.referenceSdDocumentItem = r.referenceSdDocumentItem,
                di.referenceSdDocumentItemNormalized = r.referenceSdDocumentItemNormalized,
                di.deliveryDocumentItemNormalized = r.deliveryDocumentItemNormalized,
                di.storageLocation = r.storageLocation
        """, {"records": items})

        # Link DeliveryItem to Delivery
        session.run("""
            MATCH (d:Delivery), (di:DeliveryItem)
            WHERE d.deliveryDocument = di.deliveryDocument
            MERGE (d)-[:HAS_ITEM]->(di)
        """)

        # Link SalesOrder to Delivery (via delivery items referencing sales orders)
        session.run("""
            MATCH (so:SalesOrder), (di:DeliveryItem)
            WHERE so.salesOrder = di.referenceSdDocument
            WITH so, di
            MATCH (d:Delivery {deliveryDocument: di.deliveryDocument})
            MERGE (so)-[:FULFILLED_BY]->(d)
        """)

        # Link Delivery to Plant (shipping point)
        session.run("""
            MATCH (d:Delivery), (p:Plant)
            WHERE d.shippingPoint = p.plant
            MERGE (d)-[:SHIPPED_FROM]->(p)
        """)

        # Link DeliveryItem to Plant
        session.run("""
            MATCH (di:DeliveryItem), (p:Plant)
            WHERE di.plant = p.plant
            MERGE (di)-[:STORED_AT]->(p)
        """)
        
        # Link DeliveryItem to SalesOrderItem (using normalized item number)
        session.run("""
            MATCH (di:DeliveryItem), (soi:SalesOrderItem)
            WHERE di.referenceSdDocument = soi.salesOrder
              AND di.referenceSdDocumentItemNormalized = soi.salesOrderItem
            MERGE (di)-[:FULFILLS_ITEM]->(soi)
        """)
    print("  Done.")


def seed_billing(driver, data):
    """Create BillingDocument and BillingItem nodes."""
    headers = data["billing_document_headers"]
    items = data["billing_document_items"]
    cancellations = data["billing_document_cancellations"]

    # Mark cancelled docs
    cancelled_ids = {c["billingDocument"] for c in cancellations}
    for h in headers:
        if h["billingDocument"] in cancelled_ids:
            h["billingDocumentIsCancelled"] = True

    print(f"Seeding {len(headers)} BillingDocument nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (b:BillingDocument {billingDocument: r.billingDocument})
            SET b.billingDocumentType = r.billingDocumentType,
                b.creationDate = r.creationDate,
                b.billingDocumentDate = r.billingDocumentDate,
                b.totalNetAmount = r.totalNetAmount,
                b.transactionCurrency = r.transactionCurrency,
                b.soldToParty = r.soldToParty,
                b.accountingDocument = r.accountingDocument,
                b.billingDocumentIsCancelled = r.billingDocumentIsCancelled,
                b.companyCode = r.companyCode,
                b.fiscalYear = r.fiscalYear
        """, {"records": headers})

        # Link BillingDocument to Customer
        session.run("""
            MATCH (b:BillingDocument), (c:Customer)
            WHERE b.soldToParty = c.businessPartner
            MERGE (b)-[:SOLD_TO]->(c)
        """)

    # Normalize referenceSdDocumentItem for matching with delivery items
    for item in items:
        if item.get("referenceSdDocumentItem"):
            item["referenceSdDocumentItemNormalized"] = _normalize_item_number(item["referenceSdDocumentItem"])
    
    print(f"Seeding {len(items)} BillingItem nodes...")
    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (bi:BillingItem {billingDocument: r.billingDocument, billingDocumentItem: r.billingDocumentItem})
            SET bi.material = r.material,
                bi.billingQuantity = r.billingQuantity,
                bi.netAmount = r.netAmount,
                bi.transactionCurrency = r.transactionCurrency,
                bi.referenceSdDocument = r.referenceSdDocument,
                bi.referenceSdDocumentItem = r.referenceSdDocumentItem,
                bi.referenceSdDocumentItemNormalized = r.referenceSdDocumentItemNormalized
        """, {"records": items})

        # Link BillingItem to BillingDocument
        session.run("""
            MATCH (b:BillingDocument), (bi:BillingItem)
            WHERE b.billingDocument = bi.billingDocument
            MERGE (b)-[:HAS_ITEM]->(bi)
        """)

        # Link Delivery to BillingDocument (via billing items referencing deliveries)
        session.run("""
            MATCH (d:Delivery), (bi:BillingItem)
            WHERE d.deliveryDocument = bi.referenceSdDocument
            WITH d, bi
            MATCH (b:BillingDocument {billingDocument: bi.billingDocument})
            MERGE (d)-[:BILLED_IN]->(b)
        """)
        
        # Link BillingItem to DeliveryItem (using normalized item numbers)
        session.run("""
            MATCH (bi:BillingItem), (di:DeliveryItem)
            WHERE bi.referenceSdDocument = di.deliveryDocument
              AND bi.referenceSdDocumentItemNormalized = di.deliveryDocumentItemNormalized
            MERGE (bi)-[:BILLS_ITEM]->(di)
        """)
    print("  Done.")


def seed_journal_entries(driver, data):
    """Create JournalEntry nodes."""
    records = data["journal_entry_items_accounts_receivable"]
    print(f"Seeding {len(records)} JournalEntry nodes...")

    # Deduplicate by accountingDocument (take first item per document)
    seen = set()
    unique = []
    for r in records:
        key = r["accountingDocument"]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (j:JournalEntry {accountingDocument: r.accountingDocument})
            SET j.companyCode = r.companyCode,
                j.fiscalYear = r.fiscalYear,
                j.glAccount = r.glAccount,
                j.postingDate = r.postingDate,
                j.documentDate = r.documentDate,
                j.amountInTransactionCurrency = r.amountInTransactionCurrency,
                j.transactionCurrency = r.transactionCurrency,
                j.customer = r.customer,
                j.referenceDocument = r.referenceDocument,
                j.profitCenter = r.profitCenter
        """, {"records": unique})

        # Link BillingDocument to JournalEntry
        session.run("""
            MATCH (b:BillingDocument), (j:JournalEntry)
            WHERE b.accountingDocument = j.accountingDocument
            MERGE (b)-[:POSTED_AS]->(j)
        """)
    print("  Done.")


def seed_payments(driver, data):
    """Create Payment nodes."""
    records = data["payments_accounts_receivable"]
    print(f"Seeding {len(records)} Payment nodes...")

    # Deduplicate by clearing document
    seen = set()
    unique = []
    for r in records:
        key = r.get("clearingAccountingDocument", r["accountingDocument"])
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    with driver.session() as session:
        session.run("""
            UNWIND $records AS r
            MERGE (p:Payment {accountingDocument: r.clearingAccountingDocument})
            SET p.clearingDate = r.clearingDate,
                p.amountInTransactionCurrency = r.amountInTransactionCurrency,
                p.transactionCurrency = r.transactionCurrency,
                p.customer = r.customer,
                p.companyCode = r.companyCode,
                p.fiscalYear = r.fiscalYear,
                p.originalDocument = r.accountingDocument
        """, {"records": unique})

        # Link JournalEntry to Payment (via clearing document)
        session.run("""
            MATCH (j:JournalEntry), (p:Payment)
            WHERE j.accountingDocument = p.originalDocument
            MERGE (j)-[:PAID_VIA]->(p)
        """)
    print("  Done.")


def seed_all(data_dir: str = None):
    """Run the full seeding pipeline."""
    if data_dir is None:
        data_dir = settings.data_dir

    print(f"Loading data from {data_dir}...")
    data = load_all_data(data_dir)

    driver = get_driver()
    try:
        clear_database(driver)
        create_indexes(driver)
        seed_customers(driver, data)
        seed_addresses(driver, data)
        seed_sales_orders(driver, data)
        seed_materials(driver, data)
        seed_plants(driver, data)
        seed_deliveries(driver, data)
        seed_billing(driver, data)
        seed_journal_entries(driver, data)
        seed_payments(driver, data)
        print("\nSeeding complete!")

        # Print summary
        with driver.session() as session:
            result = session.run("""
                MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY count DESC
            """)
            print("\nNode counts:")
            for r in result:
                print(f"  {r['label']}: {r['count']}")

            result = session.run("""
                MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count
                ORDER BY count DESC
            """)
            print("\nRelationship counts:")
            for r in result:
                print(f"  {r['type']}: {r['count']}")

    finally:
        driver.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed Neo4j with SAP O2C data")
    parser.add_argument("--data-dir", default=None, help="Path to data directory")
    args = parser.parse_args()
    seed_all(args.data_dir)
