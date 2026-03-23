"""Vanna AI Integration Configuration.

This module defines configuration settings for Vanna training and retrieval.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VannaConfig:
    """Configuration for Vanna training and retrieval behavior.

    Attributes:
        enabled: Enable/disable Vanna features
        vector_store_type: Vector store backend (currently only "chroma" supported)
        chroma_path: ChromaDB persistence path
        n_results_ddl: Top-k for DDL retrieval
        n_results_sql: Top-k for SQL retrieval
        n_results_doc: Top-k for documentation retrieval
        max_context_tokens: Maximum tokens for context

        # Agent Memory settings
        memory_enabled: Enable agent memory for learning from successful interactions
        n_results_memory: Top-k for memory retrieval
        memory_similarity_threshold: Minimum similarity score for memory matches (0-1)
        auto_save_successful: Automatically save successful Q&A pairs to memory

        # Ontology settings
        ontology_enabled: Enable ontology injection
        ontology_files: List of ontology file paths (TTL, OWL, etc.)
        ontology_max_tokens: Maximum tokens for ontology content

        # Business Document settings
        business_docs_enabled: Enable business documentation
        business_docs_paths: List of business document file paths
        n_results_business_docs: Top-k for business doc retrieval
    """

    # Core settings
    enabled: bool = True
    vector_store_type: str = "chroma"
    chroma_path: str = "./vanna_data"
    n_results_ddl: int = 5
    n_results_sql: int = 5
    n_results_doc: int = 3
    max_context_tokens: int = 4000

    # Agent Memory settings
    memory_enabled: bool = True
    n_results_memory: int = 3
    memory_similarity_threshold: float = 0.85
    auto_save_successful: bool = True

    # Ontology settings
    ontology_enabled: bool = True
    ontology_files: List[str] = field(default_factory=list)
    ontology_max_tokens: int = 8000

    # Business Document settings
    business_docs_enabled: bool = True
    business_docs_paths: List[str] = field(default_factory=list)
    n_results_business_docs: int = 2
