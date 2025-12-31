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
class ChatWithDBExecuteOntologyConfig(GPTsAppCommonConfig):
    """Chat With DB Execute Ontology Configuration.

    This configuration extends the standard DB execute config to support
    ontology-aware SQL generation with OWL-to-MySQL schema mapping.
    """

    name = ChatScene.ChatWithDbExecuteOntology.value()

    schema_retrieve_top_k: int = field(
        default=10,
        metadata={"help": _("The number of tables to retrieve from the database.")},
    )
    schema_max_tokens: int = field(
        default=100 * 1024,
        metadata={
            "help": _(
                "The maximum number of tokens to pass to the model, default 100 * 1024."
                "Just work for the schema retrieval failed, and load all tables schema."
            )
        },
    )
    max_num_results: int = field(
        default=50,
        metadata={"help": _("The maximum number of results to return from the query.")},
    )
    memory: Optional[BaseGPTsAppMemoryConfig] = field(
        default_factory=lambda: BufferWindowGPTsAppMemoryConfig(
            keep_start_rounds=0, keep_end_rounds=10
        ),
        metadata={"help": _("Memory configuration")},
    )
    # Ontology-specific configurations
    source_mapping: Optional[str] = field(
        default=None,
        metadata={
            "help": _(
                "JSON string mapping OWL ontology concepts to MySQL schema elements. "
                "Format: {owl_class: {table: 'mysql_table', columns: {...}}}"
            )
        },
    )
    graph_store_name: Optional[str] = field(
        default=None,
        metadata={
            "help": _("Name of the graph store containing the ontology schema.")
        },
    )
    # Semantic enhancement configurations (Vanna-inspired)
    ttl_path: Optional[str] = field(
        default=None,
        metadata={
            "help": _(
                "Path to the OWL/TTL ontology file for semantic enhancement. "
                "If not specified, defaults to assets/schema/1216.ttl"
            )
        },
    )
    source_mapping_path: Optional[str] = field(
        default=None,
        metadata={
            "help": _(
                "Path to the source mapping JSON file. "
                "If not specified, defaults to assets/schema/db_to_ttl_mapping.json"
            )
        },
    )
    enable_semantic_context: bool = field(
        default=True,
        metadata={
            "help": _(
                "Enable semantic context enhancement from TTL ontology. "
                "This provides better SQL generation through term translation, "
                "enum value extraction, and relationship inference."
            )
        },
    )
