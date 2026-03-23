# Feature Specification: Vanna AI Integration for Enhanced Text-to-SQL

**Feature Branch**: `002-vanna-integration`
**Created**: 2025-12-31
**Status**: Draft
**Input**: User description: "充分调研vanna-ai/vanna，如何集成到当前db-gpt中，特别是scheme学习、RAG增强等等优秀功能。尽量以扩展的方式接入到db-gpt"

## Executive Summary

Integrate Vanna AI's core RAG (Retrieval-Augmented Generation) capabilities into DB-GPT to enhance Text-to-SQL accuracy. Key features to integrate:
- **Schema Learning**: Automatic DDL extraction and storage for context-aware SQL generation
- **RAG Enhancement**: Vector-based retrieval of SQL examples, DDL, and documentation
- **Training Pipeline**: Support for DDL, documentation, and SQL example training data
- **Multi-Source Context**: Combine schema, documentation, and historical queries for better SQL generation

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Train Schema from Database (Priority: P1)

As a database administrator, I want to automatically train the system with my database schema so that it understands my table structures for accurate SQL generation.

**Why this priority**: Schema understanding is the foundation for accurate SQL generation. Without proper schema context, the system cannot generate correct table/column references.

**Independent Test**: Can be fully tested by connecting to a database and verifying that all table DDL statements are extracted, embedded, and stored in the vector store. Delivers immediate value for single-database SQL generation.

**Acceptance Scenarios**:

1. **Given** a connected MySQL/PostgreSQL database, **When** user initiates schema training, **Then** all table DDL statements are extracted and stored in the training store
2. **Given** a database with 50+ tables, **When** schema training completes, **Then** all tables are indexed and searchable by semantic similarity
3. **Given** an updated database schema (new columns added), **When** user re-trains schema, **Then** the training store reflects the latest schema changes

---

### User Story 2 - Train with SQL Examples (Priority: P2)

As a data analyst, I want to provide example SQL queries so that the system learns our specific query patterns and business logic.

**Why this priority**: SQL examples teach the system domain-specific query patterns that cannot be inferred from schema alone. This significantly improves accuracy for complex joins and business logic.

**Independent Test**: Can be fully tested by adding SQL examples and verifying they are retrieved when asking similar questions. Delivers value by improving SQL accuracy for trained query patterns.

**Acceptance Scenarios**:

1. **Given** a user provides 10 example SQL queries with natural language descriptions, **When** training completes, **Then** similar questions retrieve the relevant examples as context
2. **Given** a trained SQL example "SELECT SUM(amount) FROM orders WHERE customer_id = ?", **When** user asks "What is the total order amount for customer X?", **Then** the example is retrieved and used as context
3. **Given** existing trained examples, **When** user adds new examples, **Then** both old and new examples are searchable

---

### User Story 3 - Train with Documentation (Priority: P2)

As a business analyst, I want to add business documentation (field meanings, business rules) so that the system understands our domain terminology.

**Why this priority**: Documentation bridges the gap between business language and database columns. Critical for translating terms like "revenue" to specific column calculations.

**Independent Test**: Can be fully tested by adding documentation and verifying it's retrieved for relevant queries. Delivers value by improving natural language understanding.

**Acceptance Scenarios**:

1. **Given** documentation stating "revenue means sales_amount minus discount", **When** user asks about revenue, **Then** the documentation is retrieved as context
2. **Given** column-level documentation, **When** user references a column by its business name, **Then** the correct technical column is identified
3. **Given** multiple documentation entries, **When** a query matches several topics, **Then** the most relevant entries are retrieved (ranked by similarity)

---

### User Story 4 - RAG-Enhanced SQL Generation (Priority: P1)

As a user, I want the system to use trained context (schema, SQL examples, documentation) when generating SQL so that queries are more accurate.

**Why this priority**: This is the core value proposition - combining all training data to generate accurate SQL. Essential for the integration to provide measurable improvement.

**Independent Test**: Can be fully tested by comparing SQL accuracy with and without RAG context. Delivers the primary value of improved SQL generation accuracy.

**Acceptance Scenarios**:

1. **Given** trained schema and SQL examples, **When** user asks a natural language question, **Then** relevant context is retrieved and included in LLM prompt
2. **Given** a question similar to a trained example, **When** SQL is generated, **Then** the generated SQL follows the pattern of the trained example
3. **Given** ambiguous column references, **When** documentation is available, **Then** the correct column is selected based on documentation context

---

### User Story 5 - Manage Training Data (Priority: P3)

As an administrator, I want to view, edit, and delete training data so that I can maintain the quality of the knowledge base.

**Why this priority**: Maintenance is important for long-term usability but not required for initial functionality.

**Independent Test**: Can be fully tested by performing CRUD operations on training data through API or UI.

**Acceptance Scenarios**:

1. **Given** existing training data, **When** admin requests training data list, **Then** all DDL, SQL examples, and documentation entries are listed with metadata
2. **Given** incorrect training data, **When** admin deletes an entry, **Then** the entry is removed from the vector store and no longer retrieved
3. **Given** a training entry needs update, **When** admin modifies the content, **Then** the updated content is used in subsequent retrievals

---

### Edge Cases

- What happens when the vector store is empty (no training data)? System should fall back to using only table structure from database connection.
- How does the system handle conflicting information between DDL and documentation? DDL takes precedence for schema structure; documentation provides semantic context.
- What happens when schema changes but training data is outdated? System should detect schema changes and recommend re-training.
- How does the system handle very large schemas (1000+ tables)? Batch processing with progress indication and incremental training support.

## Requirements *(mandatory)*

### Functional Requirements

#### Training System

- **FR-001**: System MUST support training with DDL statements (CREATE TABLE, column definitions, constraints)
- **FR-002**: System MUST support training with SQL query examples paired with natural language descriptions
- **FR-003**: System MUST support training with documentation (business terms, field meanings, query patterns)
- **FR-004**: System MUST store training data in a vector store with semantic embeddings
- **FR-005**: System MUST support automatic schema extraction from connected databases (MySQL, PostgreSQL, SQLite)
- **FR-006**: System MUST deduplicate training data to prevent redundant entries

#### Retrieval System

- **FR-007**: System MUST retrieve relevant DDL based on user question similarity
- **FR-008**: System MUST retrieve relevant SQL examples based on question similarity
- **FR-009**: System MUST retrieve relevant documentation based on question content
- **FR-010**: System MUST combine retrieved context into a structured prompt format
- **FR-011**: System MUST support configurable top-k retrieval for each context type

#### Integration

- **FR-012**: System MUST integrate as an extension module, not modifying core DB-GPT code
- **FR-013**: System MUST use DB-GPT's existing VectorStoreBase interface for storage
- **FR-014**: System MUST use DB-GPT's existing EmbeddingFactory for embeddings
- **FR-015**: System MUST work with existing ChatScene (ChatWithDbExecute, ChatWithDbExecuteOntology)
- **FR-016**: System MUST provide configuration options for enabling/disabling Vanna features

#### Management API

- **FR-017**: System MUST provide API endpoints for adding training data (DDL, SQL, documentation)
- **FR-018**: System MUST provide API endpoints for listing training data with filtering
- **FR-019**: System MUST provide API endpoints for deleting training data
- **FR-020**: System MUST provide API endpoint for triggering schema training from database

### Key Entities

- **TrainingData**: Represents a piece of training content (type: DDL/SQL/Documentation, content, metadata, embedding_id)
- **TrainingStore**: Collection of TrainingData for a specific database/domain, backed by vector store
- **VannaContext**: Retrieved context bundle (DDL list, SQL examples, documentation) for a query
- **TrainingConfig**: Configuration for training behavior (embedding model, vector store type, top-k settings)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: SQL generation accuracy improves by at least 20% when using Vanna RAG context compared to base schema-only approach (measured on benchmark queries)
- **SC-002**: Schema training for a 100-table database completes within 5 minutes
- **SC-003**: Context retrieval for a query completes within 500ms
- **SC-004**: System supports at least 10,000 training entries per database without performance degradation
- **SC-005**: Users can successfully train and query the system without code modifications to existing DB-GPT installation
- **SC-006**: Training data management operations (add, list, delete) complete within 2 seconds for single operations

## Assumptions

1. DB-GPT's existing VectorStoreBase implementations (ChromaDB, Milvus, PGVector) are sufficient for Vanna training data storage
2. DB-GPT's existing EmbeddingFactory provides embeddings compatible with Vanna's semantic search requirements
3. The integration will be implemented as a new package (dbgpt-ext-vanna) following DB-GPT's extension pattern
4. Users have existing database connections configured in DB-GPT before using Vanna features
5. The initial implementation will focus on single-database training; multi-database support can be added later
6. Performance benchmarks will use a standardized query set (e.g., Spider benchmark subset) for accuracy measurement

## Design Decisions (Clarified)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Package Structure** | New `dbgpt-ext-vanna` package | Clean separation, easier distribution, follows DB-GPT extension pattern |
| **Default Vector Store** | ChromaDB | Lightweight, file-based, good for development and small deployments |
| **Integration Pattern** | New ChatScene: `ChatWithDbVanna` | Clean separation, doesn't affect existing ChatWithDbExecute behavior |
| **Import Format** | JSON files only (initial) | Simple to implement, structured format for DDL/SQL/docs |

## Out of Scope

1. Vanna's Flask/FastAPI server deployment (use DB-GPT's existing server)
2. Vanna's built-in visualization features (use DB-GPT's existing visualization)
3. Vanna's conversation history (use DB-GPT's existing chat history)
4. Fine-tuning LLM models (only RAG-based context enhancement)
5. Multi-tenant training data isolation (single-tenant per deployment)

## Technical Research Summary

### Vanna AI Architecture Analysis (from source code review)

#### Core Components (`vanna/legacy/base/base.py`)

**VannaBase Abstract Class** - The foundation class requiring these abstract methods:
- `generate_embedding(data: str) -> List[float]` - Generate embeddings for content
- `add_question_sql(question: str, sql: str) -> str` - Add Q&A training pair
- `add_ddl(ddl: str) -> str` - Add DDL statement
- `add_documentation(documentation: str) -> str` - Add documentation
- `get_similar_question_sql(question: str) -> list` - Retrieve similar Q&A pairs
- `get_related_ddl(question: str) -> list` - Retrieve relevant DDL
- `get_related_documentation(question: str) -> list` - Retrieve relevant docs
- `get_training_data() -> pd.DataFrame` - List all training data
- `remove_training_data(id: str) -> bool` - Delete training data

**Key Method - `generate_sql()`**:
```python
# Vanna's SQL generation flow:
1. question_sql_list = self.get_similar_question_sql(question)  # RAG retrieval
2. ddl_list = self.get_related_ddl(question)                    # RAG retrieval
3. doc_list = self.get_related_documentation(question)          # RAG retrieval
4. prompt = self.get_sql_prompt(question, question_sql_list, ddl_list, doc_list)
5. llm_response = self.submit_prompt(prompt)
6. return self.extract_sql(llm_response)
```

**Training Pipeline - `train()` method**:
- `train(ddl=...)` → Calls `add_ddl()`
- `train(sql=...)` → Calls `add_question_sql()` (auto-generates question if missing)
- `train(documentation=...)` → Calls `add_documentation()`
- `train(plan=TrainingPlan)` → Batch process multiple items

**TrainingPlan & TrainingPlanItem** (`vanna/legacy/types/__init__.py`):
- `ITEM_TYPE_SQL = "sql"` - SQL question-answer pairs
- `ITEM_TYPE_DDL = "ddl"` - DDL statements
- `ITEM_TYPE_IS = "is"` - Information Schema (column metadata as documentation)

#### Vector Store Integration Pattern (`vanna/legacy/chromadb/chromadb_vector.py`)

**ChromaDB Implementation** - Three separate collections:
```python
self.documentation_collection = chroma_client.get_or_create_collection("documentation")
self.ddl_collection = chroma_client.get_or_create_collection("ddl")
self.sql_collection = chroma_client.get_or_create_collection("sql")
```

**ID Generation Pattern** - Deterministic UUIDs with type suffix:
- DDL: `deterministic_uuid(ddl) + "-ddl"`
- SQL: `deterministic_uuid(json.dumps({question, sql})) + "-sql"`
- Doc: `deterministic_uuid(documentation) + "-doc"`

**Configurable Top-K Retrieval**:
- `n_results_sql` - Number of similar SQL examples (default: 10)
- `n_results_ddl` - Number of related DDL statements (default: 10)
- `n_results_documentation` - Number of related docs (default: 10)

#### Prompt Construction Pattern

Vanna builds prompts with sections:
1. `===Tables` - DDL statements
2. `===Additional Context` - Documentation
3. `===Question-SQL Pairs` - Historical Q&A examples
4. `===Response Guidelines` - Generation instructions

Token management: `str_to_approx_token_count()` estimates tokens as `len(string) / 4`

### Recommended DB-GPT Integration Architecture

Based on analysis, the integration should:

1. **Reuse DB-GPT's Vector Store Infrastructure**:
   - Create `VannaTrainingStore` extending/wrapping `VectorStoreBase`
   - Use three collection prefixes: `vanna_ddl_`, `vanna_sql_`, `vanna_doc_`
   - Leverage existing ChromaStore, MilvusStore, PGVectorStore implementations

2. **Implement Core Training Methods**:
   - `VannaTrainingService.add_ddl(db_name, ddl)`
   - `VannaTrainingService.add_question_sql(db_name, question, sql)`
   - `VannaTrainingService.add_documentation(db_name, doc)`
   - `VannaTrainingService.train_schema(db_name)` - Auto-extract DDL from connector

3. **Integrate into ChatScene**:
   - Add `VannaContextRetriever` called before prompt generation
   - Inject retrieved context into existing prompt templates
   - Make it opt-in via `ChatWithDbExecuteConfig.enable_vanna_rag`

4. **API Endpoints**:
   - `POST /api/v1/vanna/train` - Add training data
   - `GET /api/v1/vanna/training-data/{db_name}` - List training data
   - `DELETE /api/v1/vanna/training-data/{id}` - Remove training data
   - `POST /api/v1/vanna/train-schema/{db_name}` - Auto-train from database

### Alignment with Existing DB-GPT Components

| Vanna Component | DB-GPT Equivalent | Integration Strategy |
|-----------------|-------------------|---------------------|
| `VannaBase` | `BaseChat` | Extend ChatScene with Vanna retrieval |
| `ChromaDB_VectorStore` | `ChromaStore` | Wrap existing VectorStoreBase |
| `generate_embedding()` | `EmbeddingFactory` | Use DB-GPT's embedding service |
| `run_sql()` | `ConnectorManager` | Already available via database connectors |
| `TrainingPlan` | `DBSchemaRetriever` | Extend for DDL extraction |
| Prompt templates | Scene prompts | Inject Vanna context into existing templates |
