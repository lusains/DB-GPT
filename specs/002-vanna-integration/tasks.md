# Tasks: Vanna AI Integration for Enhanced Text-to-SQL

**Input**: Design documents from `/specs/002-vanna-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested - tests omitted per YAGNI principle.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1-US5) this task belongs to
- All paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Vanna module structure

- [ ] T001 Create Vanna module directory structure in packages/dbgpt-ext/src/dbgpt_ext/vanna/
- [ ] T002 [P] Create packages/dbgpt-ext/src/dbgpt_ext/vanna/__init__.py with module exports
- [ ] T003 [P] Create packages/dbgpt-ext/src/dbgpt_ext/vanna/types.py with TrainingDataType, TrainingData, QuestionSqlPair, VannaContext dataclasses
- [ ] T004 [P] Create packages/dbgpt-ext/src/dbgpt_ext/vanna/config.py with VannaConfig dataclass
- [ ] T005 Add chromadb to dbgpt-ext optional dependencies in packages/dbgpt-ext/pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core training store infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create packages/dbgpt-ext/src/dbgpt_ext/vanna/store/__init__.py with store exports
- [ ] T007 Create VannaTrainingStoreBase abstract class in packages/dbgpt-ext/src/dbgpt_ext/vanna/store/base.py with add_ddl, add_sql, add_doc, get_ddl, get_sql, get_doc, get_all, remove methods
- [ ] T008 Implement deterministic_uuid helper function in packages/dbgpt-ext/src/dbgpt_ext/vanna/store/base.py for content-based ID generation
- [ ] T009 Implement ChromaDBVannaStore in packages/dbgpt-ext/src/dbgpt_ext/vanna/store/chromadb.py with three collections (ddl, sql, doc)
- [ ] T010 Add embedding generation using DB-GPT EmbeddingFactory in packages/dbgpt-ext/src/dbgpt_ext/vanna/store/chromadb.py
- [ ] T011 Create VannaContextRetriever class in packages/dbgpt-ext/src/dbgpt_ext/vanna/retriever.py with get_context(question, db_name) method

**Checkpoint**: Foundation ready - training store and retrieval infrastructure complete

---

## Phase 3: User Story 1 - Train Schema from Database (Priority: P1) 🎯 MVP

**Goal**: Auto-extract DDL from connected databases and store in training store

**Independent Test**: Connect to database, call train_schema, verify DDL stored and retrievable

### Implementation for User Story 1

- [ ] T012 [US1] Create VannaTrainingService class in packages/dbgpt-ext/src/dbgpt_ext/vanna/service.py
- [ ] T013 [US1] Implement train_schema(db_name) method in VannaTrainingService that uses ConnectorManager to extract DDL
- [ ] T014 [US1] Add batch processing for large schemas (1000+ tables) with progress tracking in service.py
- [ ] T015 [US1] Implement add_ddl(db_name, ddl) method in VannaTrainingService
- [ ] T016 [US1] Create POST /api/v1/vanna/train-schema/{db_name} endpoint in packages/dbgpt-serve/src/dbgpt_serve/vanna/api/endpoints.py
- [ ] T017 [US1] Create packages/dbgpt-serve/src/dbgpt_serve/vanna/__init__.py with API router registration
- [ ] T018 [US1] Create TrainingRequest, TrainingResponse, SchemaTrainingResponse Pydantic models in packages/dbgpt-serve/src/dbgpt_serve/vanna/api/schemas.py
- [ ] T019 [US1] Register Vanna API router in DB-GPT server initialization

**Checkpoint**: Schema training works end-to-end via API

---

## Phase 4: User Story 4 - RAG-Enhanced SQL Generation (Priority: P1) 🎯 MVP

**Goal**: Use trained context in SQL generation prompts

**Independent Test**: Train schema, ask question, verify context included in LLM prompt

**Dependencies**: User Story 1 (schema training must work first)

### Implementation for User Story 4

- [ ] T020 [US4] Create ChatWithDbVanna ChatScene directory in packages/dbgpt-app/src/dbgpt_app/scene/chat_db/vanna_execute/
- [ ] T021 [P] [US4] Create packages/dbgpt-app/src/dbgpt_app/scene/chat_db/vanna_execute/__init__.py
- [ ] T022 [P] [US4] Create ChatWithDbVannaConfig in packages/dbgpt-app/src/dbgpt_app/scene/chat_db/vanna_execute/config.py extending GPTsAppCommonConfig
- [ ] T023 [US4] Create Vanna-enhanced prompt template in packages/dbgpt-app/src/dbgpt_app/scene/chat_db/vanna_execute/prompt.py with DDL, SQL examples, documentation sections
- [ ] T024 [US4] Create ChatWithDbVannaExecute class in packages/dbgpt-app/src/dbgpt_app/scene/chat_db/vanna_execute/chat.py extending BaseChat
- [ ] T025 [US4] Implement generate_input_values() in chat.py to call VannaContextRetriever and inject context
- [ ] T026 [US4] Add fallback to table_info when vector store is empty in chat.py
- [ ] T027 [US4] Register ChatWithDbVanna scene in packages/dbgpt-app/src/dbgpt_app/scene/__init__.py ChatScene enum
- [ ] T028 [US4] Add ChatWithDbVanna to chat factory in packages/dbgpt-app/src/dbgpt_app/scene/chat_factory.py

**Checkpoint**: RAG-enhanced SQL generation works with trained schema

---

## Phase 5: User Story 2 - Train with SQL Examples (Priority: P2)

**Goal**: Add question-SQL pairs to training store for pattern learning

**Independent Test**: Add SQL examples via API, verify retrieval by similar questions

### Implementation for User Story 2

- [ ] T029 [US2] Implement add_question_sql(db_name, question, sql) method in VannaTrainingService
- [ ] T030 [US2] Add SQL example storage with question embedding in ChromaDBVannaStore
- [ ] T031 [US2] Implement get_similar_sql(question, n_results) in ChromaDBVannaStore
- [ ] T032 [US2] Update VannaContextRetriever to include SQL examples in context
- [ ] T033 [US2] Add SQL example section to prompt template in vanna_execute/prompt.py
- [ ] T034 [US2] Create POST /api/v1/vanna/train endpoint for adding training data (ddl/sql/doc) in endpoints.py

**Checkpoint**: SQL examples can be trained and retrieved

---

## Phase 6: User Story 3 - Train with Documentation (Priority: P2)

**Goal**: Add business documentation to training store for term understanding

**Independent Test**: Add documentation via API, verify retrieval by business terms

### Implementation for User Story 3

- [ ] T035 [US3] Implement add_documentation(db_name, doc) method in VannaTrainingService
- [ ] T036 [US3] Add documentation storage in ChromaDBVannaStore
- [ ] T037 [US3] Implement get_related_documentation(question, n_results) in ChromaDBVannaStore
- [ ] T038 [US3] Update VannaContextRetriever to include documentation in context
- [ ] T039 [US3] Add documentation section to prompt template in vanna_execute/prompt.py

**Checkpoint**: Documentation can be trained and retrieved

---

## Phase 7: User Story 5 - Manage Training Data (Priority: P3)

**Goal**: List, view, and delete training data via API

**Independent Test**: List training data, delete entry, verify removal

### Implementation for User Story 5

- [ ] T040 [US5] Implement get_training_data(db_name, type_filter) method in VannaTrainingService
- [ ] T041 [US5] Implement remove_training_data(id) method in VannaTrainingService
- [ ] T042 [US5] Create GET /api/v1/vanna/training-data/{db_name} endpoint in endpoints.py
- [ ] T043 [US5] Create DELETE /api/v1/vanna/training-data/{id} endpoint in endpoints.py
- [ ] T044 [US5] Add pagination support (limit, offset) to list endpoint

**Checkpoint**: Full CRUD operations available for training data

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finalization and integration verification

- [ ] T045 [P] Add token counting and max_context_tokens enforcement in VannaContextRetriever
- [ ] T046 [P] Add deduplication check (skip if same content exists) in add_* methods
- [ ] T047 [P] Add comprehensive logging throughout Vanna module
- [ ] T048 [P] Add error handling for ChromaDB connection failures
- [ ] T049 Verify quickstart.md scenarios work end-to-end
- [ ] T050 Update packages/dbgpt-ext/src/dbgpt_ext/__init__.py to export vanna module

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────────────────────────┐
                                                 │
Phase 2: Foundational ──────────────────────────┤
                                                 │
    ┌────────────────────────────────────────────┘
    │
    ├──▶ Phase 3: US1 (Schema Training) ─────┐
    │                                         │
    │                                         ▼
    ├──▶ Phase 4: US4 (RAG Generation) ◀─────┘ [MVP Complete!]
    │
    ├──▶ Phase 5: US2 (SQL Examples)
    │
    ├──▶ Phase 6: US3 (Documentation)
    │
    └──▶ Phase 7: US5 (Management API)
                                                 │
Phase 8: Polish ◀────────────────────────────────┘
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 (Schema Training) | Foundational | - |
| US4 (RAG Generation) | US1 | - |
| US2 (SQL Examples) | Foundational | US1, US3 |
| US3 (Documentation) | Foundational | US1, US2 |
| US5 (Management) | Foundational | US1, US2, US3 |

### Within Each Phase

1. Tasks without [P] run sequentially
2. Tasks with [P] can run in parallel
3. Lower task numbers complete before higher ones (within same phase)

---

## Parallel Opportunities

### Phase 1 (Setup)
```
T002, T003, T004 can run in parallel (different files)
```

### Phase 4 (US4)
```
T021, T022 can run in parallel (different files)
```

### Phase 8 (Polish)
```
T045, T046, T047, T048 can run in parallel (independent concerns)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (Schema Training)
4. Complete Phase 4: User Story 4 (RAG Generation)
5. **STOP and VALIDATE**: Test end-to-end schema training → SQL generation
6. Demo/Deploy MVP

### Incremental Delivery

| Milestone | Stories Complete | Value Delivered |
|-----------|------------------|-----------------|
| MVP | US1 + US4 | Schema-aware SQL generation |
| +Examples | US2 | Pattern-based SQL improvement |
| +Docs | US3 | Business term understanding |
| +Management | US5 | Admin control over training data |

---

## Task Summary

| Phase | Task Count | Parallel Tasks |
|-------|------------|----------------|
| Setup | 5 | 3 |
| Foundational | 6 | 0 |
| US1 (Schema) | 8 | 0 |
| US4 (RAG) | 9 | 2 |
| US2 (SQL Examples) | 6 | 0 |
| US3 (Documentation) | 5 | 0 |
| US5 (Management) | 5 | 0 |
| Polish | 6 | 4 |
| **Total** | **50** | **9** |

---

## Notes

- MVP scope: Complete through Phase 4 (US1 + US4) = 28 tasks
- All tasks include exact file paths
- [P] indicates parallel-safe tasks
- [US#] indicates user story association
- Commit after each task or logical group
- Test independently at each checkpoint
