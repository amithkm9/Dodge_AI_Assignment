NODE_COLORS = {
    "Customer": "#3b82f6",
    "SalesOrder": "#8b5cf6",
    "SalesOrderItem": "#a78bfa",
    "Delivery": "#10b981",
    "DeliveryItem": "#34d399",
    "BillingDocument": "#ef4444",
    "BillingItem": "#f87171",
    "JournalEntry": "#f59e0b",
    "Payment": "#eab308",
    "Material": "#06b6d4",
    "Plant": "#84cc16",
    "Address": "#64748b",
}

GRAPH_SCHEMA = """
Node Labels and Properties:
- Customer: businessPartner (ID), customerName, category, isBlocked
- SalesOrder: salesOrder (ID), salesOrderType, salesOrganization, soldToParty, creationDate, totalNetAmount, transactionCurrency, overallDeliveryStatus, requestedDeliveryDate
- SalesOrderItem: salesOrder, salesOrderItem (ID pair), material, requestedQuantity, netAmount, productionPlant
- Delivery: deliveryDocument (ID), creationDate, shippingPoint, overallGoodsMovementStatus, overallPickingStatus
- DeliveryItem: deliveryDocument, deliveryDocumentItem (ID pair), actualDeliveryQuantity, plant, referenceSdDocument, referenceSdDocumentItem
- BillingDocument: billingDocument (ID), billingDocumentType, creationDate, billingDocumentDate, totalNetAmount, transactionCurrency, soldToParty, accountingDocument, billingDocumentIsCancelled
- BillingItem: billingDocument, billingDocumentItem (ID pair), material, billingQuantity, netAmount, referenceSdDocument
- JournalEntry: accountingDocument (ID), companyCode, fiscalYear, glAccount, postingDate, amountInTransactionCurrency, transactionCurrency, customer
- Payment: accountingDocument (ID), clearingDate, clearingAccountingDocument, amountInTransactionCurrency, transactionCurrency, customer
- Material: product (ID), productType, productDescription, grossWeight, netWeight, baseUnit
- Plant: plant (ID), plantName, salesOrganization
- Address: businessPartner+addressId (ID), cityName, country, region, streetName, postalCode

Relationships:
- (Customer)-[:PLACED]->(SalesOrder)
- (SalesOrder)-[:HAS_ITEM]->(SalesOrderItem)
- (SalesOrderItem)-[:REFERENCES_MATERIAL]->(Material)
- (SalesOrderItem)-[:PRODUCED_AT]->(Plant)
- (SalesOrder)-[:FULFILLED_BY]->(Delivery)
- (Delivery)-[:HAS_ITEM]->(DeliveryItem)
- (DeliveryItem)-[:FULFILLS_ITEM]->(SalesOrderItem)
- (DeliveryItem)-[:STORED_AT]->(Plant)
- (Delivery)-[:SHIPPED_FROM]->(Plant)
- (Delivery)-[:BILLED_IN]->(BillingDocument)
- (BillingDocument)-[:HAS_ITEM]->(BillingItem)
- (BillingItem)-[:BILLS_ITEM]->(DeliveryItem)
- (BillingDocument)-[:POSTED_AS]->(JournalEntry)
- (BillingDocument)-[:SOLD_TO]->(Customer)
- (JournalEntry)-[:PAID_VIA]->(Payment)
- (Customer)-[:LOCATED_AT]->(Address)
"""
