"""Base class for Vanna Training Store.

This module defines the abstract base class for training data storage.
"""

import json
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from dbgpt_ext.vanna.types import (
    AgentMemoryEntry,
    BusinessDocument,
    OntologyData,
    QuestionSqlPair,
    TrainingData,
    TrainingDataType,
)


def deterministic_uuid(content: str) -> str:
    """Generate a deterministic UUID based on content hash.

    This ensures the same content always produces the same ID,
    enabling automatic deduplication.

    Args:
        content: The content to hash.

    Returns:
        A deterministic UUID string.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, content))


class VannaTrainingStoreBase(ABC):
    """Abstract base class for Vanna training data storage.

    Implementations should provide vector storage for three types of data:
    - DDL statements (schema information)
    - SQL examples (question-SQL pairs)
    - Documentation (business context)
    """

    @abstractmethod
    def add_ddl(self, db_name: str, ddl: str) -> str:
        """Add a DDL statement to the training store.

        Args:
            db_name: The database name.
            ddl: The DDL statement (e.g., CREATE TABLE...).

        Returns:
            The ID of the stored training data.
        """

    @abstractmethod
    def add_sql(self, db_name: str, question: str, sql: str) -> str:
        """Add a question-SQL pair to the training store.

        Args:
            db_name: The database name.
            question: The natural language question.
            sql: The corresponding SQL query.

        Returns:
            The ID of the stored training data.
        """

    @abstractmethod
    def add_documentation(self, db_name: str, documentation: str) -> str:
        """Add documentation to the training store.

        Args:
            db_name: The database name.
            documentation: The documentation text.

        Returns:
            The ID of the stored training data.
        """

    @abstractmethod
    def get_similar_ddl(
        self, db_name: str, question: str, n_results: int = 5
    ) -> List[str]:
        """Get DDL statements similar to the question.

        Args:
            db_name: The database name.
            question: The natural language question.
            n_results: Maximum number of results.

        Returns:
            List of DDL statements.
        """

    @abstractmethod
    def get_similar_sql(
        self, db_name: str, question: str, n_results: int = 5
    ) -> List[QuestionSqlPair]:
        """Get SQL examples similar to the question.

        Args:
            db_name: The database name.
            question: The natural language question.
            n_results: Maximum number of results.

        Returns:
            List of question-SQL pairs.
        """

    @abstractmethod
    def get_related_documentation(
        self, db_name: str, question: str, n_results: int = 3
    ) -> List[str]:
        """Get documentation related to the question.

        Args:
            db_name: The database name.
            question: The natural language question.
            n_results: Maximum number of results.

        Returns:
            List of documentation texts.
        """

    @abstractmethod
    def get_all(
        self,
        db_name: str,
        type_filter: Optional[TrainingDataType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TrainingData]:
        """Get all training data for a database.

        Args:
            db_name: The database name.
            type_filter: Optional filter by type.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of training data entries.
        """

    @abstractmethod
    def remove(self, id: str) -> bool:
        """Remove training data by ID.

        Args:
            id: The training data ID.

        Returns:
            True if removed, False if not found.
        """

    # ========== Agent Memory Methods ==========

    def add_memory(
        self,
        db_name: str,
        question: str,
        sql: str,
        result_summary: Optional[str] = None,
    ) -> str:
        """Add a successful Q&A pair to agent memory.

        Args:
            db_name: The database name.
            question: The user's question.
            sql: The successfully executed SQL.
            result_summary: Optional summary of query results.

        Returns:
            The ID of the stored memory entry.
        """
        # Default implementation - subclasses can override
        return self.add_sql(db_name, question, sql)

    def search_memory(
        self,
        db_name: str,
        question: str,
        n_results: int = 3,
        similarity_threshold: float = 0.85,
    ) -> List[AgentMemoryEntry]:
        """Search agent memory for similar questions.

        Args:
            db_name: The database name.
            question: The user's question.
            n_results: Maximum number of results.
            similarity_threshold: Minimum similarity score (0-1).

        Returns:
            List of matching memory entries.
        """
        # Default implementation - convert SQL pairs to memory entries
        sql_pairs = self.get_similar_sql(db_name, question, n_results)
        return [
            AgentMemoryEntry(
                id=f"memory-{i}",
                db_name=db_name,
                question=pair.question,
                sql=pair.sql,
            )
            for i, pair in enumerate(sql_pairs)
        ]

    def increment_memory_success(self, memory_id: str) -> bool:
        """Increment the success count for a memory entry.

        Args:
            memory_id: The memory entry ID.

        Returns:
            True if successful, False if not found.
        """
        # Default: no-op, subclasses can implement
        return True

    # ========== Ontology Methods ==========

    def add_ontology(
        self,
        db_name: str,
        content: str,
        format: str = "ttl",
        description: Optional[str] = None,
    ) -> str:
        """Add ontology content to the store.

        Args:
            db_name: The database name.
            content: The ontology file content.
            format: File format (ttl, owl, rdf, json-ld).
            description: Optional description.

        Returns:
            The ID of the stored ontology.
        """
        # Default: store as documentation with special prefix
        doc_content = f"[ONTOLOGY:{format}]\n{content}"
        return self.add_documentation(db_name, doc_content)

    def get_ontology(self, db_name: str) -> Optional[str]:
        """Get the ontology content for a database.

        Args:
            db_name: The database name.

        Returns:
            The ontology content, or None if not found.
        """
        # Default: return None, subclasses can implement
        return None

    # ========== Business Document Methods ==========

    def add_business_document(
        self,
        db_name: str,
        title: str,
        content: str,
        category: str = "general",
    ) -> str:
        """Add a business document to the store.

        Args:
            db_name: The database name.
            title: Document title.
            content: Document content.
            category: Document category.

        Returns:
            The ID of the stored document.
        """
        # Default: store as documentation with title prefix
        doc_content = f"[{category.upper()}] {title}\n\n{content}"
        return self.add_documentation(db_name, doc_content)

    def get_related_business_docs(
        self,
        db_name: str,
        question: str,
        n_results: int = 2,
    ) -> List[BusinessDocument]:
        """Get business documents related to the question.

        Args:
            db_name: The database name.
            question: The user's question.
            n_results: Maximum number of results.

        Returns:
            List of related business documents.
        """
        # Default: return empty list, subclasses can implement
        return []

    # ========== ID Generation Methods ==========

    def generate_ddl_id(self, ddl: str) -> str:
        """Generate ID for DDL content."""
        return f"{deterministic_uuid(ddl)}-ddl"

    def generate_sql_id(self, question: str, sql: str) -> str:
        """Generate ID for SQL content."""
        content = json.dumps({"question": question, "sql": sql}, sort_keys=True)
        return f"{deterministic_uuid(content)}-sql"

    def generate_doc_id(self, documentation: str) -> str:
        """Generate ID for documentation content."""
        return f"{deterministic_uuid(documentation)}-doc"

    def generate_memory_id(self, question: str, sql: str) -> str:
        """Generate ID for memory content."""
        content = json.dumps({"question": question, "sql": sql}, sort_keys=True)
        return f"{deterministic_uuid(content)}-memory"

    def generate_ontology_id(self, content: str) -> str:
        """Generate ID for ontology content."""
        return f"{deterministic_uuid(content)}-ontology"

    def generate_business_doc_id(self, title: str, content: str) -> str:
        """Generate ID for business document."""
        combined = json.dumps({"title": title, "content": content}, sort_keys=True)
        return f"{deterministic_uuid(combined)}-bizdo"
