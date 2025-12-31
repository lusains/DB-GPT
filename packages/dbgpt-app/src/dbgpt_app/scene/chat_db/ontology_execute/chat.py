import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Type

from dbgpt import SystemApp
from dbgpt.agent.util.api_call import ApiCall
from dbgpt.util.executor_utils import blocking_func_to_async
from dbgpt.util.tracer import root_tracer, trace
from dbgpt_app.scene import BaseChat, ChatScene
from dbgpt_app.scene.base_chat import ChatParam
from dbgpt_app.scene.chat_db.ontology_execute.config import (
    ChatWithDBExecuteOntologyConfig,
)
from dbgpt_app.scene.chat_db.ontology_execute.semantic_index import (
    OntologySemanticIndex,
    get_semantic_index,
    initialize_semantic_index,
)
from dbgpt_serve.core.config import GPTsAppCommonConfig
from dbgpt_serve.datasource.manages import ConnectorManager

logger = logging.getLogger(__name__)

# Global semantic index (lazy initialized)
_semantic_index: Optional[OntologySemanticIndex] = None


class ChatWithDbOntologyExecute(BaseChat):
    """Ontology-aware Chat with Database Execute.

    This scene extends the standard chat_with_db_execute to support:
    1. Fetching graph schema from a knowledge graph (Neo4j/TuGraph)
    2. Using source_mapping to translate OWL concepts to MySQL schema
    3. Generating semantically-aware SQL queries
    """

    chat_scene: str = ChatScene.ChatWithDbExecuteOntology.value()

    @classmethod
    def param_class(cls) -> Type[GPTsAppCommonConfig]:
        return ChatWithDBExecuteOntologyConfig

    def __init__(self, chat_param: ChatParam, system_app: SystemApp):
        """Chat Data Module Initialization with Ontology Awareness.

        Args:
           - chat_param: Dict
            - chat_session_id: (str) chat session_id
            - current_user_input: (str) current user input
            - model_name:(str) llm model name
            - select_param:(str) dbname
        """
        self.db_name = chat_param.select_param
        self.curr_config = chat_param.real_app_config(ChatWithDBExecuteOntologyConfig)
        super().__init__(chat_param=chat_param, system_app=system_app)

        if not self.db_name:
            raise ValueError(
                f"{ChatScene.ChatWithDbExecuteOntology.value} mode should choose db!"
            )

        with root_tracer.start_span(
            "ChatWithDbOntologyExecute.get_connect", metadata={"db_name": self.db_name}
        ):
            local_db_manager = ConnectorManager.get_instance(self.system_app)
            self.database = local_db_manager.get_connector(self.db_name)

        self.api_call = ApiCall()

        # Get source_mapping from config or prompt parameters
        self.source_mapping = self._get_source_mapping()
        self.graph_store_name = self.curr_config.graph_store_name
        if not self.graph_store_name and chat_param.ext_info:
            self.graph_store_name = chat_param.ext_info.get("graph_store_name")

        # Auto-detect Neo4j graph store if not configured
        if not self.graph_store_name:
            self.graph_store_name = self._auto_detect_graph_store()

        # Initialize semantic index for enhanced SQL generation (Vanna-inspired)
        if self.curr_config.enable_semantic_context:
            self.semantic_index = self._get_or_init_semantic_index()
        else:
            self.semantic_index = None
            logger.info("Semantic context disabled by config")

        # Load domain rules for prompt enhancement
        self.domain_rules = self._load_domain_rules()

    def _auto_detect_graph_store(self) -> str:
        """Auto-detect a Neo4j or TuGraph data source for graph schema.

        Returns:
            str: Name of the detected graph store, or empty string if not found
        """
        try:
            local_db_manager = ConnectorManager.get_instance(self.system_app)

            # Use the official get_db_list() API to get all registered data sources
            db_list = local_db_manager.get_db_list()
            for db_info in db_list:
                db_type = db_info.get("db_type", "")
                db_name = db_info.get("db_name", "")
                # Check if it's a graph database (neo4j or tugraph)
                if db_type.lower() in ["neo4j", "tugraph"]:
                    logger.info(
                        f"Auto-detected graph store: {db_name} (type: {db_type})"
                    )
                    return db_name

        except Exception as e:
            logger.warning(f"Failed to auto-detect graph store: {e}")

        return ""

    def _load_domain_rules(self) -> str:
        """Load domain rules from markdown file.

        Domain rules provide business context for SQL generation, including:
        - Background knowledge about the domain
        - Business process flows
        - Example query patterns

        Returns:
            str: Domain rules content, or empty string if not found
        """
        try:
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent.parent.parent.parent.parent
            rules_path = project_root / "assets" / "schema" / "domain-rule.md"

            if rules_path.exists():
                with open(rules_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info(f"Loaded domain rules ({len(content)} chars)")
                return content
            else:
                logger.warning(f"Domain rules file not found: {rules_path}")
                return ""
        except Exception as e:
            logger.error(f"Failed to load domain rules: {e}")
            return ""

    def _get_or_init_semantic_index(self) -> Optional[OntologySemanticIndex]:
        """Get or initialize the semantic index for ontology-aware SQL generation.

        The semantic index provides:
        - Chinese term → column/table name translation
        - Enum value extraction from ontology comments
        - JOIN path inference from ObjectProperty relationships

        Returns:
            OntologySemanticIndex instance or None if initialization fails
        """
        global _semantic_index

        # Return cached index if available
        if _semantic_index is not None and _semantic_index._loaded:
            return _semantic_index

        try:
            # Get project root directory
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent.parent.parent.parent.parent

            # Default paths for TTL and mapping files
            ttl_path = project_root / "assets" / "schema" / "1216.ttl"
            mapping_path = project_root / "assets" / "schema" / "db_to_ttl_mapping.json"

            # Allow override from config
            if self.curr_config.ttl_path:
                ttl_path = Path(self.curr_config.ttl_path)
            if self.curr_config.source_mapping_path:
                mapping_path = Path(self.curr_config.source_mapping_path)

            if ttl_path.exists() and mapping_path.exists():
                logger.info(f"Initializing semantic index from TTL: {ttl_path}")
                _semantic_index = initialize_semantic_index(str(ttl_path), str(mapping_path))

                # Load semantic dictionary if available
                dict_path = project_root / "assets" / "schema" / "semantic_dictionary.json"
                if dict_path.exists():
                    _semantic_index.load_dictionary(str(dict_path))
                    logger.info(f"Loaded semantic dictionary: {_semantic_index.dictionary.get_stats()}")

                stats = _semantic_index.get_stats()
                logger.info(f"Semantic index initialized: {stats}")
                return _semantic_index
            else:
                if not ttl_path.exists():
                    logger.warning(f"TTL file not found: {ttl_path}")
                if not mapping_path.exists():
                    logger.warning(f"Mapping file not found: {mapping_path}")

        except Exception as e:
            logger.error(f"Failed to initialize semantic index: {e}")

        return None

    def _build_semantic_context(self, user_input: str) -> str:
        """Build semantic context for the user query.

        This method uses the semantic index to:
        1. Find relevant properties by matching Chinese terms in the query
        2. Extract semantic information (comments, examples, enum values)
        3. Identify potential JOIN relationships

        Args:
            user_input: User's natural language query

        Returns:
            Formatted semantic context string for prompt enhancement
        """
        if not self.semantic_index:
            return ""

        try:
            semantic_context = self.semantic_index.build_semantic_context(
                user_input, max_properties=8
            )
            return semantic_context
        except Exception as e:
            logger.warning(f"Failed to build semantic context: {e}")
            return ""

    def _get_source_mapping(self) -> Dict:
        """Get source mapping from config or default file.

        Returns:
            Dict: OWL to MySQL schema mapping
        """
        # Try to get from config first
        if self.curr_config.source_mapping:
            try:
                return json.loads(self.curr_config.source_mapping)
            except json.JSONDecodeError:
                logger.warning("Invalid source_mapping JSON, trying default file")
        
        # Try to load from default mapping file
        try:
            # Get project root directory
            current_file = Path(__file__)
            # Current file is in: packages/dbgpt-app/src/dbgpt_app/scene/chat_db/ontology_execute/chat.py
            # Need to go up 8 levels to reach project root: /Users/lusain/ai/DB-GPT/
            project_root = current_file.parent.parent.parent.parent.parent.parent.parent.parent
            mapping_file = project_root / "assets" / "schema" / "db_to_ttl_mapping.json"
            
            if mapping_file.exists():
                logger.info(f"Loading source mapping from: {mapping_file}")
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    # Convert list format to dict format for easier lookup
                    mapping_dict = {}
                    for table_mapping in mapping_data:
                        table_name = table_mapping.get("table_name")
                        if table_name:
                            mapping_dict[table_name] = table_mapping
                    logger.info(f"Loaded {len(mapping_dict)} table mappings")
                    return mapping_dict
            else:
                logger.warning(f"Mapping file not found: {mapping_file}")
        except Exception as e:
            logger.error(f"Failed to load source mapping file: {str(e)}")
        
        return {}

    @trace()
    async def _get_graph_schema(self) -> str:
        """Fetch graph schema from knowledge graph.

        This method retrieves the ontology schema from a configured graph store
        (Neo4j or TuGraph) to provide semantic context for SQL generation.

        Returns:
            str: Graph schema description
        """
        if not self.graph_store_name:
            return "No graph store configured"

        try:
            # Try to get graph connector from ConnectorManager
            local_db_manager = ConnectorManager.get_instance(self.system_app)
            graph_connector = local_db_manager.get_connector(self.graph_store_name)

            # Check if it's a graph database connector
            if hasattr(graph_connector, "is_graph_type") and graph_connector.is_graph_type():
                schema_parts = ["OWL Ontology Schema from Neo4j:"]

                # Try to get OWL Classes
                try:
                    class_query = """
                    MATCH (c:Class)
                    RETURN c.name as class_name
                    LIMIT 20
                    """
                    class_results = graph_connector.run(class_query)
                    classes = [r["class_name"] for r in class_results if r.get("class_name")]
                    if classes:
                        schema_parts.append(f"\nOWL Classes: {', '.join(classes)}")
                except Exception as e:
                    logger.debug(f"Failed to query OWL Classes: {e}")

                # Try to get DataProperties
                try:
                    data_prop_query = """
                    MATCH (dp:DataProperty)
                    RETURN dp.name as property_name
                    LIMIT 20
                    """
                    data_prop_results = graph_connector.run(data_prop_query)
                    data_props = [r["property_name"] for r in data_prop_results if r.get("property_name")]
                    if data_props:
                        schema_parts.append(f"\nData Properties: {', '.join(data_props[:10])}")
                except Exception as e:
                    logger.debug(f"Failed to query DataProperties: {e}")

                # Try to get ObjectProperties
                try:
                    obj_prop_query = """
                    MATCH (op:ObjectProperty)
                    RETURN op.name as property_name
                    LIMIT 20
                    """
                    obj_prop_results = graph_connector.run(obj_prop_query)
                    obj_props = [r["property_name"] for r in obj_prop_results if r.get("property_name")]
                    if obj_props:
                        schema_parts.append(f"\nObject Properties (Relationships): {', '.join(obj_props[:10])}")
                except Exception as e:
                    logger.debug(f"Failed to query ObjectProperties: {e}")

                # Fallback: Get node labels if OWL queries fail
                if len(schema_parts) == 1:  # Only the header line
                    if hasattr(graph_connector, "get_table_names"):
                        table_names = list(graph_connector.get_table_names())
                        node_labels = [
                            t.replace("_node", "")
                            for t in table_names
                            if t.endswith("_node")
                        ]
                        if node_labels:
                            schema_parts.append(f"\nNode Labels: {', '.join(node_labels)}")

                return "\n".join(schema_parts) if len(schema_parts) > 1 else "Graph schema empty"
            else:
                return "Configured store is not a graph database"

        except Exception as e:
            logger.error(f"Failed to get graph schema: {str(e)}")
            return f"Error fetching graph schema: {str(e)}"

    @trace()
    async def generate_input_values(self) -> Dict:
        """Generate input values for the prompt template.

        This method extends the standard generate_input_values to include:
        - graph_schema: Schema from knowledge graph
        - source_mapping: OWL to MySQL mapping
        """
        try:
            from dbgpt_serve.datasource.service.db_summary_client import DBSummaryClient
        except ImportError:
            raise ValueError("Could not import DBSummaryClient.")

        user_input = self.current_user_input.last_text
        client = DBSummaryClient(system_app=self.system_app)

        # Fetch table info (same as auto_execute)
        try:
            with root_tracer.start_span("ChatWithDbOntologyExecute.get_db_summary"):
                table_infos = await blocking_func_to_async(
                    self._executor,
                    client.get_db_summary,
                    self.db_name,
                    user_input,
                    self.curr_config.schema_retrieve_top_k,
                )
        except Exception as e:
            logger.error(f"Retrieved table info error: {str(e)}")
            table_infos = await blocking_func_to_async(
                self._executor, self.database.table_simple_info
            )
            if len(table_infos) > self.curr_config.schema_max_tokens:
                table_infos = table_infos[: self.curr_config.schema_max_tokens]

        # Fetch graph schema
        with root_tracer.start_span("ChatWithDbOntologyExecute.get_graph_schema"):
            graph_schema = await self._get_graph_schema()

        # Build semantic context from TTL ontology (Vanna-inspired enhancement)
        with root_tracer.start_span("ChatWithDbOntologyExecute.build_semantic_context"):
            semantic_context = self._build_semantic_context(user_input)
            if semantic_context:
                logger.info(f"Built semantic context ({len(semantic_context)} chars)")

        # Format source mapping for prompt (compact SQL-friendly format)
        if self.source_mapping:
            source_mapping_lines = ["MySQL Tables:"]
            for table_name, mapping in self.source_mapping.items():
                columns = mapping.get("columns", [])
                col_names = [c.get("column_name", "") for c in columns]
                fk_cols = [
                    c.get("column_name", "")
                    for c in columns
                    if c.get("property_type") == "ObjectProperty"
                ]
                # Compact format: table(col1, col2, ...) FK: [fk1, fk2]
                cols_str = ", ".join(col_names)
                line = f"  {table_name}({cols_str})"
                if fk_cols:
                    line += f" FK:[{','.join(fk_cols)}]"
                source_mapping_lines.append(line)
            source_mapping_str = "\n".join(source_mapping_lines)
        else:
            source_mapping_str = "No source mapping"

        input_values = {
            "db_name": self.db_name,
            "user_input": user_input,
            "top_k": self.curr_config.max_num_results,
            "dialect": self.database.dialect,
            "table_info": table_infos,
            "display_type": self._generate_numbered_list(),
            # Ontology-specific values
            "graph_schema": graph_schema,
            "source_mapping": source_mapping_str,
            # Semantic enhancement (Vanna-inspired)
            "semantic_context": semantic_context,
            # Domain rules for business context
            "domain_rules": self.domain_rules,
        }
        return input_values

    def do_action(self, prompt_response):
        """Execute the SQL action.

        Args:
            prompt_response: The parsed response from the LLM

        Returns:
            The database run_to_df function for executing SQL
        """
        print(f"do_action:{prompt_response}")
        return self.database.run_to_df
