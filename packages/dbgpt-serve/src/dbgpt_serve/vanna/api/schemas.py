"""Vanna API Pydantic Schemas.

This module defines the request/response models for Vanna API endpoints.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TrainingRequest(BaseModel):
    """Request model for adding training data."""

    db_name: str = Field(..., description="Target database name")
    type: Literal["ddl", "sql", "documentation"] = Field(
        ..., description="Type of training data"
    )
    content: str = Field(
        ..., description="Training content (DDL/SQL/documentation text)"
    )
    question: Optional[str] = Field(
        None, description="Natural language question (required for type=sql)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "db_name": "mydb",
                    "type": "ddl",
                    "content": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))",
                },
                {
                    "db_name": "mydb",
                    "type": "sql",
                    "content": "SELECT * FROM users WHERE status = 'active'",
                    "question": "Show all active users",
                },
                {
                    "db_name": "mydb",
                    "type": "documentation",
                    "content": "The 'status' column uses: 1=active, 2=inactive",
                },
            ]
        }


class TrainingResponse(BaseModel):
    """Response model for training operations."""

    success: bool = Field(..., description="Operation success status")
    id: Optional[str] = Field(None, description="Created training data ID")
    message: str = Field(..., description="Success/error message")


class SchemaTrainingResponse(BaseModel):
    """Response model for schema training operations."""

    success: bool = Field(..., description="Operation success status")
    tables_trained: int = Field(..., description="Number of tables trained")
    message: str = Field(..., description="Success/error message")


class TrainingDataItem(BaseModel):
    """Model for a single training data item."""

    id: str = Field(..., description="Training data ID")
    db_name: str = Field(..., description="Database name")
    type: str = Field(..., description="Training data type (ddl/sql/doc)")
    content: str = Field(..., description="Training content")
    question: Optional[str] = Field(None, description="Question for SQL type")
    created_at: datetime = Field(..., description="Creation timestamp")


class TrainingDataList(BaseModel):
    """Response model for listing training data."""

    total: int = Field(..., description="Total count of training data")
    items: List[TrainingDataItem] = Field(..., description="Training data items")


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Success/error message")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
