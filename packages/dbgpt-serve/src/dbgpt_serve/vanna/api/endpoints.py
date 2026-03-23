"""Vanna API Endpoints.

This module provides REST API endpoints for Vanna training data management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from dbgpt.component import ComponentType, SystemApp
from dbgpt.core import Embeddings
from dbgpt.rag.embedding import EmbeddingFactory
from dbgpt_ext.vanna import (
    ChromaDBVannaStore,
    TrainingDataType,
    VannaConfig,
    VannaContextRetriever,
    VannaTrainingService,
)
from dbgpt_serve.datasource.manages.connector_manager import ConnectorManager

from .schemas import (
    DeleteResponse,
    SchemaTrainingResponse,
    TrainingDataItem,
    TrainingDataList,
    TrainingRequest,
    TrainingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

global_system_app: Optional[SystemApp] = None
_vanna_service: Optional[VannaTrainingService] = None
_vanna_config: Optional[VannaConfig] = None


def init_endpoints(system_app: SystemApp, config: Optional[VannaConfig] = None):
    """Initialize the Vanna API endpoints.

    Args:
        system_app: The DB-GPT system app.
        config: Optional Vanna configuration.
    """
    global global_system_app, _vanna_config
    global_system_app = system_app
    _vanna_config = config or VannaConfig()


def _get_embeddings() -> Embeddings:
    """Get the embedding function from system app."""
    embedding_factory = EmbeddingFactory.get_instance(global_system_app)
    return embedding_factory.create()


def _get_vanna_service() -> VannaTrainingService:
    """Get or create the Vanna training service."""
    global _vanna_service
    if _vanna_service is None:
        config = _vanna_config or VannaConfig()
        embedding_fn = _get_embeddings()
        store = ChromaDBVannaStore(config=config, embedding_fn=embedding_fn)
        _vanna_service = VannaTrainingService(store=store, config=config)
    return _vanna_service


def _get_connector_manager() -> ConnectorManager:
    """Get the connector manager from system app."""
    return ConnectorManager.get_instance(global_system_app)


@router.post("/train", response_model=TrainingResponse)
async def add_training_data(request: TrainingRequest):
    """Add training data to the Vanna store.

    Supports DDL, SQL examples, and documentation.
    """
    try:
        service = _get_vanna_service()

        if request.type == "ddl":
            id = service.add_ddl(request.db_name, request.content)
        elif request.type == "sql":
            if not request.question:
                raise HTTPException(
                    status_code=400,
                    detail="question is required for SQL training data",
                )
            id = service.add_question_sql(
                request.db_name, request.question, request.content
            )
        elif request.type == "documentation":
            id = service.add_documentation(request.db_name, request.content)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown type: {request.type}")

        return TrainingResponse(
            success=True,
            id=id,
            message="Training data added successfully",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to add training data")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-schema/{db_name}", response_model=SchemaTrainingResponse)
async def train_schema(db_name: str):
    """Auto-train from database schema.

    Extracts DDL from all tables in the database and adds to training store.
    """
    try:
        service = _get_vanna_service()
        connector_manager = _get_connector_manager()

        # Get database connector
        try:
            connector = connector_manager.get_connector(db_name)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Database '{db_name}' not found: {str(e)}",
            )

        # Train schema
        tables_trained = service.train_schema(db_name, connector)

        return SchemaTrainingResponse(
            success=True,
            tables_trained=tables_trained,
            message=f"Schema training completed: {tables_trained} tables",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to train schema")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-data/{db_name}", response_model=TrainingDataList)
async def list_training_data(
    db_name: str,
    type: Optional[str] = Query(None, description="Filter by type (ddl/sql/documentation)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """List training data for a database.

    Supports filtering by type and pagination.
    """
    try:
        service = _get_vanna_service()

        # Convert type string to enum
        type_filter = None
        if type:
            type_map = {
                "ddl": TrainingDataType.DDL,
                "sql": TrainingDataType.SQL,
                "documentation": TrainingDataType.DOCUMENTATION,
                "doc": TrainingDataType.DOCUMENTATION,
            }
            type_filter = type_map.get(type.lower())
            if type_filter is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid type: {type}. Use ddl, sql, or documentation",
                )

        data = service.get_training_data(
            db_name=db_name,
            type_filter=type_filter,
            limit=limit,
            offset=offset,
        )

        items = [
            TrainingDataItem(
                id=item.id,
                db_name=item.db_name,
                type=item.type.value,
                content=item.content,
                question=item.question,
                created_at=item.created_at,
            )
            for item in data
        ]

        return TrainingDataList(
            total=len(items),  # Note: This is page count, not total
            items=items,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list training data")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/training-data/{id}", response_model=DeleteResponse)
async def delete_training_data(id: str):
    """Delete training data by ID."""
    try:
        service = _get_vanna_service()
        removed = service.remove_training_data(id)

        if removed:
            return DeleteResponse(success=True, message="Training data deleted")
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Training data not found: {id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete training data")
        raise HTTPException(status_code=500, detail=str(e))


def get_vanna_retriever() -> VannaContextRetriever:
    """Get the Vanna context retriever.

    This is used by ChatWithDbVanna to retrieve context for SQL generation.
    """
    service = _get_vanna_service()
    config = _vanna_config or VannaConfig()
    return VannaContextRetriever(store=service._store, config=config)
