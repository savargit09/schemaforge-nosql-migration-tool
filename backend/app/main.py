from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from .config import settings
from .engine import run_pipeline

app = FastAPI(title="Relational-to-NoSQL Schema Migration Tool", version="0.2.0", description="Workload-aware MongoDB schema recommendations with transparent trade-off explanations.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=900)
db = client[settings.mongodb_database]
COLLECTIONS = ["projects", "schemas", "workloads", "migration_runs", "generated_schemas", "tradeoff_reports"]


def ready() -> bool:
    try:
        client.admin.command("ping")
        return True
    except PyMongoError:
        return False


def mongo():
    if not ready():
        raise HTTPException(503, "MongoDB is unavailable. Start the MongoDB service described in README.md.")
    return db


def oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(400, "Invalid identifier")
    return ObjectId(value)


def clean(value: Any):
    if isinstance(value, ObjectId): return str(value)
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list): return [clean(v) for v in value]
    return value


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""


class SchemaIn(BaseModel):
    project_id: str
    ddl: str = Field(min_length=10)


class WorkloadIn(BaseModel):
    project_id: str
    queries: list[str] = Field(min_length=1)


class MigrationIn(BaseModel):
    project_name: str = "Order Management Migration"
    ddl: str = Field(min_length=10)
    queries: list[str] = Field(min_length=1)
    row_counts: dict[str, int] = {}
    overrides: dict[str, str] = {}


class OverrideIn(BaseModel):
    overrides: dict[str, str]


@app.on_event("startup")
def init_db():
    if ready():
        for name in COLLECTIONS:
            if name not in db.list_collection_names(): db.create_collection(name)
        db.projects.create_index([("name", ASCENDING)])
        db.schemas.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        db.workloads.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        db.migration_runs.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        db.generated_schemas.create_index([("migration_id", ASCENDING)], unique=True)
        db.tradeoff_reports.create_index([("migration_id", ASCENDING)], unique=True)


@app.get("/api/health")
def health():
    return {"status": "ok", "mongodb": "connected" if ready() else "unavailable", "database": settings.mongodb_database}


@app.get("/api/metrics")
def metrics():
    d = mongo()
    runs = list(d.migration_runs.find({}, {"result.cost_summary": 1}))
    embedded = sum(r.get("result", {}).get("cost_summary", {}).get("embedded_relationships", 0) for r in runs)
    referenced = sum(r.get("result", {}).get("cost_summary", {}).get("referenced_relationships", 0) for r in runs)
    return {"projects": d.projects.count_documents({}), "schemas": d.schemas.count_documents({}), "migration_runs": len(runs), "recommendations": embedded + referenced, "embedded_relationships": embedded, "referenced_relationships": referenced}


@app.post("/api/projects", status_code=201)
def create_project(body: ProjectIn):
    d = mongo(); now = datetime.now(timezone.utc)
    doc = body.model_dump() | {"created_at": now, "updated_at": now}
    result = d.projects.insert_one(doc)
    return clean(doc | {"_id": result.inserted_id})


@app.get("/api/projects")
def list_projects(): return [clean(x) for x in mongo().projects.find().sort("created_at", DESCENDING)]


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    doc = mongo().projects.find_one({"_id": oid(project_id)})
    if not doc: raise HTTPException(404, "Project not found")
    return clean(doc)


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, body: ProjectIn):
    d = mongo(); result = d.projects.find_one_and_update({"_id": oid(project_id)}, {"$set": body.model_dump() | {"updated_at": datetime.now(timezone.utc)}}, return_document=True)
    if not result: raise HTTPException(404, "Project not found")
    return clean(result)


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    d = mongo(); result = d.projects.delete_one({"_id": oid(project_id)})
    if not result.deleted_count: raise HTTPException(404, "Project not found")


@app.post("/api/schemas", status_code=201)
def save_schema(body: SchemaIn):
    d = mongo(); now = datetime.now(timezone.utc)
    doc = body.model_dump() | {"created_at": now}
    if not d.projects.find_one({"_id": oid(body.project_id)}): raise HTTPException(404, "Project not found")
    res = d.schemas.insert_one(doc); return clean(doc | {"_id": res.inserted_id})


@app.get("/api/schemas/{schema_id}")
def get_schema(schema_id: str):
    x = mongo().schemas.find_one({"_id": oid(schema_id)})
    if not x: raise HTTPException(404, "Schema not found")
    return clean(x)


@app.put("/api/schemas/{schema_id}")
def update_schema(schema_id: str, body: SchemaIn):
    d = mongo()
    if not d.projects.find_one({"_id": oid(body.project_id)}): raise HTTPException(404, "Project not found")
    x = d.schemas.find_one_and_update({"_id": oid(schema_id)}, {"$set": body.model_dump() | {"updated_at": datetime.now(timezone.utc)}}, return_document=True)
    if not x: raise HTTPException(404, "Schema not found")
    return clean(x)


@app.delete("/api/schemas/{schema_id}", status_code=204)
def delete_schema(schema_id: str):
    if not mongo().schemas.delete_one({"_id": oid(schema_id)}).deleted_count: raise HTTPException(404, "Schema not found")


@app.post("/api/workloads", status_code=201)
def save_workload(body: WorkloadIn):
    d = mongo(); now = datetime.now(timezone.utc); doc = body.model_dump() | {"created_at": now}
    if not d.projects.find_one({"_id": oid(body.project_id)}): raise HTTPException(404, "Project not found")
    res = d.workloads.insert_one(doc); return clean(doc | {"_id": res.inserted_id})


@app.get("/api/workloads/{workload_id}")
def get_workload(workload_id: str):
    x = mongo().workloads.find_one({"_id": oid(workload_id)})
    if not x: raise HTTPException(404, "Workload not found")
    return clean(x)


@app.put("/api/workloads/{workload_id}")
def update_workload(workload_id: str, body: WorkloadIn):
    x = mongo().workloads.find_one_and_update({"_id": oid(workload_id)}, {"$set": body.model_dump()}, return_document=True)
    if not x: raise HTTPException(404, "Workload not found")
    return clean(x)


@app.delete("/api/workloads/{workload_id}", status_code=204)
def delete_workload(workload_id: str):
    if not mongo().workloads.delete_one({"_id": oid(workload_id)}).deleted_count: raise HTTPException(404, "Workload not found")


@app.post("/api/migrations", status_code=201)
def create_migration(body: MigrationIn):
    d = mongo(); now = datetime.now(timezone.utc)
    project = d.projects.find_one({"name": body.project_name})
    if not project:
        doc = {"name": body.project_name, "description": "Generated from the submitted migration input.", "created_at": now, "updated_at": now}
        project_id = d.projects.insert_one(doc).inserted_id
    else: project_id = project["_id"]
    try:
        result = run_pipeline(body.ddl, body.queries, body.row_counts, body.overrides)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    run = {"project_id": project_id, "project_name": body.project_name, "status": "completed", "created_at": now, "input": body.model_dump(), "result": result}
    migration_id = d.migration_runs.insert_one(run).inserted_id
    d.generated_schemas.insert_one({"migration_id": migration_id, "project_id": project_id, "schema": result["mongo_schema"], "created_at": now})
    d.tradeoff_reports.insert_one({"migration_id": migration_id, "project_id": project_id, "items": result["tradeoffs"], "created_at": now})
    d.schemas.insert_one({"project_id": str(project_id), "ddl": body.ddl, "parsed": result["parsed_schema"], "created_at": now})
    d.workloads.insert_one({"project_id": str(project_id), "queries": body.queries, "analysis": result["workload"], "created_at": now})
    return {"migration_id": str(migration_id), "project_id": str(project_id), "input": body.model_dump(), **clean(result)}


@app.get("/api/migrations")
def list_migrations(): return [clean(x) for x in mongo().migration_runs.find({}, {"input.ddl": 0}).sort("created_at", DESCENDING)]


@app.get("/api/migrations/{migration_id}")
def get_migration(migration_id: str):
    x = mongo().migration_runs.find_one({"_id": oid(migration_id)})
    if not x: raise HTTPException(404, "Migration not found")
    return clean(x)


@app.get("/api/migrations/{migration_id}/recommendations")
def get_recommendations(migration_id: str):
    x = mongo().migration_runs.find_one({"_id": oid(migration_id)}, {"result.recommendations": 1})
    if not x: raise HTTPException(404, "Migration not found")
    return clean(x["result"]["recommendations"])


@app.post("/api/migrations/{migration_id}/generate")
def regenerate_migration(migration_id: str, body: OverrideIn):
    d = mongo(); ident = oid(migration_id)
    run = d.migration_runs.find_one({"_id": ident})
    if not run: raise HTTPException(404, "Migration not found")
    source = run["input"]
    try:
        result = run_pipeline(source["ddl"], source["queries"], source.get("row_counts", {}), body.overrides)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    source["overrides"] = body.overrides
    d.migration_runs.update_one({"_id": ident}, {"$set": {"input": source, "result": result, "updated_at": datetime.now(timezone.utc)}})
    d.generated_schemas.update_one({"migration_id": ident}, {"$set": {"schema": result["mongo_schema"], "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    d.tradeoff_reports.update_one({"migration_id": ident}, {"$set": {"items": result["tradeoffs"], "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"migration_id": migration_id, "project_id": str(run["project_id"]), "input": source, **clean(result)}


@app.get("/api/migrations/{migration_id}/tradeoffs")
def get_tradeoffs(migration_id: str):
    x = mongo().tradeoff_reports.find_one({"migration_id": oid(migration_id)})
    if not x: raise HTTPException(404, "Trade-off report not found")
    return clean(x["items"])


@app.get("/api/generated-schemas/{migration_id}")
def get_generated_schema(migration_id: str):
    x = mongo().generated_schemas.find_one({"migration_id": oid(migration_id)})
    if not x: raise HTTPException(404, "Generated schema not found")
    return clean(x["schema"])


@app.get("/api/migrations/{migration_id}/export")
def export_migration(migration_id: str): return get_migration(migration_id)


@app.get("/api/database/collections")
def collection_status():
    d = mongo()
    return {"database": settings.mongodb_database, "collections": [{"name": n, "documents": d[n].count_documents({}), "indexes": list(d[n].index_information().keys())} for n in d.list_collection_names()]}


@app.get("/api/database/collections/{collection_name}/sample")
def collection_sample(collection_name: str):
    d = mongo()
    if collection_name not in d.list_collection_names(): raise HTTPException(404, "Collection not found")
    coll = d[collection_name]
    indexes = [{"name": name, "keys": [[key, direction] for key, direction in spec["key"]], "unique": spec.get("unique", False)} for name, spec in coll.index_information().items()]
    return {"collection": collection_name, "documents": coll.count_documents({}), "indexes": indexes, "sample": [clean(x) for x in coll.find().limit(3)]}
