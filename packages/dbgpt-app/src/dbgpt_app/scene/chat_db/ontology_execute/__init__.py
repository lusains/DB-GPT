"""Chat with Database Execute - Ontology Enhanced.

This module provides ontology-aware SQL generation using:
1. OWL/TTL ontology parsing for semantic understanding
2. Source mapping for OWL-to-MySQL translation
3. Semantic context enhancement (Vanna-inspired RAG approach)

Key Components:
- ChatWithDbOntologyExecute: Main chat class with ontology support
- OntologySemanticIndex: Semantic index for fast lookups
- ChatWithDBExecuteOntologyConfig: Configuration options
"""

from dbgpt_app.scene.chat_db.ontology_execute.chat import ChatWithDbOntologyExecute
from dbgpt_app.scene.chat_db.ontology_execute.config import (
    ChatWithDBExecuteOntologyConfig,
)
from dbgpt_app.scene.chat_db.ontology_execute.semantic_index import (
    OntologySemanticIndex,
    SemanticDictionary,
    TermMapping,
    get_semantic_index,
    initialize_semantic_index,
)

__all__ = [
    "ChatWithDbOntologyExecute",
    "ChatWithDBExecuteOntologyConfig",
    "OntologySemanticIndex",
    "SemanticDictionary",
    "TermMapping",
    "get_semantic_index",
    "initialize_semantic_index",
]
