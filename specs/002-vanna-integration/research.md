# Research: Vanna AI Integration

**Date**: 2025-12-31
**Feature**: 002-vanna-integration
**Purpose**: Resolve technical unknowns and document best practices

## Research Summary

All technical unknowns from the specification have been resolved through:
1. Vanna AI source code analysis (`/Users/lusain/ai/vanna`)
2. DB-GPT codebase exploration
3. User clarification session

---

## Decision 1: Vector Store Integration Pattern

**Question**: How should Vanna training data be stored using DB-GPT's existing vector store infrastructure?

**Decision**: Wrap DB-GPT's `VectorStoreBase` with three separate collections per database

**Rationale**:
- Vanna uses 3 separate collections: `ddl`, `sql`, `documentation` (source: `chromadb_vector.py`)
- Separate collections enable independent top-k tuning (e.g., more DDL, fewer SQL examples)
- DB-GPT already has ChromaStore, MilvusStore, PGVectorStore implementations
- Collection naming: `vanna_{db_name}_{type}` (e.g., `vanna_mydb_ddl`)

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Single collection with metadata filtering | Slower queries, harder to tune top-k per type |
| Vanna's native ChromaDB implementation | Doesn't reuse DB-GPT infrastructure, duplicate code |

**Implementation Pattern** (from Vanna source):
```python
# vanna/legacy/chromadb/chromadb_vector.py
self.ddl_collection = chroma_client.get_or_create_collection("ddl")
self.sql_collection = chroma_client.get_or_create_collection("sql")
self.documentation_collection = chroma_client.get_or_create_collection("documentation")
```

---

## Decision 2: Embedding Generation

**Question**: Should we use Vanna's embedding functions or DB-GPT's EmbeddingFactory?

**Decision**: Use DB-GPT's `EmbeddingFactory` exclusively

**Rationale**:
- DB-GPT already has unified embedding infrastructure
- Supports multiple backends (OpenAI, local models, etc.)
- User configuration already exists in DB-GPT
- Avoids duplicate embedding model configuration

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Vanna's default embedding | Requires separate configuration, not integrated with DB-GPT |
| Support both | Unnecessary complexity, violates YAGNI |

---

## Decision 3: Training Data ID Generation

**Question**: How should training data IDs be generated to support deduplication?

**Decision**: Use deterministic UUIDs based on content hash with type suffix

**Rationale** (from Vanna source `utils.py`):
```python
def deterministic_uuid(content: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, content))

# Usage:
id = deterministic_uuid(ddl) + "-ddl"      # DDL
id = deterministic_uuid(json.dumps({question, sql})) + "-sql"  # SQL
id = deterministic_uuid(documentation) + "-doc"  # Documentation
```

**Benefits**:
- Same content always produces same ID → automatic deduplication
- Type suffix enables easy filtering and deletion
- UUID format compatible with most storage systems

---

## Decision 4: ChatScene Integration

**Question**: How should Vanna context be injected into the SQL generation prompt?

**Decision**: Create new `ChatWithDbVanna` ChatScene extending `BaseChat`

**Rationale**:
- User clarified preference for separate scene vs extending existing
- Clean separation from `ChatWithDbExecute` and `ChatWithDbExecuteOntology`
- No risk of affecting existing functionality
- Can be enabled/disabled independently

**Context Injection Pattern**:
```python
# In ChatWithDbVanna.generate_input_values():
vanna_context = self.vanna_retriever.get_context(user_input, db_name)

input_values = {
    # ... existing values ...
    "vanna_ddl": vanna_context.ddl_list,
    "vanna_sql_examples": vanna_context.sql_examples,
    "vanna_documentation": vanna_context.documentation,
}
```

---

## Decision 5: Schema Auto-Training

**Question**: How should automatic schema training from database connections work?

**Decision**: Use existing `ConnectorManager` to extract DDL via `get_table_ddl()` or similar

**Rationale**:
- DB-GPT already has database connector infrastructure
- `DBSchemaRetriever` exists for schema extraction
- No need to reinvent database introspection

**Flow**:
1. User calls `POST /api/v1/vanna/train-schema/{db_name}`
2. Get connector from `ConnectorManager.get_connector(db_name)`
3. For each table: extract DDL statement
4. Call `VannaTrainingService.add_ddl(db_name, ddl)` for each

---

## Decision 6: Default Configuration Values

**Question**: What should be the default top-k values for retrieval?

**Decision**: Match Vanna defaults with slight reduction for token efficiency

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `n_results_ddl` | 5 | Schema context, more is better for accuracy |
| `n_results_sql` | 5 | SQL examples, quality over quantity |
| `n_results_documentation` | 3 | Documentation, usually less relevant |

**Vanna defaults**: All 10 (source: `chromadb_vector.py:25-29`)

**Our reduction rationale**: DB-GPT prompts already include table_info and other context; lower defaults reduce token usage while maintaining accuracy.

---

## Decision 7: API Design

**Question**: What API endpoints are needed for training data management?

**Decision**: RESTful API following DB-GPT patterns

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/vanna/train` | POST | Add training data (DDL/SQL/doc) |
| `/api/v1/vanna/train-schema/{db_name}` | POST | Auto-train from database |
| `/api/v1/vanna/training-data/{db_name}` | GET | List training data |
| `/api/v1/vanna/training-data/{id}` | DELETE | Remove training data |

**Request format** (JSON only per user clarification):
```json
{
  "db_name": "mydb",
  "type": "ddl|sql|documentation",
  "content": "CREATE TABLE...",
  "question": "optional for sql type"
}
```

---

## Best Practices from Vanna Source Code

### 1. Token Management
Vanna estimates tokens as `len(string) / 4` (source: `base.py`). We should track and limit total context size.

### 2. Prompt Section Structure
Vanna organizes context in clear sections:
- `===Tables` for DDL
- `===Additional Context` for documentation
- `===Question-SQL Pairs` for examples

We should follow similar structure for clarity.

### 3. Deduplication Before Storage
Check if content already exists before adding (deterministic UUID makes this trivial).

### 4. Graceful Fallback
When vector store is empty, fall back to table_info from database connection (already implemented in DB-GPT).

---

## Unresolved / Future Research

| Topic | Status | Notes |
|-------|--------|-------|
| Multi-tenant isolation | Deferred | Per user request, single-tenant for MVP |
| Milvus/PGVector backends | Deferred | ChromaDB only for MVP |
| Feedback/rating system | Deferred | Per user request |
| Performance benchmarking | Post-MVP | Need test dataset (Spider subset) |
