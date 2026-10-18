# API reference

Interactive request and response schemas are served by FastAPI OpenAPI at `/docs`. All database-backed routes return HTTP 503 when MongoDB cannot be reached. Invalid SQL/workload inputs return 422; malformed identifiers return 400; missing resources return 404.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Check process and MongoDB availability |
| GET | `/api/metrics` | Dashboard metrics derived from MongoDB records |
| POST, GET | `/api/projects` | Create and list project records |
| GET, PUT, DELETE | `/api/projects/{project_id}` | Read, update, delete a project |
| POST | `/api/schemas` | Store source SQL DDL under a project |
| GET, PUT, DELETE | `/api/schemas/{schema_id}` | Retrieve, update, or delete a stored schema |
| POST | `/api/workloads` | Store representative SQL queries |
| GET, PUT, DELETE | `/api/workloads/{workload_id}` | Retrieve, update, delete workload |
| POST | `/api/migrations` | Parse, analyze, recommend, generate and persist one run |
| POST | `/api/migrations/{migration_id}/generate` | Apply embed/reference overrides and regenerate stored artifacts |
| GET | `/api/migrations` | List run history |
| GET | `/api/migrations/{migration_id}` | Retrieve complete persisted result |
| GET | `/api/migrations/{migration_id}/recommendations` | Retrieve per-relationship decisions |
| GET | `/api/migrations/{migration_id}/tradeoffs` | Retrieve explanation report |
| GET | `/api/generated-schemas/{migration_id}` | Retrieve generated MongoDB schema |
| GET | `/api/migrations/{migration_id}/export` | Retrieve run JSON for export |
| GET | `/api/database/collections` | Inspect actual collection names, document counts and indexes |
| GET | `/api/database/collections/{collection_name}/sample` | Inspect index definitions and up to three actual documents |

## Migration request

```json
{
  "project_name": "Order Management Migration",
  "ddl": "CREATE TABLE ...",
  "queries": ["SELECT ... JOIN ..."],
  "row_counts": {"customers": 15, "orders": 40, "order_items": 80, "products": 20},
  "overrides": {"orders->order_items": "EMBED"}
}
```

Counts are explicitly supplied estimates in the UI. The sample seed has matching source-table sizes; `order_items` are embedded in the order documents. The response includes `migration_id`, `project_id`, parsed schema, workload signals, graph, decisions, cost indicators, generated schema, and explanations.
