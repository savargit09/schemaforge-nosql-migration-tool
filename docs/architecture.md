# Implemented architecture

```text
React + Vite
    | REST JSON
    v
FastAPI + Pydantic validation
    |---------------- MongoDB / PyMongo (six collections, indexes)
    |
    +-- SQLGlot DDL parser -> entities, attributes, PK/FK
    +-- SQLGlot workload analyzer -> accesses, joins, filters, ordering, grouping
    +-- Relational property graph -> FK edges + workload evidence
    +-- Cardinality profiler -> supplied child/parent row ratio
    +-- Explicit denormalization rules -> EMBED / REFERENCE
    +-- Comparative cost indicators -> fetches, growth and update considerations
    +-- Trade-off explainer -> evidence, benefit, cost per relationship
    +-- MongoDB schema generator -> collections, fields, nested arrays, index suggestions
```

Rules use supplied table counts. Ratios <= 1.5 are one-to-one/one-to-few, <= 8 are one-to-few, and > 8 are high fan-out; missing counts are treated as unknown and favor references. An embedded strategy is preferred when the relationship is not high-fan-out and access evidence does not show independent child access outweighing co-access. This is an interpretable prototype heuristic, not a production cost optimizer.
