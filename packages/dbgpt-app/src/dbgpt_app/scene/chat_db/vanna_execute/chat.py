"""ChatWithDbVanna Chat Handler.

This module provides Vanna-enhanced Text-to-SQL generation with RAG context.
"""

import logging
from typing import Dict, Type

from dbgpt import SystemApp
from dbgpt.agent.util.api_call import ApiCall
from dbgpt.util.executor_utils import blocking_func_to_async
from dbgpt.util.tracer import root_tracer, trace
from dbgpt_app.scene import BaseChat, ChatScene
from dbgpt_app.scene.base_chat import ChatParam
from dbgpt_app.scene.chat_db.vanna_execute.config import ChatWithDbVannaConfig
from dbgpt_serve.core.config import GPTsAppCommonConfig
from dbgpt_serve.datasource.manages import ConnectorManager

logger = logging.getLogger(__name__)


class ChatWithDbVannaExecute(BaseChat):
    """Vanna-enhanced Chat with Database scene.

    Uses trained DDL, SQL examples, and documentation for context-aware SQL generation.
    """

    chat_scene: str = ChatScene.ChatWithDbVanna.value()

    @classmethod
    def param_class(cls) -> Type[GPTsAppCommonConfig]:
        return ChatWithDbVannaConfig

    def __init__(self, chat_param: ChatParam, system_app: SystemApp):
        """Initialize ChatWithDbVanna.

        Args:
            chat_param: Chat parameters including db_name.
            system_app: DB-GPT system application.
        """
        self.db_name = chat_param.select_param
        self.curr_config = chat_param.real_app_config(ChatWithDbVannaConfig)
        super().__init__(chat_param=chat_param, system_app=system_app)

        if not self.db_name:
            raise ValueError(
                f"{ChatScene.ChatWithDbVanna.value} mode requires a database selection!"
            )

        # Initialize database connector
        with root_tracer.start_span(
            "ChatWithDbVannaExecute.get_connect", metadata={"db_name": self.db_name}
        ):
            local_db_manager = ConnectorManager.get_instance(self.system_app)
            self.database = local_db_manager.get_connector(self.db_name)

        self.api_call = ApiCall()
        self._vanna_retriever = None

    def _get_vanna_retriever(self):
        """Lazily initialize and get the Vanna context retriever."""
        if self._vanna_retriever is None:
            try:
                from dbgpt_serve.vanna.api.endpoints import get_vanna_retriever

                self._vanna_retriever = get_vanna_retriever()
            except Exception as e:
                logger.warning(f"Failed to initialize Vanna retriever: {e}")
                self._vanna_retriever = None
        return self._vanna_retriever

    @trace()
    async def generate_input_values(self) -> Dict:
        """Generate input values for the prompt template.

        Retrieves enhanced Vanna context (DDL, SQL examples, documentation,
        agent memory, ontology, business docs) and falls back to table_info
        if Vanna store is empty.
        """
        user_input = self.current_user_input.last_text

        # Initialize Vanna context variables
        vanna_ddl = ""
        vanna_sql_examples = ""
        vanna_documentation = ""
        vanna_memory = ""
        vanna_ontology = ""
        vanna_business_docs = ""
        table_info = ""
        domain_rule = ""

        # Load domain rule file if configured (direct injection)
        if self.curr_config.domain_rule_path:
            try:
                import os
                if os.path.exists(self.curr_config.domain_rule_path):
                    with open(self.curr_config.domain_rule_path, "r", encoding="utf-8") as f:
                        domain_rule = f.read()
                    # Truncate if too long
                    max_chars = self.curr_config.domain_rule_max_tokens * 4
                    if len(domain_rule) > max_chars:
                        domain_rule = domain_rule[:max_chars]
                        logger.info(f"Truncated domain rule to {max_chars} chars")
                    logger.info(f"Loaded domain rule: {len(domain_rule)} chars")
            except Exception as e:
                logger.warning(f"Failed to load domain rule: {e}")

        # Try to get enhanced Vanna context
        retriever = self._get_vanna_retriever()
        if retriever:
            try:
                with root_tracer.start_span("ChatWithDbVannaExecute.get_enhanced_context"):
                    context = await blocking_func_to_async(
                        self._executor,
                        retriever.get_enhanced_context,
                        user_input,
                        self.db_name,
                    )

                    if not context.is_empty():
                        # Format DDL list
                        if context.ddl_list:
                            vanna_ddl = "\n\n".join(context.ddl_list)

                        # Format SQL examples (Vanna style: question then SQL)
                        if context.sql_examples:
                            sql_parts = []
                            for ex in context.sql_examples:
                                sql_parts.append(f"{ex.question}\n{ex.sql}")
                            vanna_sql_examples = "\n\n".join(sql_parts)

                        # Format documentation
                        if context.documentation:
                            vanna_documentation = "\n\n".join(context.documentation)

                        # Format agent memory examples (highest priority - proven answers)
                        if context.memory_examples:
                            memory_parts = []
                            for mem in context.memory_examples:
                                memory_parts.append(
                                    f"Q: {mem.question}\nSQL: {mem.sql}"
                                    + (f"\nResult: {mem.result_summary}" if mem.result_summary else "")
                                )
                            vanna_memory = "\n\n".join(memory_parts)

                        # Format ontology (domain knowledge)
                        if context.ontology:
                            vanna_ontology = context.ontology

                        # Format business documents
                        if context.business_docs:
                            doc_parts = []
                            for doc in context.business_docs:
                                doc_parts.append(f"[{doc.category}] {doc.title}\n{doc.content}")
                            vanna_business_docs = "\n\n".join(doc_parts)

                        logger.info(
                            f"Retrieved enhanced Vanna context: {len(context.ddl_list)} DDL, "
                            f"{len(context.sql_examples)} SQL examples, "
                            f"{len(context.documentation)} docs, "
                            f"{len(context.memory_examples)} memory, "
                            f"{'has' if context.ontology else 'no'} ontology, "
                            f"{len(context.business_docs)} business docs"
                        )
                    else:
                        logger.info("Vanna context is empty, will use fallback")

            except Exception as e:
                logger.warning(f"Failed to retrieve enhanced Vanna context: {e}")

        # Fallback to table_info if Vanna context is empty/failed
        if not vanna_ddl and self.curr_config.fallback_to_table_info:
            logger.info("Using fallback table_info retrieval")
            try:
                from dbgpt_serve.datasource.service.db_summary_client import (
                    DBSummaryClient,
                )

                client = DBSummaryClient(system_app=self.system_app)
                with root_tracer.start_span("ChatWithDbVannaExecute.get_db_summary"):
                    table_info = await blocking_func_to_async(
                        self._executor,
                        client.get_db_summary,
                        self.db_name,
                        user_input,
                        self.curr_config.schema_retrieve_top_k,
                    )
            except Exception as e:
                logger.warning(f"Fallback table_info retrieval failed: {e}")
                try:
                    table_info = await blocking_func_to_async(
                        self._executor, self.database.table_simple_info
                    )
                    if len(table_info) > self.curr_config.schema_max_tokens:
                        table_info = table_info[: self.curr_config.schema_max_tokens]
                except Exception as e2:
                    logger.error(f"All fallback methods failed: {e2}")
                    table_info = "No table information available."

        input_values = {
            "db_name": self.db_name,
            "user_input": user_input,
            "top_k": self.curr_config.max_num_results,
            "dialect": self.database.dialect,
            "domain_rule": domain_rule or "No domain rules configured.",
            "vanna_ddl": vanna_ddl or "No trained DDL available.",
            "vanna_sql_examples": vanna_sql_examples or "No SQL examples available.",
            "vanna_documentation": vanna_documentation or "No documentation available.",
            "vanna_memory": vanna_memory or "No previous successful answers.",
            "vanna_ontology": vanna_ontology or "No domain ontology available.",
            "vanna_business_docs": vanna_business_docs or "No business documentation.",
            "table_info": table_info or "No additional table info.",
            "display_type": self._generate_numbered_list(),
        }

        return input_values

    def do_action(self, prompt_response):
        """Execute the generated SQL query."""
        logger.debug(f"do_action: {prompt_response}")
        return self.database.run_to_df

    async def save_successful_to_memory(
        self, question: str, sql: str, result_summary: str = None
    ) -> str:
        """Save a successful Q&A pair to agent memory.

        This enables learning from successful interactions for future queries.

        Args:
            question: The user's original question.
            sql: The successfully executed SQL query.
            result_summary: Optional summary of query results.

        Returns:
            The memory entry ID, or empty string if save failed.
        """
        retriever = self._get_vanna_retriever()
        if not retriever:
            logger.debug("Vanna retriever not available, skipping memory save")
            return ""

        try:
            memory_id = await blocking_func_to_async(
                self._executor,
                retriever.save_to_memory,
                self.db_name,
                question,
                sql,
                result_summary,
            )
            if memory_id:
                logger.info(f"Saved successful Q&A to memory: {memory_id}")
            return memory_id
        except Exception as e:
            logger.warning(f"Failed to save to memory: {e}")
            return ""

    def get_memory_auto_save_enabled(self) -> bool:
        """Check if auto-save to memory is enabled.

        Returns:
            True if auto-save is enabled in Vanna config.
        """
        retriever = self._get_vanna_retriever()
        if retriever and hasattr(retriever, "_config"):
            return getattr(retriever._config, "auto_save_successful", False)
        return False
