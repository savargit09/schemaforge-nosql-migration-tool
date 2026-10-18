# Review 2 evidence index

Real screenshots captured from the local running application and database on 25 September 2026. The report embeds these images; originals are retained here.

| Screenshot | Evidence shown |
|---|---|
| `dashboard.jpg` | Live dashboard metrics and connected database state |
| `input.jpg` | SQL DDL and representative workload submitted in the UI |
| `analysis.jpg` | Parsed entities/relationships, workload signals, graph and recommendation result |
| `tradeoffs.jpg` | Decision evidence, benefits and trade-offs |
| `override.jpg` | User override followed by generated output update |
| `history.jpg` | Migration history retrieved from MongoDB |
| `mongodb_documents.jpg` | Actual MongoDB collections, seeded records and indexes |
| `mongodb_indexes.jpg` | Collection counts and order index definitions |
| `swagger.jpg` | FastAPI OpenAPI route documentation |
| `api_response.jpg` | Actual collection sample API response with document and index data |

Additional verification is recorded in `Review_2_Report.docx`, `database/backup-export/manifest.json`, and the terminal result from `python -m pytest backend/tests -q` (7 passed). No latency or throughput benchmark screenshot is included because those measurements are planned for Review 3.
