# Implementation Plan: Vanna AI Integration for Enhanced Text-to-SQL

**Branch**: `002-vanna-integration` | **Date**: 2025-12-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-vanna-integration/spec.md`
**Scope**: Core mainline functionality (feedback, multi-tenant deferred)

## Summary

Integrate Vanna AI's RAG capabilities into DB-GPT as a new extension package (`dbgpt-ext-vanna`) to enhance Text-to-SQL accuracy. Core features:
- **Training System**: Store DDL, SQL examples, and documentation with semantic embeddings
- **Retrieval System**: RAG-based context retrieval for SQL generation
- **New ChatScene**: `ChatWithDbVanna` for Vanna-enhanced SQL generation
- **API Endpoints**: Training data management and schema auto-training

## Technical Context

**Language/Version**: Python >= 3.10 (aligns with DB-GPT requirements)
**Primary Dependencies**: chromadb, dbgpt (core), dbgpt-ext (extension base)
**Storage**: ChromaDB (default, file-based); VectorStoreBase abstraction for Milvus/PGVector
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux/macOS server (same as DB-GPT)
**Project Type**: Monorepo extension package
**Performance Goals**: Context retrieval < 500ms, schema training 100 tables < 5 min
**Constraints**: No core DB-GPT modifications, extension-only pattern
**Scale/Scope**: 10,000+ training entries per database

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: PASS - No specific constitution defined for this project. Following DB-GPT extension patterns and YAGNI principles.

| Principle | Compliance |
|-----------|-----------|
| Extension-only pattern | PASS - New package under packages/, no core modifications |
| Test-first approach | PASS - Tests defined in tasks, pytest infrastructure exists |
| YAGNI / Core-first | PASS - User specified core features only, deferring feedback/multi-tenant |

## Project Structure

### Documentation (this feature)

```text
specs/002-vanna-integration/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
packages/
├── dbgpt-ext/                    # Existing extension package
│   └── src/dbgpt_ext/
│       └── vanna/                # NEW: Vanna integration module
│           ├── __init__.py
│           ├── config.py         # VannaConfig dataclass
│           ├── store/            # Training data storage
│           │   ├── __init__.py
│           │   ├── base.py       # VannaTrainingStore abstract
│           │   └── chromadb.py   # ChromaDB implementation
│           ├── service.py        # VannaTrainingService
│           ├── retriever.py      # VannaContextRetriever
│           └── types.py          # TrainingData, VannaContext types
│
├── dbgpt-app/                    # Existing app package
│   └── src/dbgpt_app/
│       └── scene/
│           └── chat_db/
│               └── vanna_execute/ # NEW: ChatWithDbVanna scene
│                   ├── __init__.py
│                   ├── chat.py
│                   ├── config.py
│                   └── prompt.py
│
└── dbgpt-serve/                  # Existing serve package
    └── src/dbgpt_serve/
        └── vanna/                # NEW: Vanna API endpoints
            ├── __init__.py
            ├── api/
            │   └── endpoints.py
            └── service/
                └── service.py

tests/
└── dbgpt_ext/
    └── vanna/
        ├── test_store.py
        ├── test_service.py
        └── test_retriever.py
```

**Structure Decision**: Follow existing DB-GPT monorepo pattern. Vanna core logic in `dbgpt-ext/vanna/`, ChatScene in `dbgpt-app/scene/chat_db/vanna_execute/`, API in `dbgpt-serve/vanna/`.

## Complexity Tracking

> No constitution violations requiring justification.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Separate collections | 3 ChromaDB collections (ddl, sql, doc) | Follows Vanna pattern, enables independent top-k tuning |
| New ChatScene vs extending | New `ChatWithDbVanna` | User choice - clean separation, no side effects |
| Package location | Inside dbgpt-ext, not new package | Simpler - no new package overhead |

## Deferred Features

Per user input, the following are deferred to future iterations:
- Feedback/rating system for SQL quality
- Multi-tenant training data isolation
- CSV/Markdown import formats
- Milvus/PGVector storage backends (ChromaDB only for MVP)
