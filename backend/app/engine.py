"""Transparent workload-aware relational to MongoDB schema recommendation."""
from collections import Counter, defaultdict
from typing import Any
import sqlglot
from sqlglot import exp


def _type_name(node: Any) -> str:
    if node is None:
        return "UNKNOWN"
    return node.sql(dialect="mysql").upper()


def parse_ddl(ddl: str) -> dict:
    statements = sqlglot.parse(ddl, read="mysql")
    tables: dict[str, dict] = {}
    pending = []
    for stmt in statements:
        if not isinstance(stmt, exp.Create) or not isinstance(stmt.this, exp.Schema):
            continue
        table = stmt.this.this.name.lower()
        columns, pks, fks = [], [], []
        for item in stmt.this.expressions:
            if isinstance(item, exp.ColumnDef):
                name = item.name.lower()
                dtype = _type_name(item.args.get("kind"))
                columns.append({"name": name, "type": dtype, "nullable": True})
                for constraint in item.args.get("constraints") or []:
                    kind = constraint.args.get("kind")
                    if isinstance(kind, exp.PrimaryKeyColumnConstraint):
                        pks.append(name)
                    elif isinstance(kind, exp.Reference):
                        pending.append((table, [name], kind))
            elif isinstance(item, exp.Constraint):
                for c in item.expressions:
                    kind = c if isinstance(c, (exp.PrimaryKey, exp.ForeignKey)) else c.args.get("kind")
                    if isinstance(kind, exp.PrimaryKey):
                        pks.extend(x.name.lower() for x in kind.expressions)
                    elif isinstance(kind, exp.ForeignKey):
                        pending.append((table, [x.name.lower() for x in kind.expressions], kind.args.get("reference")))
            elif isinstance(item, exp.ForeignKey):
                pending.append((table, [x.name.lower() for x in item.expressions], item.args.get("reference")))
        tables[table] = {"name": table, "columns": columns, "primary_key": list(dict.fromkeys(pks)), "foreign_keys": fks}
    for source, cols, ref in pending:
        if ref is None:
            continue
        target = ref.this
        if isinstance(target, exp.Schema):
            target_table = target.this.name.lower()
            target_cols = [x.name.lower() for x in target.expressions]
        elif isinstance(target, exp.Table):
            target_table, target_cols = target.name.lower(), []
        else:
            target_table, target_cols = str(target).lower(), []
        fk = {"columns": cols, "references_table": target_table, "references_columns": target_cols or ["id"]}
        if source in tables:
            tables[source]["foreign_keys"].append(fk)
    if not tables:
        raise ValueError("No CREATE TABLE definitions were found in the supplied SQL DDL.")
    return {"tables": list(tables.values())}


def analyze_workload(queries: list[str], tables: list[dict]) -> dict:
    known = {t["name"] for t in tables}
    accesses, joins, filters, sorts, groups = Counter(), Counter(), Counter(), Counter(), Counter()
    coaccess = Counter()
    for query in queries:
        try:
            tree = sqlglot.parse_one(query, read="mysql")
        except Exception as exc:
            raise ValueError(f"Could not parse workload query: {exc}") from exc
        alias_to_table = {t.alias_or_name.lower(): t.name.lower() for t in tree.find_all(exp.Table) if t.name.lower() in known}
        used = sorted(set(alias_to_table.values()))
        accesses.update(used)
        for join in tree.find_all(exp.Join):
            on = join.args.get("on")
            if on is not None:
                cols = list(on.find_all(exp.Column))
                if len(cols) >= 2:
                    a = alias_to_table.get(cols[0].table.lower(), cols[0].table.lower())
                    b = alias_to_table.get(cols[1].table.lower(), cols[1].table.lower())
                    if a in known and b in known:
                        joins[tuple(sorted((a, b)))] += 1
        for clause, counter in ((exp.Where, filters), (exp.Order, sorts), (exp.Group, groups)):
            node = tree.find(clause)
            if node:
                for col in node.find_all(exp.Column):
                    tab = alias_to_table.get(col.table.lower(), col.table.lower())
                    if tab in known:
                        counter[(tab, col.name.lower())] += 1
        for i, a in enumerate(used):
            for b in used[i + 1:]:
                coaccess[tuple(sorted((a, b)))] += 1
    return {
        "query_count": len(queries),
        "table_accesses": dict(accesses),
        "join_frequency": [{"tables": list(k), "count": v} for k, v in joins.items()],
        "co_access": [{"tables": list(k), "count": v} for k, v in coaccess.items()],
        "filters": [{"table": k[0], "column": k[1], "count": v} for k, v in filters.items()],
        "sorts": [{"table": k[0], "column": k[1], "count": v} for k, v in sorts.items()],
        "groups": [{"table": k[0], "column": k[1], "count": v} for k, v in groups.items()],
    }


def recommend(parsed: dict, workload: dict, row_counts: dict[str, int] | None = None, overrides: dict[str, str] | None = None) -> dict:
    row_counts, overrides = row_counts or {}, overrides or {}
    tables = {t["name"]: t for t in parsed["tables"]}
    co = {tuple(x["tables"]): x["count"] for x in workload["co_access"]}
    accesses = workload["table_accesses"]
    decisions, edges, graph_nodes = [], [], []
    for t in tables.values():
        graph_nodes.append({"id": t["name"], "label": t["name"], "columns": len(t["columns"])})
        for fk in t["foreign_keys"]:
            parent, child = fk["references_table"], t["name"]
            parent_rows = max(1, row_counts.get(parent, 1))
            child_rows = row_counts.get(child)
            fanout = round(child_rows / parent_rows, 2) if child_rows is not None else None
            if fanout is None:
                cardinality = "unknown; conservatively treated as potentially many"
            elif fanout <= 1.5:
                cardinality = "one-to-one / one-to-few"
            elif fanout <= 8:
                cardinality = "one-to-few"
            else:
                cardinality = "one-to-many / high fan-out"
            pair = tuple(sorted((parent, child)))
            co_count = co.get(pair, 0)
            child_access = accesses.get(child, 0)
            parent_access = accesses.get(parent, 0)
            high_fanout = fanout is None or fanout > 8
            choice = "REFERENCE" if high_fanout or (child_access > co_count and child_access > parent_access) else "EMBED"
            key = f"{parent}->{child}"
            if overrides.get(key, "").upper() in {"EMBED", "REFERENCE"}:
                choice = overrides[key].upper()
            evidence = [f"Estimated child/parent row ratio: {fanout if fanout is not None else 'unavailable'} ({cardinality}).", f"Queries co-accessing {parent} and {child}: {co_count} of {workload['query_count']}.", f"Independent table accesses: {child}={child_access}, {parent}={parent_access}."]
            if choice == "REFERENCE":
                why = ("High or unknown fan-out risks unbounded parent documents; referencing keeps document growth bounded." if high_fanout else "Independent child access exceeds observed co-access, so referencing keeps the child separately addressable and limits unnecessary duplication.")
            else:
                why = "The relationship is retrieved together by the workload and estimated fan-out is bounded, so embedding can avoid a separate lookup."
            decisions.append({"relationship": key, "parent": parent, "child": child, "foreign_key": fk["columns"], "decision": choice, "cardinality": cardinality, "fanout": fanout, "co_access_count": co_count, "child_access_count": child_access, "parent_access_count": parent_access, "evidence": evidence, "reason": why, "benefit": "Avoids a separate relationship lookup on co-accessed reads." if choice == "EMBED" else "Bounds document growth and avoids duplicating independently maintained child records.", "tradeoff": "Parent documents grow; updating child values may require rewriting the parent." if choice == "EMBED" else "Reads that need both entities require an additional reference resolution."})
            edges.append({"source": parent, "target": child, "decision": choice, "fanout": fanout})
    schema = {"database": "nosql_migration_tool", "collections": []}
    embedded = {(d["parent"], d["child"]): d for d in decisions if d["decision"] == "EMBED"}
    for table in tables.values():
        fields = {"_id": "ObjectId", **{c["name"]: _bson_type(c["type"]) for c in table["columns"]}}
        for d in decisions:
            if d["child"] == table["name"] and d["decision"] == "REFERENCE":
                for fk_col in d["foreign_key"]:
                    source_type = next((c["type"] for c in table["columns"] if c["name"] == fk_col), "UNKNOWN")
                    target_key = ", ".join(tables[d["parent"]]["primary_key"]) or "_id"
                    fields[fk_col] = f"{_bson_type(source_type)} (reference to {d['parent']}.{target_key})"
        nested = []
        for d in decisions:
            if d["parent"] == table["name"] and d["decision"] == "EMBED":
                child = tables[d["child"]]
                child_fields = {c["name"]: _bson_type(c["type"]) for c in child["columns"] if c["name"] not in child["primary_key"] and c["name"] not in d["foreign_key"]}
                for rel in decisions:
                    if rel["child"] == d["child"] and rel["decision"] == "REFERENCE":
                        for fk_col in rel["foreign_key"]:
                            source_type = next((c["type"] for c in child["columns"] if c["name"] == fk_col), "UNKNOWN")
                            target_key = ", ".join(tables[rel["parent"]]["primary_key"]) or "_id"
                            child_fields[fk_col] = f"{_bson_type(source_type)} (reference to {rel['parent']}.{target_key})"
                nested.append({"name": d["child"], "array": True, "fields": child_fields})
        schema["collections"].append({"name": table["name"], "fields": fields, "embedded": nested, "indexes": _indexes_for(table, workload)})
    return {"recommendations": decisions, "graph": {"nodes": graph_nodes, "edges": edges}, "mongo_schema": schema, "cost_summary": _estimate(decisions, workload)}


def _bson_type(sql_type: str) -> str:
    t = sql_type.upper()
    if any(x in t for x in ("INT", "SERIAL")): return "Int32/Int64"
    if any(x in t for x in ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE")): return "Decimal128/Double"
    if any(x in t for x in ("DATE", "TIME")): return "Date"
    if "BOOL" in t: return "Boolean"
    return "String"


def _indexes_for(table: dict, workload: dict) -> list[dict]:
    fields: dict[str, list[str]] = defaultdict(list)
    for x in workload["filters"]:
        if x["table"] == table["name"]: fields[x["column"]].append("filter")
    for x in workload["sorts"]:
        if x["table"] == table["name"]: fields[x["column"]].append("sort")
    for x in table["primary_key"]: fields[x].append("primary key")
    return [{"field": f, "direction": 1, "reason": "Supports workload " + ", ".join(dict.fromkeys(why)) + " access."} for f, why in fields.items()]


def _estimate(decisions: list[dict], workload: dict) -> dict:
    embeds = sum(d["decision"] == "EMBED" for d in decisions)
    refs = len(decisions) - embeds
    joins = sum(x["count"] for x in workload["join_frequency"])
    return {"relationships": len(decisions), "embedded_relationships": embeds, "referenced_relationships": refs, "workload_join_occurrences": joins, "logical_fetches_avoided_estimate": min(embeds, joins), "read_cost": "lower for co-access paths selected for embedding; heuristic estimate", "write_cost": "higher consistency/update fan-out for duplicated or embedded fields", "formula": "logical fetches avoided is bounded by min(embedded relationships, parsed join occurrences); this is a comparative heuristic, not a latency benchmark."}


def run_pipeline(ddl: str, queries: list[str], row_counts: dict[str, int] | None = None, overrides: dict[str, str] | None = None) -> dict:
    parsed = parse_ddl(ddl)
    workload = analyze_workload(queries, parsed["tables"])
    result = recommend(parsed, workload, row_counts, overrides)
    result["parsed_schema"] = parsed
    result["workload"] = workload
    result["tradeoffs"] = [{"decision": x["decision"], "relationship": x["relationship"], "evidence": x["evidence"], "benefit": x["benefit"], "tradeoff": x["tradeoff"], "reason": x["reason"]} for x in result["recommendations"]]
    return result
