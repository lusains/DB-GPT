"""ChatWithDbVanna Configuration."""

from dataclasses import dataclass, field
from typing import Optional

from dbgpt.util.i18n_utils import _
from dbgpt_app.scene import ChatScene
from dbgpt_serve.core.config import (
    BaseGPTsAppMemoryConfig,
    BufferWindowGPTsAppMemoryConfig,
    GPTsAppCommonConfig,
)


@dataclass
class ChatWithDbVannaConfig(GPTsAppCommonConfig):
    """Chat With DB Vanna Configuration.

    Extends base configuration with Vanna-specific settings.
    """

    name = ChatScene.ChatWithDbVanna.value()

    # Vanna context retrieval settings
    vanna_n_results_ddl: int = field(
        default=5,
        metadata={"help": _("Number of DDL statements to retrieve from Vanna store.")},
    )
    vanna_n_results_sql: int = field(
        default=5,
        metadata={"help": _("Number of SQL examples to retrieve from Vanna store.")},
    )
    vanna_n_results_doc: int = field(
        default=3,
        metadata={"help": _("Number of documentation entries to retrieve.")},
    )
    vanna_max_context_tokens: int = field(
        default=4000,
        metadata={"help": _("Maximum tokens for Vanna context in prompt.")},
    )

    # Fallback settings
    fallback_to_table_info: bool = field(
        default=True,
        metadata={
            "help": _(
                "Fall back to table_info when Vanna store is empty or retrieval fails."
            )
        },
    )
    schema_retrieve_top_k: int = field(
        default=10,
        metadata={"help": _("Top-k for fallback schema retrieval.")},
    )
    schema_max_tokens: int = field(
        default=100 * 1024,
        metadata={"help": _("Maximum tokens for fallback schema info.")},
    )

    # Query settings
    max_num_results: int = field(
        default=50,
        metadata={"help": _("Maximum number of results to return from the query.")},
    )

    # Domain rule injection (directly into prompt, not via vector store)
    domain_rule_path: Optional[str] = field(
        default="/Users/lusain/ai/DB-GPT/assets/schema/domain-rule.md",
        metadata={
            "help": _(
                "Path to domain-rule.md file for direct injection into prompt. "
                "This bypasses vector store and injects the full content."
            )
        },
    )
    domain_rule_max_tokens: int = field(
        default=2000,
        metadata={"help": _("Maximum tokens for domain rule content.")},
    )

    # Memory settings
    memory: Optional[BaseGPTsAppMemoryConfig] = field(
        default_factory=lambda: BufferWindowGPTsAppMemoryConfig(
            keep_start_rounds=0, keep_end_rounds=10
        ),
        metadata={"help": _("Memory configuration")},
    )
