"""Vanna.AI 2.0 inspired Text2SQL tools for DB-GPT agents.

Following Vanna 2.0 architecture where:
1. Agent gets database schema via get_database_schema tool
2. Agent generates SQL based on schema and user question
3. Agent executes SQL via run_sql tool

This enables full Text2SQL workflow with clean separation of concerns.
"""

import logging
from typing import Optional

import pandas as pd
from typing_extensions import Annotated, Doc

from ...resource.tool.base import tool

logger = logging.getLogger(__name__)


@tool(
    description=(
        "Get database schema information including tables, columns, and types. "
        "Use this to understand database structure before generating SQL queries. "
        "Returns detailed schema information for the specified database."
    ),
)
def get_database_schema(
    database_name: Annotated[
        str, Doc("Database identifier to retrieve schema from (e.g., 'sales_db').")
    ],
    table_names: Annotated[
        Optional[str],
        Doc(
            "Optional comma-separated list of specific tables to get schema for. "
            "If not specified, returns schema for all tables."
        ),
    ] = None,
) -> str:
    """Get database schema information for Text2SQL.

    This tool retrieves database structure information including:
    - Available tables
    - Column names and types
    - Primary keys and constraints

    The LLM uses this schema to generate accurate SQL queries.

    Args:
        database_name: Target database name
        table_names: Optional specific tables (comma-separated)

    Returns:
        Formatted schema information as string

    Examples:
        >>> get_database_schema("sales_db")
        # Returns schema for all tables in sales_db

        >>> get_database_schema("sales_db", "customers,orders")
        # Returns schema only for customers and orders tables
    """
    try:
        from dbgpt.component import SystemApp
        from dbgpt_serve.datasource.manages.connector_manager import ConnectorManager

        # Get connector manager from system app
        system_app = SystemApp.get_instance()
        connector_manager: ConnectorManager = system_app.get_component(
            ConnectorManager.name,
            component_type=ConnectorManager,
        )

        # Get database connector
        connector = connector_manager.get_connector(database_name)

        # Get table names
        if table_names:
            tables = [t.strip() for t in table_names.split(",")]
        else:
            tables = list(connector.get_table_names())

        if not tables:
            return f"No tables found in database '{database_name}'"

        # Get schema information
        schema_info = connector.get_table_info(tables)

        result = f"""Database: {database_name}
Available Tables: {', '.join(tables)}

Schema Information:
{schema_info}
"""

        logger.info(
            f"Retrieved schema for database '{database_name}', tables: {tables}"
        )
        return result

    except Exception as e:
        error_msg = f"Failed to get schema for database '{database_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@tool(
    description=(
        "Execute SQL queries against specified database and return results. "
        "Use this after understanding database schema with get_database_schema. "
        "Supports SELECT, INSERT, UPDATE, DELETE and other SQL operations."
    ),
)
def run_sql(
    sql: Annotated[str, Doc("SQL query to execute (generated based on database schema).")],
    database_name: Annotated[
        str, Doc("Database identifier to execute query against.")
    ],
) -> str:
    """Execute SQL query against database.

    This tool executes SQL queries following Vanna 2.0 pattern:
    1. LLM generates SQL based on schema from get_database_schema
    2. This tool executes the SQL
    3. Returns formatted results

    Args:
        sql: SQL query string to execute
        database_name: Target database name

    Returns:
        Formatted query results or execution status

    Examples:
        >>> run_sql("SELECT * FROM customers LIMIT 5", "sales_db")
        # Returns first 5 customer records

        >>> run_sql("SELECT category, COUNT(*) FROM products GROUP BY category", "sales_db")
        # Returns product count by category
    """
    try:
        from dbgpt.component import SystemApp
        from dbgpt_serve.datasource.manages.connector_manager import ConnectorManager

        # Get connector manager
        system_app = SystemApp.get_instance()
        connector_manager: ConnectorManager = system_app.get_component(
            ConnectorManager.name,
            component_type=ConnectorManager,
        )

        # Get database connector
        connector = connector_manager.get_connector(database_name)

        logger.info(f"Executing SQL on '{database_name}': {sql[:100]}...")

        # Execute SQL and get results as DataFrame
        df: pd.DataFrame = connector.run_to_df(sql)

        # Determine query type
        query_type = sql.strip().upper().split()[0]

        if query_type == "SELECT":
            # Format SELECT results
            if df.empty:
                result = "Query executed successfully. No rows returned."
            else:
                row_count = len(df)
                # Convert to readable format
                result_preview = df.to_string(max_rows=10, max_cols=10)

                if row_count > 10:
                    result = f"""Query returned {row_count} rows (showing first 10):

{result_preview}

... and {row_count - 10} more rows"""
                else:
                    result = f"""Query returned {row_count} rows:

{result_preview}"""

        else:
            # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
            rows_affected = len(df) if not df.empty else 0
            result = f"Query executed successfully. {rows_affected} row(s) affected."

        logger.info(
            f"SQL execution completed on '{database_name}': {query_type} query"
        )
        return result

    except Exception as e:
        error_msg = f"Failed to execute SQL on '{database_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}\n\nSQL: {sql}"
