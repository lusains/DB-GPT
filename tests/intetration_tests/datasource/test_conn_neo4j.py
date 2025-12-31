import pytest
from dbgpt_ext.datasource.conn_neo4j import Neo4jConnector

# --- Test Connection Parameters ---
# Update these if your Neo4j instance is different
HOST = "localhost"
PORT = 7687
USER = "neo4j"
PWD = "password"
DB_NAME = "neo4j"


@pytest.fixture(scope="session")
def connector():
    """
    Pytest fixture to create and tear down a Neo4jConnector instance.
    This runs once for the entire test session.
    """
    try:
        # Initialize connection
        conn = Neo4jConnector.from_uri_db(HOST, PORT, USER, PWD, DB_NAME)

        # --- Setup: Clean database and add test data ---
        conn.run("MATCH (n) DETACH DELETE n")
        conn.run("CREATE (:Person {name: 'Alice', age: 30})")
        conn.run("CREATE (:Person {name: 'Bob', age: 35})")
        conn.run("CREATE (:City {name: 'New York'})")
        conn.run(
            "MATCH (p1:Person {name: 'Alice'}), (p2:Person {name: 'Bob'}) "
            "CREATE (p1)-[:FRIENDS_WITH {since: 2020}]->(p2)"
        )
        conn.run(
            "MATCH (p:Person {name: 'Alice'}), (c:City {name: 'New York'}) "
            "CREATE (p)-[:LIVES_IN]->(c)"
        )
        # Create an index for testing
        conn.run("CREATE INDEX person_name_index IF NOT EXISTS FOR (n:Person) ON (n.name)")

        yield conn

        # --- Teardown: Clean up database ---
        conn.run("MATCH (n) DETACH DELETE n")
        conn.run("DROP INDEX person_name_index IF EXISTS")
        conn.close()

    except Exception as e:
        pytest.fail(f"Failed to connect to Neo4j: {e}")


def test_get_table_names(connector):
    """Test retrieving table names (node labels and relationship types)."""
    table_names = list(connector.get_table_names())

    # Expected tables are node labels and relationship types
    assert "Person_node" in table_names
    assert "City_node" in table_names
    assert "FRIENDS_WITH_relationship" in table_names
    assert "LIVES_IN_relationship" in table_names


def test_get_columns(connector):
    """Test retrieving columns (properties) for a specific node label."""
    # Test for a node label that exists
    columns = connector.get_columns("Person", "node")
    column_names = {col["name"] for col in columns}
    assert "name" in column_names
    assert "age" in column_names

    # Test for a relationship type
    rel_columns = connector.get_columns("FRIENDS_WITH", "relationship")
    rel_column_names = {col["name"] for col in rel_columns}
    assert "since" in rel_column_names

    # Test for a non-existent table
    empty_columns = connector.get_columns("NonExistentLabel", "node")
    assert len(empty_columns) == 0


def test_get_indexes(connector):
    """Test retrieving indexes for a specific node label."""
    indexes = connector.get_indexes("Person", "node")
    assert len(indexes) > 0
    # Check if the created index is found
    assert any(idx["name"] == "person_name_index" for idx in indexes)


def test_run_without_stream(connector):
    """Test the 'run' method for non-streaming queries."""
    query = "MATCH (p:Person) RETURN p.name AS name ORDER BY p.name"
    result = connector.run(query)

    assert len(result) == 2
    # Convert result records to a list of names for easier comparison
    names = [record["name"] for record in result]
    assert names == ["Alice", "Bob"]


def test_run_with_stream(connector):
    """Test the 'run_stream' method for streaming queries."""
    query = "MATCH (p:Person) RETURN p.name AS name ORDER BY p.name"
    result_stream = connector.run_stream(query)

    # Consume the generator and check the results
    results = list(result_stream)
    assert len(results) == 2
    names = [record["name"] for record in results]
    assert names == ["Alice", "Bob"]


def test_is_graph_type(connector):
    """Test if the connector identifies as a graph database."""
    assert connector.is_graph_type() is True
