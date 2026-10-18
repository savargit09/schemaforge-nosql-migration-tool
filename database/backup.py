"""Portable Extended JSON backup/restore for all collections in the configured DB."""
import argparse
import json
import os
from pathlib import Path
from bson import json_util
from pymongo import MongoClient


def dump(uri: str, database: str, output: Path) -> None:
    client = MongoClient(uri, serverSelectionTimeoutMS=2500)
    client.admin.command("ping")
    db = client[database]
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"database": database, "collections": []}
    for name in sorted(db.list_collection_names()):
        rows = list(db[name].find({}))
        (output / f"{name}.json").write_text(json_util.dumps(rows, indent=2), encoding="utf-8")
        indexes = []
        for index_name, spec in db[name].index_information().items():
            if index_name == "_id_":
                continue
            indexes.append({"name": index_name, "keys": list(spec["key"]), **{k:spec[k] for k in ("unique","sparse","expireAfterSeconds") if k in spec}})
        manifest["collections"].append({"name":name,"document_count":len(rows),"indexes":indexes})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    client.close()
    print(f"Exported {len(manifest['collections'])} collections from {database} to {output}")


def restore(uri: str, database: str, source: Path) -> None:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest["database"] != database:
        raise ValueError(f"Backup database {manifest['database']} does not match target {database}")
    client = MongoClient(uri, serverSelectionTimeoutMS=2500)
    client.admin.command("ping")
    db = client[database]
    for item in manifest["collections"]:
        name = item["name"]
        if name in db.list_collection_names():
            db.drop_collection(name)
        rows = json_util.loads((source / f"{name}.json").read_text(encoding="utf-8"))
        if rows:
            db[name].insert_many(rows)
        for index in item["indexes"]:
            db[name].create_index(index["keys"], name=index["name"], **{k:index[k] for k in ("unique","sparse","expireAfterSeconds") if k in index})
        print(f"Restored {name}: {len(rows)} documents")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["dump","restore"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database = os.getenv("MONGODB_DATABASE", "nosql_migration_tool")
    dump(uri,database,args.path) if args.action == "dump" else restore(uri,database,args.path)
