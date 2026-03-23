"""ChromaDB implementation of Vanna Training Store.

This module provides ChromaDB-backed storage for Vanna training data.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from dbgpt_ext.vanna.config import VannaConfig
from dbgpt_ext.vanna.store.base import VannaTrainingStoreBase
from dbgpt_ext.vanna.types import (
    AgentMemoryEntry,
    BusinessDocument,
    QuestionSqlPair,
    TrainingData,
    TrainingDataType,
)

logger = logging.getLogger(__name__)


class ChromaDBVannaStore(VannaTrainingStoreBase):
    """ChromaDB-backed training store for Vanna.

    Stores training data in three separate collections per database:
    - vanna_{db_name}_ddl: DDL statements
    - vanna_{db_name}_sql: Question-SQL pairs
    - vanna_{db_name}_doc: Documentation

    Args:
        config: Vanna configuration.
        embedding_fn: Embedding function for generating vectors.
    """

    def __init__(
        self,
        config: VannaConfig,
        embedding_fn: Any,
    ) -> None:
        """Initialize ChromaDB Vanna Store.

        Args:
            config: Vanna configuration with chroma_path.
            embedding_fn: DB-GPT Embeddings instance for vector generation.
        """
        try:
            from chromadb import PersistentClient, Settings
        except ImportError:
            raise ImportError(
                "chromadb is required for ChromaDBVannaStore. "
                "Install with: pip install chromadb"
            )

        self._config = config
        self._embedding_fn = embedding_fn

        settings = Settings(
            persist_directory=config.chroma_path,
            anonymized_telemetry=False,
        )
        self._client = PersistentClient(
            path=config.chroma_path,
            settings=settings,
        )
        self._collections: Dict[str, Any] = {}

    def _get_collection(self, db_name: str, data_type: str) -> Any:
        """Get or create a ChromaDB collection.

        Args:
            db_name: Database name.
            data_type: Data type ('ddl', 'sql', or 'doc').

        Returns:
            ChromaDB collection.
        """
        collection_name = f"vanna_{db_name}_{data_type}"
        if collection_name not in self._collections:
            self._collections[collection_name] = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[collection_name]

    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        return self._embedding_fn.embed_query(text)

    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        return self._embedding_fn.embed_documents(texts)

    def add_ddl(self, db_name: str, ddl: str) -> str:
        """Add a DDL statement to the training store."""
        collection = self._get_collection(db_name, "ddl")
        id = self.generate_ddl_id(ddl)

        # Check for duplicate
        existing = collection.get(ids=[id])
        if existing and existing.get("ids"):
            logger.debug(f"DDL already exists with ID {id}")
            return id

        embedding = self._embed(ddl)
        collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[ddl],
            metadatas=[{
                "db_name": db_name,
                "type": TrainingDataType.DDL.value,
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        logger.info(f"Added DDL to training store: {id}")
        return id

    def add_sql(self, db_name: str, question: str, sql: str) -> str:
        """Add a question-SQL pair to the training store."""
        collection = self._get_collection(db_name, "sql")
        id = self.generate_sql_id(question, sql)

        # Check for duplicate
        existing = collection.get(ids=[id])
        if existing and existing.get("ids"):
            logger.debug(f"SQL example already exists with ID {id}")
            return id

        # Store as JSON document, embed based on question for similarity search
        content = json.dumps({"question": question, "sql": sql})
        embedding = self._embed(question)
        collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "db_name": db_name,
                "type": TrainingDataType.SQL.value,
                "question": question,
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        logger.info(f"Added SQL example to training store: {id}")
        return id

    def add_documentation(self, db_name: str, documentation: str) -> str:
        """Add documentation to the training store."""
        collection = self._get_collection(db_name, "doc")
        id = self.generate_doc_id(documentation)

        # Check for duplicate
        existing = collection.get(ids=[id])
        if existing and existing.get("ids"):
            logger.debug(f"Documentation already exists with ID {id}")
            return id

        embedding = self._embed(documentation)
        collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[documentation],
            metadatas=[{
                "db_name": db_name,
                "type": TrainingDataType.DOCUMENTATION.value,
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        logger.info(f"Added documentation to training store: {id}")
        return id

    def get_similar_ddl(
        self, db_name: str, question: str, n_results: int = 5
    ) -> List[str]:
        """Get DDL statements similar to the question."""
        collection = self._get_collection(db_name, "ddl")

        if collection.count() == 0:
            return []

        query_embedding = self._embed(question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
        )

        if results and results.get("documents"):
            return results["documents"][0]
        return []

    def get_similar_sql(
        self, db_name: str, question: str, n_results: int = 5
    ) -> List[QuestionSqlPair]:
        """Get SQL examples similar to the question."""
        collection = self._get_collection(db_name, "sql")

        if collection.count() == 0:
            return []

        query_embedding = self._embed(question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
        )

        pairs = []
        if results and results.get("documents"):
            for doc in results["documents"][0]:
                try:
                    data = json.loads(doc)
                    pairs.append(QuestionSqlPair(
                        question=data["question"],
                        sql=data["sql"],
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse SQL document: {e}")
        return pairs

    def get_related_documentation(
        self, db_name: str, question: str, n_results: int = 3
    ) -> List[str]:
        """Get documentation related to the question."""
        collection = self._get_collection(db_name, "doc")

        if collection.count() == 0:
            return []

        query_embedding = self._embed(question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
        )

        if results and results.get("documents"):
            return results["documents"][0]
        return []

    def get_all(
        self,
        db_name: str,
        type_filter: Optional[TrainingDataType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TrainingData]:
        """Get all training data for a database."""
        all_data = []

        types_to_query = (
            [type_filter] if type_filter
            else [TrainingDataType.DDL, TrainingDataType.SQL, TrainingDataType.DOCUMENTATION]
        )

        for data_type in types_to_query:
            type_suffix = {
                TrainingDataType.DDL: "ddl",
                TrainingDataType.SQL: "sql",
                TrainingDataType.DOCUMENTATION: "doc",
            }[data_type]

            collection = self._get_collection(db_name, type_suffix)
            results = collection.get()

            if results and results.get("ids"):
                for i, id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i] if results.get("metadatas") else {}
                    document = results["documents"][i] if results.get("documents") else ""

                    # Parse question from SQL type documents
                    question = None
                    content = document
                    if data_type == TrainingDataType.SQL:
                        try:
                            data = json.loads(document)
                            question = data.get("question")
                            content = data.get("sql", document)
                        except json.JSONDecodeError:
                            pass

                    all_data.append(TrainingData(
                        id=id,
                        db_name=db_name,
                        type=data_type,
                        content=content,
                        question=question,
                        created_at=datetime.fromisoformat(
                            metadata.get("created_at", datetime.utcnow().isoformat())
                        ),
                        metadata=metadata,
                    ))

        # Apply pagination
        return all_data[offset:offset + limit]

    def remove(self, id: str) -> bool:
        """Remove training data by ID."""
        # Determine type from ID suffix
        if id.endswith("-ddl"):
            type_suffix = "ddl"
        elif id.endswith("-sql"):
            type_suffix = "sql"
        elif id.endswith("-doc"):
            type_suffix = "doc"
        else:
            logger.warning(f"Unknown ID format: {id}")
            return False

        # Try all databases (we don't have db_name in the ID)
        for collection_name, collection in self._collections.items():
            if collection_name.endswith(f"_{type_suffix}"):
                try:
                    existing = collection.get(ids=[id])
                    if existing and existing.get("ids"):
                        collection.delete(ids=[id])
                        logger.info(f"Removed training data: {id}")
                        return True
                except Exception as e:
                    logger.debug(f"Error checking collection {collection_name}: {e}")

        logger.warning(f"Training data not found: {id}")
        return False

    def get_training_data_count(self, db_name: str) -> Dict[str, int]:
        """Get count of training data by type.

        Args:
            db_name: Database name.

        Returns:
            Dictionary with counts per type.
        """
        return {
            "ddl": self._get_collection(db_name, "ddl").count(),
            "sql": self._get_collection(db_name, "sql").count(),
            "doc": self._get_collection(db_name, "doc").count(),
            "memory": self._get_collection(db_name, "memory").count(),
            "ontology": self._get_collection(db_name, "ontology").count(),
            "bizdoc": self._get_collection(db_name, "bizdoc").count(),
        }

    # ========== Agent Memory Implementation ==========

    def add_memory(
        self,
        db_name: str,
        question: str,
        sql: str,
        result_summary: Optional[str] = None,
    ) -> str:
        """Add a successful Q&A pair to agent memory."""
        collection = self._get_collection(db_name, "memory")
        id = self.generate_memory_id(question, sql)

        # Check for duplicate
        existing = collection.get(ids=[id])
        if existing and existing.get("ids"):
            # Update success count
            logger.debug(f"Memory already exists with ID {id}, incrementing count")
            self.increment_memory_success(id)
            return id

        # Store as JSON document with question for embedding
        content = json.dumps({
            "question": question,
            "sql": sql,
            "result_summary": result_summary,
            "success_count": 1,
        })
        embedding = self._embed(question)
        collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "db_name": db_name,
                "type": TrainingDataType.MEMORY.value,
                "question": question,
                "success_count": 1,
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        logger.info(f"Added memory entry: {id}")
        return id

    def search_memory(
        self,
        db_name: str,
        question: str,
        n_results: int = 3,
        similarity_threshold: float = 0.85,
    ) -> List[AgentMemoryEntry]:
        """Search agent memory for similar questions."""
        collection = self._get_collection(db_name, "memory")

        if collection.count() == 0:
            return []

        query_embedding = self._embed(question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        entries = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                try:
                    # ChromaDB returns distances (lower is better for cosine)
                    # Convert to similarity: similarity = 1 - distance
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    similarity = 1 - distance

                    if similarity < similarity_threshold:
                        continue

                    data = json.loads(doc)
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    entries.append(AgentMemoryEntry(
                        id=results["ids"][0][i],
                        db_name=db_name,
                        question=data["question"],
                        sql=data["sql"],
                        result_summary=data.get("result_summary"),
                        success_count=data.get("success_count", 1),
                        created_at=datetime.fromisoformat(
                            metadata.get("created_at", datetime.utcnow().isoformat())
                        ),
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse memory document: {e}")

        return entries

    def increment_memory_success(self, memory_id: str) -> bool:
        """Increment the success count for a memory entry."""
        # Find the collection containing this memory
        for collection_name, collection in self._collections.items():
            if collection_name.endswith("_memory"):
                try:
                    existing = collection.get(ids=[memory_id])
                    if existing and existing.get("ids"):
                        # Update metadata
                        metadata = existing["metadatas"][0]
                        metadata["success_count"] = metadata.get("success_count", 1) + 1

                        # Update document
                        doc = json.loads(existing["documents"][0])
                        doc["success_count"] = doc.get("success_count", 1) + 1

                        collection.update(
                            ids=[memory_id],
                            documents=[json.dumps(doc)],
                            metadatas=[metadata],
                        )
                        logger.debug(f"Incremented success count for memory: {memory_id}")
                        return True
                except Exception as e:
                    logger.debug(f"Error updating memory {memory_id}: {e}")
        return False

    # ========== Ontology Implementation ==========

    def add_ontology(
        self,
        db_name: str,
        content: str,
        format: str = "ttl",
        description: Optional[str] = None,
    ) -> str:
        """Add ontology content to the store."""
        collection = self._get_collection(db_name, "ontology")
        id = self.generate_ontology_id(content)

        # Check for duplicate
        existing = collection.get(ids=[id])
        if existing and existing.get("ids"):
            logger.debug(f"Ontology already exists with ID {id}")
            return id

        # Store the full ontology content
        doc_content = json.dumps({
            "content": content,
            "format": format,
            "description": description,
        })

        # Embed based on description or first 1000 chars of content
        embed_text = description or content[:1000]
        embedding = self._embed(embed_text)

        collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[doc_content],
            metadatas=[{
                "db_name": db_name,
                "type": TrainingDataType.ONTOLOGY.value,
                "format": format,
                "description": description or "",
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        logger.info(f"Added ontology to training store: {id}")
        return id

    def get_ontology(self, db_name: str) -> Optional[str]:
        """Get the ontology content for a database."""
        collection = self._get_collection(db_name, "ontology")

        if collection.count() == 0:
            return None

        # Get all ontology entries (typically just one per db)
        results = collection.get()
        if results and results.get("documents"):
            # Combine all ontology content
            ontology_parts = []
            for doc in results["documents"]:
                try:
                    data = json.loads(doc)
                    content = data.get("content", "")
                    format_type = data.get("format", "ttl")
                    ontology_parts.append(f"[{format_type.upper()}]\n{content}")
                except json.JSONDecodeError:
                    ontology_parts.append(doc)
            return "\n\n".join(ontology_parts)
        return None

    # ========== Business Document Implementation ==========

    def add_business_document(
        self,
        db_name: str,
        title: str,
        content: str,
        category: str = "general",
    ) -> str:
        """Add a business document to the store."""
        collection = self._get_collection(db_name, "bizdoc")
        id = self.generate_business_doc_id(title, content)

        # Check for duplicate
        existing = collection.get(ids=[id])
        if existing and existing.get("ids"):
            logger.debug(f"Business document already exists with ID {id}")
            return id

        # Store as JSON document
        doc_content = json.dumps({
            "title": title,
            "content": content,
            "category": category,
        })

        # Embed based on title + first 500 chars of content
        embed_text = f"{title}\n{content[:500]}"
        embedding = self._embed(embed_text)

        collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[doc_content],
            metadatas=[{
                "db_name": db_name,
                "type": "bizdoc",
                "title": title,
                "category": category,
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        logger.info(f"Added business document to training store: {id}")
        return id

    def get_related_business_docs(
        self,
        db_name: str,
        question: str,
        n_results: int = 2,
    ) -> List[BusinessDocument]:
        """Get business documents related to the question."""
        collection = self._get_collection(db_name, "bizdoc")

        if collection.count() == 0:
            return []

        query_embedding = self._embed(question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
        )

        docs = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                try:
                    data = json.loads(doc)
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    docs.append(BusinessDocument(
                        id=results["ids"][0][i],
                        db_name=db_name,
                        title=data.get("title", ""),
                        content=data.get("content", ""),
                        category=data.get("category", "general"),
                        created_at=datetime.fromisoformat(
                            metadata.get("created_at", datetime.utcnow().isoformat())
                        ),
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse business document: {e}")

        return docs
