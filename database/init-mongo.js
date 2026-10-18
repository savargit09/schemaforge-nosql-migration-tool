db = db.getSiblingDB('nosql_migration_tool');
['projects','schemas','workloads','migration_runs','generated_schemas','tradeoff_reports'].forEach(n => db.createCollection(n));
db.projects.createIndex({name:1});
db.schemas.createIndex({project_id:1,created_at:-1});
db.workloads.createIndex({project_id:1,created_at:-1});
db.migration_runs.createIndex({project_id:1,created_at:-1});
db.generated_schemas.createIndex({migration_id:1},{unique:true});
db.tradeoff_reports.createIndex({migration_id:1},{unique:true});
