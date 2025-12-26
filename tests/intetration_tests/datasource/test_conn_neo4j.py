
import os
import pytest
from dbgpt_ext.datasource.conn_neo4j import Neo4jConnector

# --- Neo4j Connection Configuration ---
NEO4J_HOST = os.getenv("NEO4J_HOST", "localhost")
NEO4J_PORT = int(os.getenv("NEO4J_PORT", "7687"))
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

@pytest.fixture
def neo4j_connector():
    """A pytest fixture to create a Neo4jConnector instance and close it after the test."""
    try:
        connector = Neo4jConnector.from_uri_db(
            host=NEO4J_HOST,
            port=NEO4J_PORT,
            user=NEO4J_USER,
            pwd=NEO4J_PASSWORD,
            db_name=NEO4J_DATABASE,
        )
        yield connector
    finally:
        if 'connector' in locals() and connector:
            connector.close()

def test_connection(neo4j_connector):
    """Test if a connection to Neo4j can be successfully established."""
    assert neo4j_connector._driver is not None

def test_run_query(neo4j_connector):
    """Test if a Cypher query can be successfully executed."""
    # Clean up the database
    neo4j_connector.run("MATCH (n) DETACH DELETE n")
    # Create a node
    neo4j_connector.run("CREATE (:TestNode {name: 'test'})")
    # Query the node
    result = neo4j_connector.run("MATCH (n:TestNode) RETURN n.name AS name")
    assert len(result) == 1
    assert result[0]["name"] == "test"

def test_get_table_names(neo4j_connector):
    """Test if node labels and relationship types can be successfully retrieved."""
    # Clean up the database
    neo4j_connector.run("MATCH (n) DETACH DELETE n")
    # Create some data
    neo4j_connector.run("CREATE (:NodeA)-[:REL_A]->(:NodeB)")
    table_names = list(neo4j_connector.get_table_names())
    assert "NodeA_node" in table_names
    assert "NodeB_node" in table_names
    assert "REL_A_relationship" in table_names

def test_get_columns(neo4j_connector):
    """Test if properties of a node or relationship can be successfully retrieved."""
    # Clean up the database
    neo4j_connector.run("MATCH (n) DETACH DELETE n")
    # Create a node with properties
    neo4j_connector.run("CREATE (:NodeC {prop1: 'value1', prop2: 123})")
    columns = neo4j_connector.get_columns("NodeC", "node")
    assert len(columns) == 2
    prop_names = {col["name"] for col in columns}
    assert "prop1" in prop_names
    assert "prop2" in prop_names
