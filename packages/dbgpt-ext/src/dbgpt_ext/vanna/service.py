"""Vanna Training Service.

This module provides the main service interface for Vanna training operations.
"""

import logging
from typing import Any, List, Optional

from dbgpt_ext.vanna.config import VannaConfig
from dbgpt_ext.vanna.store.base import VannaTrainingStoreBase
from dbgpt_ext.vanna.types import TrainingData, TrainingDataType

logger = logging.getLogger(__name__)


class VannaTrainingService:
    """Service for managing Vanna training data.

    Provides high-level operations for training schema, adding examples,
    and managing training data.

    Args:
        store: The training data store.
        config: Vanna configuration.
    """

    def __init__(
        self,
        store: VannaTrainingStoreBase,
        config: Optional[VannaConfig] = None,
    ) -> None:
        """Initialize the training service.

        Args:
            store: Training data store implementation.
            config: Optional configuration.
        """
        self._store = store
        self._config = config or VannaConfig()

    def train_schema(
        self,
        db_name: str,
        connector: Any,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None,
    ) -> int:
        """Train schema from database by extracting DDL for all tables.

        Args:
            db_name: The database name.
            connector: Database connector (RDBMSConnector or compatible).
            batch_size: Number of tables to process in each batch (for large schemas).
            progress_callback: Optional callback for progress updates.
                Signature: callback(current: int, total: int, table_name: str)

        Returns:
            Number of tables trained.
        """
        logger.info(f"Starting schema training for database: {db_name}")

        # Get all table names
        table_names = list(connector.get_table_names())
        total_tables = len(table_names)
        logger.info(f"Found {total_tables} tables to train")

        trained_count = 0

        for i, table_name in enumerate(table_names):
            try:
                # Get DDL for the table
                ddl = connector.get_table_info([table_name])

                if ddl and ddl.strip():
                    self._store.add_ddl(db_name, ddl)
                    trained_count += 1
                    logger.debug(f"Trained table: {table_name}")

                if progress_callback:
                    progress_callback(i + 1, total_tables, table_name)

            except Exception as e:
                logger.warning(f"Failed to extract DDL for table {table_name}: {e}")
                continue

        logger.info(f"Schema training completed: {trained_count}/{total_tables} tables")
        return trained_count

    def add_ddl(self, db_name: str, ddl: str) -> str:
        """Add a DDL statement to the training store.

        Args:
            db_name: The database name.
            ddl: The DDL statement.

        Returns:
            The ID of the stored training data.
        """
        if not ddl or not ddl.strip():
            raise ValueError("DDL cannot be empty")

        return self._store.add_ddl(db_name, ddl.strip())

    def add_question_sql(self, db_name: str, question: str, sql: str) -> str:
        """Add a question-SQL pair to the training store.

        Args:
            db_name: The database name.
            question: The natural language question.
            sql: The corresponding SQL query.

        Returns:
            The ID of the stored training data.
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        if not sql or not sql.strip():
            raise ValueError("SQL cannot be empty")

        return self._store.add_sql(db_name, question.strip(), sql.strip())

    def add_documentation(self, db_name: str, documentation: str) -> str:
        """Add documentation to the training store.

        Args:
            db_name: The database name.
            documentation: The documentation text.

        Returns:
            The ID of the stored training data.
        """
        if not documentation or not documentation.strip():
            raise ValueError("Documentation cannot be empty")

        return self._store.add_documentation(db_name, documentation.strip())

    def get_training_data(
        self,
        db_name: str,
        type_filter: Optional[TrainingDataType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TrainingData]:
        """Get training data for a database.

        Args:
            db_name: The database name.
            type_filter: Optional filter by type.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of training data entries.
        """
        return self._store.get_all(
            db_name=db_name,
            type_filter=type_filter,
            limit=limit,
            offset=offset,
        )

    def remove_training_data(self, id: str) -> bool:
        """Remove training data by ID.

        Args:
            id: The training data ID.

        Returns:
            True if removed, False if not found.
        """
        return self._store.remove(id)
