from app.engine import parse_ddl, analyze_workload, run_pipeline

DDL = """
CREATE TABLE customers (customer_id INT PRIMARY KEY, name VARCHAR(100));
CREATE TABLE orders (order_id INT PRIMARY KEY, customer_id INT, CONSTRAINT fk_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id));
CREATE TABLE order_items (item_id INT PRIMARY KEY, order_id INT, CONSTRAINT fk_order FOREIGN KEY (order_id) REFERENCES orders(order_id));
"""

def test_parse_primary_foreign_keys():
    parsed = parse_ddl(DDL)
    by_name = {t["name"]: t for t in parsed["tables"]}
    assert by_name["customers"]["primary_key"] == ["customer_id"]
    assert by_name["orders"]["foreign_keys"][0]["references_table"] == "customers"

def test_workload_join_and_filters():
    parsed = parse_ddl(DDL)
    result = analyze_workload(["SELECT c.name FROM customers c JOIN orders o ON c.customer_id=o.customer_id WHERE c.customer_id=1"], parsed["tables"])
    assert result["query_count"] == 1
    assert result["table_accesses"]["orders"] == 1
    assert result["filters"][0]["column"] == "customer_id"

def test_pipeline_decisions_and_override():
    queries = ["SELECT * FROM orders o JOIN order_items i ON o.order_id=i.order_id"]
    result = run_pipeline(DDL, queries, {"orders": 10, "order_items": 20, "customers": 10})
    assert result["recommendations"][0]["decision"] in {"EMBED", "REFERENCE"}
    forced = run_pipeline(DDL, queries, {"orders": 10, "order_items": 20, "customers": 10}, {"orders->order_items": "REFERENCE"})
    assert next(x for x in forced["recommendations"] if x["relationship"] == "orders->order_items")["decision"] == "REFERENCE"
    assert "collections" in result["mongo_schema"]

def test_invalid_ddl_rejected():
    try:
        parse_ddl("not ddl")
    except ValueError as exc:
        assert "No CREATE TABLE" in str(exc)
    else:
        raise AssertionError("invalid DDL should fail")
