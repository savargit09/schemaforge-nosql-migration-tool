# Review 2 rubric-to-evidence mapping

| Rubric criterion | Project evidence | Report section | Screenshot/artifact |
|---|---|---|---|
| Database implementation | MongoDB database, collections, nested order items, indexes, sample documents | 3-4 | `docs/evidence/` MongoDB/Compass screenshots; `database/` setup and seed |
| CRUD operations | Project/schema/workload CRUD API routes and Mongo persistence | 6, 8 | Swagger request/response screenshot and verified DB state |
| Data modelling quality | Workload-driven embed/reference choices, row fan-out, indexes, duplication trade-offs | 3, 5 | Recommendations and generated schema screenshots |
| Functional prototype | DDL + workload -> parsing -> analysis -> recommendation -> generated schema -> persistence/retrieval | 7 | Actual running UI and MongoDB evidence |
| Progress and documentation | README, API OpenAPI, tests, export/restore steps, demo sequence, status split | 10-14, appendices | Test output and verified dump/restore evidence |

Only capture and mark evidence after obtaining it from the running application or database. A route definition or planned command alone does not prove a CRUD or backup result.
