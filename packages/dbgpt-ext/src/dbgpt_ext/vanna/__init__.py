"""Vanna AI Integration for DB-GPT.

This module provides Vanna-style training data management for enhanced Text-to-SQL
generation using RAG (Retrieval-Augmented Generation).

Example:
    >>> from dbgpt_ext.vanna import VannaConfig, VannaTrainingService
    >>> config = VannaConfig(chroma_path="./my_vanna_data")
    >>> service = VannaTrainingService(config)
    >>> service.train_schema("mydb")
"""

from dbgpt_ext.vanna.config import VannaConfig
from dbgpt_ext.vanna.retriever import VannaContextRetriever
from dbgpt_ext.vanna.service import VannaTrainingService
from dbgpt_ext.vanna.store import ChromaDBVannaStore, VannaTrainingStoreBase
from dbgpt_ext.vanna.types import (
    AgentMemoryEntry,
    BusinessDocument,
    EnhancedVannaContext,
    OntologyData,
    QuestionSqlPair,
    TrainingData,
    TrainingDataType,
    VannaContext,
)

__all__ = [
    "VannaConfig",
    "TrainingDataType",
    "TrainingData",
    "QuestionSqlPair",
    "VannaContext",
    "EnhancedVannaContext",
    "AgentMemoryEntry",
    "OntologyData",
    "BusinessDocument",
    "VannaTrainingStoreBase",
    "ChromaDBVannaStore",
    "VannaContextRetriever",
    "VannaTrainingService",
]
