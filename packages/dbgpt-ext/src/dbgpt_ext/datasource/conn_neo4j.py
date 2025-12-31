#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional

from dbgpt.datasource.base import BaseConnector
from dbgpt.vis.tags import Vis, vis_tags


@vis_tags(vis_type=Vis.VIS_GRAPH)
class PNeo4jConnector(BaseConnector[Any]):
    """Neo4j Connector for DB-GPT"""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Neo4j connector.
        Args:
            uri (str): The uri of the Neo4j database.
            user (str): The user of the Neo4j database.
            password (str): The password of the Neo4j database.
        """
        super().__init__(**kwargs)
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def connect(self) -> Any:
        """Connect to the Neo4j database."""
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError(
                "Please install neo4j (`pip install neo4j`) to use this connector."
            )
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self) -> None:
        """Close the connection to the Neo4j database."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def get_session(self) -> Any:
        """Get a session from the driver."""
        if not self._driver:
            self.connect()
        return self._driver.session()

    def run(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """Run a query on the Neo4j database.
        Args:
            query (str): The query to run.
        Returns:
            List[Dict[str, Any]]: The result of the query.
        """
        with self.get_session() as session:
            result = session.run(query, **kwargs)
            return [record.data() for record in result]

    def get_table_names(self) -> List[str]:
        """Get the names of the tables in the database."""
        with self.get_session() as session:
            result = session.run("CALL db.labels()")
            return [record["label"] for record in result]

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get the info of a table.
        Args:
            table_name (str): The name of the table.
        Returns:
            Dict[str, Any]: The info of the table.
        """
        with self.get_session() as session:
            result = session.run(f"MATCH (n:{table_name}) RETURN n LIMIT 1")
            record = result.single()
            if record:
                properties = record["n"].keys()
                return {"properties": properties}
            return {"properties": []}
