#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import MagicMock, patch

import pytest

from dbgpt_ext.datasource.conn_neo4j import PNeo4jConnector


@pytest.fixture
def mock_neo4j_driver():
    with patch("dbgpt_ext.datasource.conn_neo4j.GraphDatabase") as mock_graph_database:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()

        mock_graph_database.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        mock_result.data.return_value = [
            {"label": "TestLabel1"},
            {"label": "TestLabel2"},
        ]
        yield mock_driver


def test_connect(mock_neo4j_driver):
    connector = PNeo4jConnector(
        uri="bolt://localhost:7687", user="neo4j", password="password"
    )
    driver = connector.connect()
    assert driver is not None
    assert driver == mock_neo4j_driver
    connector.close()


def test_run(mock_neo4j_driver):
    connector = PNeo4jConnector(
        uri="bolt://localhost:7687", user="neo4j", password="password"
    )
    result = connector.run("MATCH (n) RETURN n")
    assert result is not None
    connector.close()


def test_get_table_names(mock_neo4j_driver):
    connector = PNeo4jConnector(
        uri="bolt://localhost:7687", user="neo4j", password="password"
    )
    table_names = connector.get_table_names()
    assert table_names == ["TestLabel1", "TestLabel2"]
    connector.close()


if __name__ == "__main__":
    unittest.main()
