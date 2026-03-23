"""Vanna Context Retriever.

This module provides context retrieval for Vanna-enhanced SQL generation.
Supports enhanced context with agent memory, ontology, and business documents.
"""

import logging
from typing import Optional

from dbgpt_ext.vanna.config import VannaConfig
from dbgpt_ext.vanna.store.base import VannaTrainingStoreBase
from dbgpt_ext.vanna.types import EnhancedVannaContext, VannaContext

logger = logging.getLogger(__name__)


class VannaContextRetriever:
    """Retrieves training context for SQL generation prompts.

    Combines DDL, SQL examples, documentation, agent memory, ontology,
    and business documents into context for injection into LLM prompts.

    Args:
        store: The training data store.
        config: Vanna configuration.
    """

    def __init__(
        self,
        store: VannaTrainingStoreBase,
        config: Optional[VannaConfig] = None,
    ) -> None:
        """Initialize the context retriever.

        Args:
            store: Training data store implementation.
            config: Optional configuration. Uses defaults if not provided.
        """
        self._store = store
        self._config = config or VannaConfig()

    def get_context(self, question: str, db_name: str) -> VannaContext:
        """Retrieve context for a natural language question.

        Args:
            question: The user's natural language question.
            db_name: The target database name.

        Returns:
            VannaContext containing relevant DDL, SQL examples, and documentation.
        """
        logger.info(f"Retrieving Vanna context for question: {question[:50]}...")

        # Retrieve DDL statements
        ddl_list = self._store.get_similar_ddl(
            db_name=db_name,
            question=question,
            n_results=self._config.n_results_ddl,
        )

        # Retrieve SQL examples
        sql_examples = self._store.get_similar_sql(
            db_name=db_name,
            question=question,
            n_results=self._config.n_results_sql,
        )

        # Retrieve documentation
        documentation = self._store.get_related_documentation(
            db_name=db_name,
            question=question,
            n_results=self._config.n_results_doc,
        )

        context = VannaContext(
            ddl_list=ddl_list,
            sql_examples=sql_examples,
            documentation=documentation,
        )

        # Enforce token limit if configured
        if self._config.max_context_tokens > 0:
            context = self._truncate_context(context)

        logger.info(
            f"Retrieved context: {len(ddl_list)} DDL, "
            f"{len(sql_examples)} SQL examples, "
            f"{len(documentation)} docs "
            f"(~{context.total_tokens} tokens)"
        )

        return context

    def get_enhanced_context(
        self, question: str, db_name: str
    ) -> EnhancedVannaContext:
        """Retrieve enhanced context including memory, ontology, and business docs.

        Args:
            question: The user's natural language question.
            db_name: The target database name.

        Returns:
            EnhancedVannaContext with all available context types.
        """
        logger.info(f"Retrieving enhanced Vanna context for: {question[:50]}...")

        # Get base context
        ddl_list = self._store.get_similar_ddl(
            db_name=db_name,
            question=question,
            n_results=self._config.n_results_ddl,
        )

        sql_examples = self._store.get_similar_sql(
            db_name=db_name,
            question=question,
            n_results=self._config.n_results_sql,
        )

        documentation = self._store.get_related_documentation(
            db_name=db_name,
            question=question,
            n_results=self._config.n_results_doc,
        )

        # Get agent memory if enabled
        memory_examples = []
        if self._config.memory_enabled:
            memory_examples = self._store.search_memory(
                db_name=db_name,
                question=question,
                n_results=self._config.n_results_memory,
                similarity_threshold=self._config.memory_similarity_threshold,
            )
            if memory_examples:
                logger.info(f"Found {len(memory_examples)} memory matches")

        # Get ontology if enabled
        ontology = None
        if self._config.ontology_enabled:
            ontology = self._store.get_ontology(db_name)
            if ontology:
                # Truncate if too long
                max_onto_tokens = self._config.ontology_max_tokens
                if len(ontology) // 4 > max_onto_tokens:
                    ontology = ontology[: max_onto_tokens * 4]
                    logger.debug(f"Truncated ontology to {max_onto_tokens} tokens")

        # Get business documents if enabled
        business_docs = []
        if self._config.business_docs_enabled:
            business_docs = self._store.get_related_business_docs(
                db_name=db_name,
                question=question,
                n_results=self._config.n_results_business_docs,
            )
            if business_docs:
                logger.info(f"Found {len(business_docs)} related business docs")

        context = EnhancedVannaContext(
            ddl_list=ddl_list,
            sql_examples=sql_examples,
            documentation=documentation,
            ontology=ontology,
            memory_examples=memory_examples,
            business_docs=business_docs,
        )

        # Enforce token limit if configured
        if self._config.max_context_tokens > 0:
            context = self._truncate_enhanced_context(context)

        logger.info(
            f"Retrieved enhanced context: {len(ddl_list)} DDL, "
            f"{len(sql_examples)} SQL, {len(documentation)} docs, "
            f"{len(memory_examples)} memory, "
            f"{'has' if ontology else 'no'} ontology, "
            f"{len(business_docs)} business docs "
            f"(~{context.total_tokens} tokens)"
        )

        return context

    def save_to_memory(
        self,
        db_name: str,
        question: str,
        sql: str,
        result_summary: Optional[str] = None,
    ) -> str:
        """Save a successful Q&A pair to agent memory.

        Args:
            db_name: The database name.
            question: The user's question.
            sql: The successfully executed SQL.
            result_summary: Optional summary of query results.

        Returns:
            The memory entry ID.
        """
        if not self._config.memory_enabled:
            logger.debug("Memory is disabled, skipping save")
            return ""

        memory_id = self._store.add_memory(
            db_name=db_name,
            question=question,
            sql=sql,
            result_summary=result_summary,
        )
        logger.info(f"Saved to memory: {memory_id}")
        return memory_id

    def _truncate_context(self, context: VannaContext) -> VannaContext:
        """Truncate context to fit within token limit.

        Prioritizes DDL > SQL examples > Documentation when truncating.

        Args:
            context: The context to truncate.

        Returns:
            Truncated context.
        """
        max_tokens = self._config.max_context_tokens

        if context.total_tokens <= max_tokens:
            return context

        logger.debug(
            f"Truncating context from {context.total_tokens} to {max_tokens} tokens"
        )

        # Truncate documentation first (least priority)
        while context.documentation and context.total_tokens > max_tokens:
            context.documentation.pop()

        # Then SQL examples
        while context.sql_examples and context.total_tokens > max_tokens:
            context.sql_examples.pop()

        # Finally DDL (most important)
        while context.ddl_list and context.total_tokens > max_tokens:
            context.ddl_list.pop()

        return context

    def _truncate_enhanced_context(
        self, context: EnhancedVannaContext
    ) -> EnhancedVannaContext:
        """Truncate enhanced context to fit within token limit.

        Priority (highest to lowest):
        1. Memory examples (highest - proven successful)
        2. DDL statements
        3. SQL examples
        4. Business documents
        5. Documentation
        6. Ontology (lowest - usually very long)

        Args:
            context: The context to truncate.

        Returns:
            Truncated context.
        """
        max_tokens = self._config.max_context_tokens

        if context.total_tokens <= max_tokens:
            return context

        logger.debug(
            f"Truncating enhanced context from {context.total_tokens} "
            f"to {max_tokens} tokens"
        )

        # Truncate in order of priority (lowest first)

        # 1. Truncate ontology first (can be very long)
        if context.ontology and context.total_tokens > max_tokens:
            # Reduce ontology by half each time
            while context.ontology and context.total_tokens > max_tokens:
                context.ontology = context.ontology[: len(context.ontology) // 2]
                if len(context.ontology) < 100:
                    context.ontology = None
                    break

        # 2. Truncate documentation
        while context.documentation and context.total_tokens > max_tokens:
            context.documentation.pop()

        # 3. Truncate business docs
        while context.business_docs and context.total_tokens > max_tokens:
            context.business_docs.pop()

        # 4. Truncate SQL examples
        while context.sql_examples and context.total_tokens > max_tokens:
            context.sql_examples.pop()

        # 5. Truncate DDL (keep as much as possible)
        while context.ddl_list and context.total_tokens > max_tokens:
            context.ddl_list.pop()

        # 6. Truncate memory only as last resort (highest priority)
        while context.memory_examples and context.total_tokens > max_tokens:
            context.memory_examples.pop()

        return context
