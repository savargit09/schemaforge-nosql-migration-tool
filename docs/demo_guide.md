# Review 2 demonstration sequence (7-10 minutes)

1. **Problem, 30 s** - Relational normalization makes common related reads join-heavy; migration design must make the workload evidence and costs reviewable.
2. **Architecture, 45 s** - Show the React -> FastAPI -> parser/analyzer -> graph/rules/cost -> MongoDB pipeline and Swagger.
3. **MongoDB model, 45 s** - Show the six metadata collections, embedded order items, references, and indexes in MongoDB.
4. **Input, 60 s** - Open New migration; inspect the order DDL, estimated table counts, and SELECT/JOIN workload.
5. **Analysis, 90 s** - Run migration; explain parsed tables, PK/FK graph, filters, sorting, join/co-access counts, and fan-out.
6. **Recommendations, 90 s** - Explain every EMBED/REFERENCE decision from workload and cardinality. Open evidence and trade-off details.
7. **Generated schema, 45 s** - Inspect generated MongoDB collections/fields/nested arrays/index suggestions and export JSON.
8. **Persistence, 45 s** - Open Run History, retrieve saved result, and show actual MongoDB documents and index list.
9. **CRUD/API, 45 s** - Use Swagger for project CRUD and retrieve the generated schema/tradeoff endpoint.
10. **Validation and close, 45 s** - Show actual test output, state cost estimates are heuristics, distinguish Review 3 work.

Run `docker compose -f database/docker-compose.yml up -d`, start the API and Vite UI per README, then run `python -m app.seed` before the presentation. Use actual saved results and screenshots from the demonstration machine.
