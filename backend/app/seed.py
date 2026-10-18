"""Seed a small deterministic order management workload into MongoDB."""
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from .config import settings

client = MongoClient(settings.mongodb_uri)
db = client[settings.mongodb_database]
for name in ["projects", "schemas", "workloads", "migration_runs", "generated_schemas", "tradeoff_reports"]:
    db[name].create_index([("created_at", DESCENDING)]) if name in {"projects", "migration_runs"} else None
db.projects.delete_many({"name": "Order Management Demonstration"})
now = datetime.now(timezone.utc)
project = {"name": "Order Management Demonstration", "description": "Deterministic seed dataset for relational-to-document schema design.", "created_at": now, "updated_at": now}
db.projects.insert_one(project)
customers = [{"customer_id": i, "name": f"Customer {i:02d}", "email": f"customer{i:02d}@example.test", "city": ["Vellore", "Chennai", "Bengaluru"][i % 3]} for i in range(1, 16)]
products = [{"product_id": i, "name": f"Product {i:02d}", "category": ["Books", "Electronics", "Home"][i % 3], "unit_price": round(20 + i * 3.25, 2)} for i in range(1, 21)]
orders = []
for i in range(1, 41):
    items = []
    for j in range(1, 1 + (i % 3 + 1)):
        product = products[(i * j) % len(products)]
        items.append({"product_id": product["product_id"], "name": product["name"], "quantity": j, "unit_price": product["unit_price"]})
    total = round(sum(x["quantity"] * x["unit_price"] for x in items), 2)
    orders.append({"order_id": i, "customer_id": ((i - 1) % len(customers)) + 1, "order_date": (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat(), "status": ["PLACED", "SHIPPED", "DELIVERED"][i % 3], "order_total": total, "items": items})
for coll, rows in (("customers", customers), ("products", products), ("orders", orders)):
    db[coll].delete_many({})
    db[coll].insert_many(rows)
db.customers.create_index([("customer_id", ASCENDING)], unique=True)
db.products.create_index([("product_id", ASCENDING)], unique=True)
db.orders.create_index([("order_id", ASCENDING)], unique=True)
db.orders.create_index([("customer_id", ASCENDING), ("order_date", DESCENDING)])
db.orders.create_index([("status", ASCENDING), ("order_date", DESCENDING)])
db["order_items"].delete_many({})
print({"customers": len(customers), "products": len(products), "orders": len(orders), "order_items": sum(len(x["items"]) for x in orders)})
client.close()
