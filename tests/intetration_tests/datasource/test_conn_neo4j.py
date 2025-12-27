import pytest
from dbgpt_ext.datasource.conn_neo4j import Neo4jConnector

@pytest.fixture
def neo4j_connector():
    # Setup Neo4jConnector for testing
    # Make sure you have a Neo4j instance running
    connector = Neo4jConnector.from_uri_db(uri="bolt://localhost:7687", user="neo4j", password="password", db_name="neo4j")
    return connector

def test_get_session(neo4j_connector):
    # Test getting a session
    session = neo4j_connector.get_session()
    assert session is not None
    session.close()

def test_run(neo4j_connector):
    # Test running a query
    with neo4j_connector.get_session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS count")
        record = result.single()
        assert record is not None
        assert "count" in record

def test_close(neo4j_connector):
    # Test closing the connection
    neo4j_connector.close()
    assert neo4j_connector._driver is None
