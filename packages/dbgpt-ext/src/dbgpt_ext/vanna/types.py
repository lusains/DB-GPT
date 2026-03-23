"""Vanna AI Integration Type Definitions.

This module defines the core data structures for Vanna training data management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TrainingDataType(str, Enum):
    """Type of training data content."""

    DDL = "ddl"  # CREATE TABLE statements
    SQL = "sql"  # Question-SQL pairs
    DOCUMENTATION = "doc"  # Business documentation
    ONTOLOGY = "ontology"  # Ontology files (TTL, OWL, etc.)
    MEMORY = "memory"  # Agent memory (successful Q&A pairs)


@dataclass
class QuestionSqlPair:
    """A question-SQL pair for training examples."""

    question: str
    sql: str


@dataclass
class TrainingData:
    """Represents a single piece of training content stored in the vector store.

    Attributes:
        id: Unique identifier (format: {uuid}-{type})
        db_name: Associated database name
        type: Content type (DDL, SQL, or Documentation)
        content: The actual content (DDL/SQL/doc text)
        question: Natural language description (required for SQL type)
        created_at: Creation timestamp
        metadata: Additional metadata
    """

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


@dataclass
class VannaContext:
    """Retrieved context bundle for a specific query.

    Used to enhance LLM prompts with relevant training data.
    """

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
        """Check if context contains any data."""
        return not (self.ddl_list or self.sql_examples or self.documentation)


@dataclass
class AgentMemoryEntry:
    """A successful Q&A pair stored in agent memory.

    Used for learning from successful interactions.

    Attributes:
        id: Unique identifier
        db_name: Associated database name
        question: The original user question
        sql: The successfully executed SQL
        result_summary: Optional summary of query results
        created_at: When this was saved
        success_count: How many times this answer was reused
        metadata: Additional context
    """

    id: str
    db_name: str
    question: str
    sql: str
    result_summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    success_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OntologyData:
    """Ontology file content for semantic understanding.

    Supports TTL, OWL, and other ontology formats.

    Attributes:
        id: Unique identifier
        db_name: Associated database name
        content: The ontology file content
        format: File format (ttl, owl, rdf, json-ld)
        description: Optional description
        created_at: When this was added
    """

    id: str
    db_name: str
    content: str
    format: str = "ttl"
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BusinessDocument:
    """Business documentation for domain context.

    Provides business rules, workflows, and domain knowledge.

    Attributes:
        id: Unique identifier
        db_name: Associated database name
        title: Document title
        content: The document content (markdown supported)
        category: Document category (workflow, rule, example, etc.)
        created_at: When this was added
    """

    id: str
    db_name: str
    title: str
    content: str
    category: str = "general"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EnhancedVannaContext(VannaContext):
    """Extended context with ontology, memory, and business documents.

    Adds support for:
    - Ontology information for semantic understanding
    - Agent memory for learning from successful interactions
    - Business documents for domain knowledge
    """

    ontology: Optional[str] = None
    memory_examples: List[AgentMemoryEntry] = field(default_factory=list)
    business_docs: List[BusinessDocument] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        """Estimate token count (len / 4 approximation)."""
        total = super().total_tokens
        if self.ontology:
            total += len(self.ontology) // 4
        total += sum(
            (len(m.question) + len(m.sql)) // 4 for m in self.memory_examples
        )
        total += sum(len(d.content) // 4 for d in self.business_docs)
        return total

    def is_empty(self) -> bool:
        """Check if context contains any data."""
        return (
            super().is_empty()
            and not self.ontology
            and not self.memory_examples
            and not self.business_docs
        )
