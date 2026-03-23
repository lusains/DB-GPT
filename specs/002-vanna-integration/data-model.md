# Data Model: Vanna AI Integration

**Date**: 2025-12-31
**Feature**: 002-vanna-integration

## Entity Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  TrainingData   │     │  TrainingStore   │     │  VannaContext   │
│  (DDL/SQL/Doc)  │────▶│  (per database)  │────▶│  (per query)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
   Vector Store            ChromaDB Client           Prompt Builder
   (embeddings)            (3 collections)           (LLM context)
```

---

## Core Entities

### 1. TrainingDataType (Enum)

```python
class TrainingDataType(str, Enum):
    """Type of training data content."""
    DDL = "ddl"              # CREATE TABLE statements
    SQL = "sql"              # Question-SQL pairs
    DOCUMENTATION = "doc"    # Business documentation
```

### 2. TrainingData

Represents a single piece of training content stored in the vector store.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | str | Unique identifier | Format: `{uuid}-{type}` (e.g., `abc123-ddl`) |
| `db_name` | str | Associated database name | Required, non-empty |
| `type` | TrainingDataType | Content type | Required |
| `content` | str | The actual content (DDL/SQL/doc text) | Required, non-empty |
| `question` | Optional[str] | Natural language description | Required for SQL type |
| `created_at` | datetime | Creation timestamp | Auto-generated |
| `metadata` | Dict[str, Any] | Additional metadata | Optional |

**Validation Rules**:
- `id` is generated deterministically from content hash + type suffix
- If `type == SQL`, `question` must be provided
- `content` must be non-empty string
- `db_name` must match an existing database connection

**Python Definition**:
```python
@dataclass
class TrainingData:
    id: str
    db_name: str
    type: TrainingDataType
    content: str
    question: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.type == TrainingDataType.SQL and not self.question:
            raise ValueError("question is required for SQL training data")
        if not self.content:
            raise ValueError("content cannot be empty")
```

---

### 3. VannaContext

Retrieved context bundle for a specific query, used to enhance LLM prompts.

| Field | Type | Description |
|-------|------|-------------|
| `ddl_list` | List[str] | Retrieved DDL statements |
| `sql_examples` | List[QuestionSqlPair] | Retrieved SQL examples |
| `documentation` | List[str] | Retrieved documentation |
| `total_tokens` | int | Estimated token count |

**Python Definition**:
```python
@dataclass
class QuestionSqlPair:
    question: str
    sql: str

@dataclass
class VannaContext:
    ddl_list: List[str] = field(default_factory=list)
    sql_examples: List[QuestionSqlPair] = field(default_factory=list)
    documentation: List[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        """Estimate token count (len / 4 approximation)."""
        total = sum(len(ddl) for ddl in self.ddl_list)
        total += sum(len(ex.question) + len(ex.sql) for ex in self.sql_examples)
        total += sum(len(doc) for doc in self.documentation)
        return total // 4

    def is_empty(self) -> bool:
        return not (self.ddl_list or self.sql_examples or self.documentation)
```

---

### 4. VannaConfig

Configuration for Vanna training and retrieval behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | True | Enable/disable Vanna features |
| `vector_store_type` | str | "chroma" | Vector store backend |
| `chroma_path` | str | "./vanna_data" | ChromaDB persistence path |
| `n_results_ddl` | int | 5 | Top-k for DDL retrieval |
| `n_results_sql` | int | 5 | Top-k for SQL retrieval |
| `n_results_doc` | int | 3 | Top-k for documentation retrieval |
| `max_context_tokens` | int | 4000 | Maximum tokens for context |

**Python Definition**:
```python
@dataclass
class VannaConfig:
    enabled: bool = True
    vector_store_type: str = "chroma"
    chroma_path: str = "./vanna_data"
    n_results_ddl: int = 5
    n_results_sql: int = 5
    n_results_doc: int = 3
    max_context_tokens: int = 4000
```

---

### 5. TrainingRequest (API)

Request model for adding training data via API.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `db_name` | str | Yes | Target database name |
| `type` | str | Yes | "ddl", "sql", or "documentation" |
| `content` | str | Yes | Training content |
| `question` | str | Conditional | Required if type is "sql" |

**Validation**:
- `type` must be one of: "ddl", "sql", "documentation"
- `question` required when `type == "sql"`

---

### 6. TrainingResponse (API)

Response model for training operations.

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Operation success status |
| `id` | Optional[str] | Created training data ID |
| `message` | str | Success/error message |

---

## State Transitions

### TrainingData Lifecycle

```
                    ┌──────────┐
                    │  Create  │
                    └────┬─────┘
                         │
                         ▼
    ┌────────────────────────────────────┐
    │            STORED                   │
    │  (in vector store with embedding)   │
    └────────────────┬───────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────┐            ┌──────────┐
    │ Retrieve│            │  Delete  │
    │ (query) │            │          │
    └─────────┘            └──────────┘
```

**Notes**:
- No "update" operation - delete and recreate instead (simpler, deterministic IDs handle dedup)
- Retrieval is based on semantic similarity to query
- Deletion removes from vector store, embeddings are lost

---

## Storage Schema

### ChromaDB Collections (per database)

| Collection Name | Document Format | Metadata |
|----------------|-----------------|----------|
| `vanna_{db_name}_ddl` | DDL statement text | `{created_at, table_name}` |
| `vanna_{db_name}_sql` | JSON: `{question, sql}` | `{created_at}` |
| `vanna_{db_name}_doc` | Documentation text | `{created_at, topic}` |

**Example Collection Names**:
- `vanna_mydb_ddl`
- `vanna_mydb_sql`
- `vanna_mydb_doc`

---

## Relationships

```
Database Connection (DB-GPT)
        │
        │ 1:N
        ▼
TrainingData (many per database)
        │
        │ stored in
        ▼
Vector Store Collection (3 per database)
        │
        │ retrieved by
        ▼
VannaContext (constructed per query)
        │
        │ injected into
        ▼
ChatWithDbVanna Prompt
```

---

## Index Strategy

| Collection | Index Type | Purpose |
|------------|------------|---------|
| DDL | Vector (embedding) | Semantic search for relevant tables |
| SQL | Vector (embedding) | Find similar question patterns |
| Documentation | Vector (embedding) | Match business terms to docs |

All collections use the same embedding model from DB-GPT's `EmbeddingFactory`.
