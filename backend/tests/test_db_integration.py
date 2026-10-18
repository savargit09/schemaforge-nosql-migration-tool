import pytest
from fastapi.testclient import TestClient
from app.main import app, db, ready

pytestmark = pytest.mark.skipif(not ready(), reason="MongoDB is not running")


def test_project_workload_crud_and_migration_persistence():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name":"Integration Project", "description":"Disposable API integration fixture"})
        assert project.status_code == 201
        project_id = project.json()["_id"]
        assert client.get(f"/api/projects/{project_id}").status_code == 200
        assert client.put(f"/api/projects/{project_id}", json={"name":"Integration Project Updated", "description":"Updated fixture"}).status_code == 200

        schema = client.post("/api/schemas", json={"project_id":project_id,"ddl":"CREATE TABLE customers (customer_id INT PRIMARY KEY);"})
        assert schema.status_code == 201
        schema_id = schema.json()["_id"]
        assert client.get(f"/api/schemas/{schema_id}").status_code == 200
        assert client.put(f"/api/schemas/{schema_id}", json={"project_id":project_id,"ddl":"CREATE TABLE customers (customer_id INT PRIMARY KEY, name VARCHAR(60));"}).status_code == 200

        workload = client.post("/api/workloads", json={"project_id":project_id, "queries":["SELECT * FROM customers"]})
        assert workload.status_code == 201
        workload_id = workload.json()["_id"]
        assert client.get(f"/api/workloads/{workload_id}").status_code == 200
        assert client.put(f"/api/workloads/{workload_id}", json={"project_id":project_id, "queries":["SELECT * FROM customers WHERE customer_id=1"]}).status_code == 200

        ddl = "CREATE TABLE customers (customer_id INT PRIMARY KEY, name VARCHAR(60)); CREATE TABLE orders (order_id INT PRIMARY KEY, customer_id INT, FOREIGN KEY (customer_id) REFERENCES customers(customer_id));"
        run = client.post("/api/migrations", json={"project_name":"Disposable Integration Migration", "ddl":ddl, "queries":["SELECT c.name FROM customers c JOIN orders o ON c.customer_id=o.customer_id"], "row_counts":{"customers":2,"orders":4}})
        assert run.status_code == 201, run.text
        migration_id = run.json()["migration_id"]
        assert client.get(f"/api/migrations/{migration_id}").status_code == 200
        assert client.get(f"/api/generated-schemas/{migration_id}").status_code == 200
        assert client.get(f"/api/migrations/{migration_id}/tradeoffs").status_code == 200
        assert client.get("/api/database/collections").status_code == 200
        sample = client.get("/api/database/collections/orders/sample")
        assert sample.status_code == 200
        assert sample.json()["documents"] == 40
        assert "customer_id_1_order_date_-1" in [i["name"] for i in sample.json()["indexes"]]
        assert client.delete(f"/api/schemas/{schema_id}").status_code == 204
        assert client.delete(f"/api/workloads/{workload_id}").status_code == 204
        assert client.delete(f"/api/projects/{project_id}").status_code == 204

        # Remove the integration run's transient records from the local test database.
        from bson import ObjectId
        ident = ObjectId(migration_id)
        saved = db.migration_runs.find_one({"_id":ident})
        if saved:
            pid = saved["project_id"]
            db.generated_schemas.delete_many({"migration_id":ident})
            db.tradeoff_reports.delete_many({"migration_id":ident})
            db.schemas.delete_many({"project_id":str(pid)})
            db.workloads.delete_many({"project_id":str(pid)})
            db.projects.delete_one({"_id":pid})
            db.migration_runs.delete_one({"_id":ident})
