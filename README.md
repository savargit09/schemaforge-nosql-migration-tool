# Relational-to-NoSQL Schema Migration Tool

### Automated Denormalized Schema Recommendation with Trade-off Explanation

**BCSE406L – NoSQL Databases | Review 2 Prototype**

**Team:** Anish Jaiswal · Savar Gambhir · Sakthi

---

## 1. Project Overview

The **Relational-to-NoSQL Schema Migration Tool** is a workload-aware schema design assistant that helps convert a relational database design into a **MongoDB-oriented denormalized schema**.

The tool does not simply convert SQL tables into MongoDB collections. Instead, it analyzes:

- SQL table definitions
- Primary keys
- Foreign-key relationships
- Representative workload queries
- Table row counts
- Relationship cardinality
- Estimated foreign-key fan-out
- Query access patterns
- User-provided embedding/reference overrides

Based on this information, the system recommends whether related relational entities should be **embedded** or **referenced** in MongoDB.

For every recommendation, the system also provides a **trade-off explanation**, making the schema-design process transparent rather than treating it as a black-box conversion.

### Core idea

```text
Relational Schema + Workload + Cardinality
                    ↓
             Schema Analysis
                    ↓
          Embedding / Referencing
              Recommendation
                    ↓
          Trade-off Explanation
                    ↓
       MongoDB-Oriented Schema
                    ↓
             MongoDB Storage
```

The current Review 2 implementation targets **MongoDB**.

---

# 2. Problem Statement

Relational databases are generally designed around **normalization**, where information is separated into multiple tables and relationships are represented using foreign keys.

NoSQL document databases such as MongoDB use a different data-modeling philosophy. Related information may be **denormalized and embedded inside documents** to optimize common application access patterns.

Therefore, migrating a relational schema to MongoDB is not simply a matter of:

```text
SQL Table → MongoDB Collection
```

A useful migration requires decisions such as:

- Which entities should be embedded?
- Which entities should remain referenced?
- How does relationship cardinality affect the decision?
- How does fan-out affect document size and duplication?
- Which queries frequently access related entities together?
- When does denormalization improve read locality?
- When can embedding create excessive duplication or document growth?

The project addresses this problem using a **transparent, deterministic recommendation pipeline**.

---

# 3. Objectives

The main objectives of the project are:

1. Parse relational database definitions provided as SQL DDL.
2. Extract tables, columns, primary keys, and foreign keys.
3. Build a representation of relationships between relational entities.
4. Analyze representative SQL workload queries.
5. Estimate relationship fan-out using supplied row counts.
6. Identify query access patterns and relationship usage.
7. Recommend embedding or referencing strategies.
8. Generate a MongoDB-oriented document schema.
9. Explain the reasoning behind each recommendation.
10. Persist migration runs and generated artifacts in MongoDB.
11. Provide a web-based interface for submitting and reviewing migrations.
12. Provide APIs for accessing projects, schemas, workloads, migrations, recommendations, and generated schemas.

---

# 4. Key Features

### SQL Schema Analysis

The system accepts SQL DDL and extracts:

- Tables
- Columns
- Primary keys
- Foreign keys
- Relationships

### Workload Analysis

Representative SQL queries are analyzed to identify:

- Tables accessed
- JOIN relationships
- Filtering patterns
- Ordering
- Grouping
- Relationship access frequency

### Cardinality and Fan-out Analysis

The system uses supplied row counts to estimate relationship fan-out.

For example:

```text
40 orders
80 order_items
```

can provide evidence that the average number of order items per order is approximately:

```text
80 / 40 = 2 items per order
```

This information becomes one of the signals used by the recommendation engine.

### Embedding / Referencing Recommendations

The system determines whether relationships are better represented using:

```text
Embedding
```

or:

```text
Referencing
```

based on the available schema, workload, and cardinality evidence.

### Transparent Trade-off Explanation

Instead of returning only:

```text
Recommendation: EMBED
```

the system provides the reasoning and relevant evidence behind the decision.

### MongoDB Schema Generation

The recommendation is converted into a MongoDB-oriented document schema.

### Persistent Migration History

Migration runs and generated artifacts are stored in MongoDB so previous runs can be retrieved.

### Web Dashboard

A React-based interface allows users to:

- Create migrations
- Submit SQL DDL
- Provide workload queries
- Provide row counts
- Review recommendations
- Inspect generated schemas
- View migration history

---

# 5. System Architecture

```text
┌──────────────────────────────────────┐
│          React + Vite UI             │
│                                      │
│  New Migration │ Results │ History   │
└───────────────────┬──────────────────┘
                    │ HTTP / REST
                    ▼
┌──────────────────────────────────────┐
│          FastAPI Backend             │
│                                      │
│  Pydantic Models                     │
│  API Routes                          │
│  Migration Orchestration             │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│       Analysis Pipeline              │
│                                      │
│  SQLGlot Parser                      │
│       ↓                              │
│  Workload Analyzer                   │
│       ↓                              │
│  Relational Graph                    │
│       ↓                              │
│  Fan-out / Cardinality Analysis      │
│       ↓                              │
│  Deterministic Rule Engine           │
│       ↓                              │
│  Schema Generator                    │
│       ↓                              │
│  Trade-off Generator                 │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│             PyMongo                  │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│          MongoDB Atlas               │
│                                      │
│ projects                             │
│ schemas                              │
│ workloads                            │
│ migration_runs                       │
│ generated_schemas                    │
│ tradeoff_reports                     │
└──────────────────────────────────────┘
```

---

# 6. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Build Tool | Vite |
| Backend | FastAPI |
| API Validation | Pydantic |
| SQL Parsing | SQLGlot |
| Database Driver | PyMongo |
| Target Database | MongoDB |
| Cloud Database | MongoDB Atlas |
| Frontend Styling | Tailwind CSS |
| API Documentation | FastAPI / OpenAPI / Swagger |
| Testing | Pytest |
| Programming Languages | Python, JavaScript |

---

# 7. How the System Works

The migration process follows a sequence of analysis stages.

## Step 1 — Input Relational Schema

The user provides SQL DDL containing tables, columns, primary keys, and foreign keys.

Example:

```sql
CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    order_date DATE,
    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);
```

---

## Step 2 — SQL Parsing

The backend uses **SQLGlot** to parse the SQL structure.

The parser identifies:

```text
Tables
Columns
Primary Keys
Foreign Keys
Relationships
```

This information is converted into an internal representation used by the rest of the migration pipeline.

---

## Step 3 — Relational Graph Construction

The relationships between tables are represented as a graph.

For example:

```text
Customer
   │
   │ 1 : N
   ▼
 Order
   │
   │ 1 : N
   ▼
OrderItem
```

This graph allows the system to reason about relationships rather than treating tables independently.

---

## Step 4 — Workload Analysis

Representative queries are analyzed to determine how the database is expected to be accessed.

For example:

```sql
SELECT o.order_id, c.name
FROM orders o
JOIN customers c
ON o.customer_id = c.customer_id;
```

The system can identify that:

```text
orders ↔ customers
```

is an actively accessed relationship.

Workload information therefore becomes an important signal for schema design.

---

## Step 5 — Fan-out Estimation

If row counts are provided, the system estimates relationship fan-out.

For example:

```text
Customers = 15
Orders    = 40
```

An approximate average order fan-out can be estimated as:

```text
40 / 15 ≈ 2.67
```

Similarly:

```text
Orders      = 40
Order Items = 80
```

gives:

```text
80 / 40 = 2 items per order
```

These values are treated as evidence rather than measured production statistics.

---

## Step 6 — Recommendation Engine

The system applies deterministic heuristics to available signals such as:

- Relationship structure
- Cardinality
- Fan-out
- Workload access patterns
- Query locality
- Potential duplication
- Document growth considerations
- Explicit user overrides

The result is a recommendation such as:

```text
EMBED
```

or:

```text
REFERENCE
```

---

# 8. Embedding vs Referencing

This is one of the most important concepts in the project.

## Embedding

Embedding stores related information directly inside a MongoDB document.

Example:

```json
{
  "_id": 101,
  "customer_id": 5,
  "items": [
    {
      "product_id": 10,
      "quantity": 2
    },
    {
      "product_id": 20,
      "quantity": 1
    }
  ]
}
```

### Advantages

- Related information can be retrieved together.
- Reduces the need for joins.
- Improves read locality.
- Represents tightly coupled data naturally.

### Disadvantages

- Can increase document size.
- Can duplicate information.
- Updates to duplicated data can become more difficult.

---

## Referencing

Referencing keeps related entities separately and stores an identifier.

Example:

```json
{
  "_id": 101,
  "customer_id": 5
}
```

The customer information remains in another collection.

### Advantages

- Reduces duplication.
- Better for independently changing entities.
- Useful when related data has high or unpredictable growth.

### Disadvantages

- Requires additional lookups.
- Can increase query complexity.
- Related data is not stored together.

---

# 9. Core Concepts

Understanding the following concepts is important for understanding this project.

## Relational Database

A database where data is organized into tables and relationships are represented using keys.

Example:

```text
customers
orders
products
order_items
```

---

## NoSQL Database

A class of databases designed around data models other than the traditional relational table model.

MongoDB uses a **document-oriented model**.

---

## Normalization

Normalization separates data into multiple related tables to reduce redundancy and update anomalies.

Example:

```text
Customer
   ↓
Orders
   ↓
Order Items
```

---

## Denormalization

Denormalization intentionally combines related information to reduce the amount of work required to retrieve frequently accessed data.

MongoDB schema design often uses denormalization through embedding.

---

## Cardinality

Cardinality describes the relationship between entities.

Common examples:

```text
1 : 1
1 : N
N : N
```

For example:

```text
One customer → Many orders
```

is a:

```text
1 : N
```

relationship.

---

## Fan-out

Fan-out describes how many related child records exist per parent.

For example:

```text
40 orders
80 order items
```

gives an average fan-out of:

```text
2 items per order
```

High fan-out can influence whether embedding is appropriate.

---

## Query Locality

Query locality refers to how frequently related information is accessed together.

If an application frequently retrieves:

```text
Order + Order Items
```

together, embedding the order items may improve read locality.

---

## Workload-Aware Schema Design

Instead of designing a MongoDB schema only from the original relational structure, the project considers **how the data is actually queried**.

This is a central principle of the project.

---

# 10. Why This Is Not Just an SQL-to-Mongo Converter

A simple converter might perform:

```text
SQL Table → MongoDB Collection
```

Our system instead performs:

```text
SQL Schema
    ↓
Relationship Analysis
    ↓
Workload Analysis
    ↓
Cardinality / Fan-out Analysis
    ↓
Schema Recommendation
    ↓
Trade-off Explanation
    ↓
MongoDB Schema
```

The main contribution of the project is therefore the **decision-support layer** between the relational schema and the generated MongoDB model.

---

# 11. Recommendation Philosophy

The recommendation system is intentionally **deterministic and transparent**.

It does not claim to be a machine-learning model or benchmark-derived optimizer.

Instead, it applies explicit rules to observable signals.

Conceptually:

```text
Relationship
     +
Cardinality
     +
Fan-out
     +
Workload
     +
Query locality
     +
User override
     ↓
Recommendation
     ↓
Explanation
```

This makes the system easier to:

- Understand
- Debug
- Demonstrate
- Validate
- Extend

---

# 12. User Overrides

The system also supports explicit embedding/reference overrides.

This is useful because automated heuristics cannot capture every application-specific requirement.

Therefore, the user can explicitly influence the generated schema when domain knowledge should take priority over the default recommendation.

---

# 13. MongoDB Data Model

The application persists migration-related information in MongoDB.

### `projects`

Stores project-level metadata.

### `schemas`

Stores submitted relational schemas and parsed schema information.

### `workloads`

Stores representative workload queries and their analysis.

### `migration_runs`

Stores migration execution information and results.

### `generated_schemas`

Stores generated MongoDB-oriented schemas.

### `tradeoff_reports`

Stores the reasoning and trade-off explanations associated with recommendations.

---

# 14. MongoDB Atlas Setup

The current project uses **MongoDB Atlas** as the database backend.

Create a MongoDB Atlas cluster and obtain its connection string.

The backend reads the following environment variables:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-hostname>/
MONGODB_DATABASE=nosql_migration_tool
CORS_ORIGINS=http://localhost:5173
```

### Important

Do **not** commit your actual `.env` file.

Your `.gitignore` excludes:

```text
.env
backend/.env
```

Only the example configuration should be committed.

---

# 15. Project Structure

```text
project/
│
├── backend/
│   ├── app/
│   │   └── ...
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── pyproject.toml
│
├── database/
│   ├── sample_data/
│   ├── backup.py
│   └── ...
│
├── docs/
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── .gitignore
└── README.md
```

---

# 16. Prerequisites

Install the following:

- **Python 3.11 or newer**
- **Node.js 20 or newer**
- **MongoDB Atlas account**
- **Git**

Verify Python:

```powershell
python --version
```

Verify Node:

```powershell
node --version
```

Verify npm:

```powershell
npm --version
```

Verify Git:

```powershell
git --version
```

---

# 17. Backend Setup

From the project root:

```powershell
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

Create the backend environment file:

```powershell
Copy-Item backend/.env.example backend/.env
```

Then edit:

```text
backend/.env
```

and add your MongoDB Atlas connection information.

---

# 18. Start the Backend

From the project root:

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload --port 8000
```

The backend should be available at:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# 19. Frontend Setup

Open another terminal.

From the project root:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

The frontend should be available at:

```text
http://localhost:5173
```

---

# 20. Running the Complete Application

Two terminals are normally required.

### Terminal 1 — Backend

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — Frontend

```powershell
cd frontend
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

# 21. Demonstration Workflow

A typical demonstration follows these steps:

### 1. Open the dashboard

Launch the React frontend.

### 2. Verify database connection

The application should indicate whether MongoDB is connected.

### 3. Create a migration

Provide:

- Project name
- SQL DDL
- Row counts
- Representative workload
- Optional relationship overrides

### 4. Run migration

The backend processes the input through the analysis pipeline.

### 5. Inspect recommendations

Review:

- Parsed entities
- Relationships
- Query access patterns
- Cardinality information
- Fan-out evidence
- Embed/reference decisions

### 6. Inspect generated schema

Review the MongoDB-oriented schema generated by the recommendation engine.

### 7. Inspect trade-offs

Review why each relationship received its recommendation.

### 8. Check migration history

Previously executed migrations can be retrieved from MongoDB.

---

# 22. Example Dataset

The project includes an order-management example involving entities such as:

```text
Customer
Product
Order
OrderItem
```

Conceptually:

```text
Customer
   │
   │ 1:N
   ▼
 Order
   │
   │ 1:N
   ▼
OrderItem
   │
   │ N:1
   ▼
 Product
```

Representative row counts used by the demonstration include:

```text
Customers     = 15
Products      = 20
Orders        = 40
Order Items   = 80
```

These values are used as input evidence for schema recommendation and demonstration purposes.

---

# 23. API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check API and MongoDB availability |
| GET | `/api/metrics` | Retrieve persisted dashboard metrics |
| POST/GET/PUT/DELETE | `/api/projects` | Project management |
| POST/GET/PUT/DELETE | `/api/schemas` | Source schema management |
| POST/GET/PUT/DELETE | `/api/workloads` | Workload management |
| POST | `/api/migrations` | Run migration analysis |
| GET | `/api/migrations` | Retrieve migration history |
| GET | `/api/migrations/{id}` | Retrieve a migration |
| GET | `/api/migrations/{id}/recommendations` | Retrieve recommendations |
| GET | `/api/migrations/{id}/tradeoffs` | Retrieve trade-off explanations |
| GET | `/api/generated-schemas/{id}` | Retrieve generated schema |
| GET | `/api/database/collections` | Inspect collection counts and indexes |

Detailed request and response schemas are available through FastAPI's OpenAPI documentation.

---

# 24. Testing

The backend test suite can be executed using:

```powershell
$env:PYTHONPATH = "backend"
pytest backend/tests -q
```

The project also includes integration-oriented verification of:

- API functionality
- MongoDB connectivity
- Persistence
- Migration execution
- Generated schema storage
- Migration history
- Database collections

---

# 25. Build Verification

The frontend production build can be tested with:

```powershell
cd frontend
npm run build
```

A successful build confirms that the frontend can be compiled for production deployment.

---

# 26. Current Scope — Review 2

The implemented Review 2 prototype focuses on:

- MongoDB as the NoSQL target
- SQL DDL parsing
- Relational schema analysis
- Relationship graph construction
- Workload analysis
- Fan-out estimation
- Cardinality-based reasoning
- Deterministic schema recommendation
- Embedding/reference decisions
- Trade-off explanations
- MongoDB schema generation
- MongoDB persistence
- REST APIs
- React dashboard
- Migration history
- Generated schema retrieval
- Testing and verification

---

# 27. Current Limitations

The current system has deliberately defined boundaries.

### No live relational database migration

The current prototype analyzes SQL DDL and representative workloads.

It does not currently connect directly to a production relational database and migrate its live data.

### Heuristic recommendations

Recommendations are based on explicit deterministic rules.

They are not claimed to be:

- Machine-learning predictions
- Benchmark-derived performance guarantees
- Production workload measurements

### Limited SQL coverage

The parser focuses on common relational constructs and workload patterns supported by the implemented SQLGlot analysis.

Unsupported SQL shapes may require additional handling.

### Fan-out estimation

Fan-out is estimated from supplied row counts.

If row counts are missing, the system cannot calculate the corresponding evidence.

### No measured latency model

The cost indicators describe logical schema/query characteristics.

They are not actual database latency measurements.

---

# 28. Review 3 / Future Work

Potential future extensions include:

### Live Relational Database ETL

Connect directly to a relational database and migrate actual records into generated MongoDB collections.

### Broader SQL Support

Improve support for:

- Additional SQL dialects
- Complex queries
- More relationship types
- Additional SQL semantics

### Cassandra Support

Extend the architecture to generate schemas for Cassandra in addition to MongoDB.

### Improved Cost Modelling

Introduce calibrated cost models based on measured workload performance.

### Workload Import

Allow workloads to be imported from real application logs or query histories.

### Richer Override Interface

Provide a more advanced UI for manually controlling embedding and referencing decisions.

### Performance Evaluation

Compare alternative schema designs using measurable:

- Query latency
- Throughput
- Storage usage
- Document growth
- Read/write performance

---

# 29. Design Philosophy

The project follows three major principles.

### Transparency

Every recommendation should be understandable.

### Workload Awareness

Schema design should consider how the data is accessed, not only how it is structured.

### Extensibility

The architecture separates:

```text
Parsing
Analysis
Recommendation
Generation
Persistence
Presentation
```

This allows future NoSQL targets and improved recommendation strategies to be added without completely redesigning the system.

---

# 30. Why This Project Matters

Traditional relational schema design emphasizes normalization and minimizing redundancy.

Document databases introduce a different design philosophy where the schema should often be shaped around **application access patterns**.

Therefore, moving from SQL to MongoDB requires a design decision rather than a direct format conversion.

This project attempts to make that decision process:

```text
Structured
    +
Workload-aware
    +
Explainable
    +
Reproducible
```

rather than relying on an opaque automatic conversion.

---

# 31. Academic Context

**Course:** BCSE406L – NoSQL Databases

**Project:** Relational-to-NoSQL Schema Migration Tool

**Project Type:** Review 2 Prototype

**Target NoSQL Database:** MongoDB

**Team Members:**

- Anish Jaiswal
- Savar Gambhir
- Sakthi

---

# 32. Repository Safety

The repository intentionally excludes local and sensitive files such as:

```text
.env
backend/.env
.venv/
node_modules/
frontend/dist/
__pycache__/
database/dump/
```

**Never commit MongoDB Atlas usernames, passwords, connection strings, API keys, or other secrets.**

Use:

```text
backend/.env.example
```

for sharing the required environment-variable structure.

---

# 33. License

This project was developed as an academic project for **BCSE406L – NoSQL Databases**.
