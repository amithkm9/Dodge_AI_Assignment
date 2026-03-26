import json
import os
from pathlib import Path


def load_jsonl_dir(directory: str) -> list[dict]:
    """Load all JSONL files from a directory."""
    records = []
    dir_path = Path(directory)
    if not dir_path.exists():
        return records
    for f in sorted(dir_path.glob("*.jsonl")):
        with open(f, "r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def load_all_data(base_dir: str) -> dict:
    """Load SAP O2C dataset files required for the graph model.
    
    Note: The following entities exist in the dataset but are not loaded as they
    are not used in the current graph model:
    - sales_order_schedule_lines: Sub-item level schedule data (confirmed dates/quantities)
    - product_plants: Material-plant assignments (MRP, profit center)
    - product_storage_locations: Material-plant-storage location data
    - customer_company_assignments: Customer FI company code extensions
    - customer_sales_area_assignments: Customer sales area master data
    
    These can be added if more detailed queries are needed.
    """
    datasets = {}
    entities = [
        "business_partners", "business_partner_addresses",
        "sales_order_headers", "sales_order_items",
        "outbound_delivery_headers", "outbound_delivery_items",
        "billing_document_headers", "billing_document_items", "billing_document_cancellations",
        "journal_entry_items_accounts_receivable", "payments_accounts_receivable",
        "products", "product_descriptions", "plants",
    ]
    for entity in entities:
        path = os.path.join(base_dir, entity)
        datasets[entity] = load_jsonl_dir(path)
        print(f"  Loaded {len(datasets[entity]):>6} records from {entity}")
    return datasets
