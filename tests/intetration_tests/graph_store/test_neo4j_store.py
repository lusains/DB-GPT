
import os
import pytest
from dbgpt.storage.graph_store.graph import MemoryGraph, Edge, Vertex
from dbgpt_ext.storage.graph_store.neo4j_store import Neo4jStore
from dbgpt.storage.graph_store.graph import GraphStoreConfig

# --- Neo4j Connection Configuration ---
NEO4J_HOST = os.getenv("NEO4J_HOST", "localhost")
NEO4J_PORT = int(os.getenv("NEO4J_PORT", "7687"))
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j_test")

@pytest.fixture
def neo4j_store():
    """A pytest fixture to create a Neo4jStore instance and clean up the database after the test."""
    config = GraphStoreConfig(
        name=NEO4J_DATABASE,
        host=NEO4J_HOST,
        port=NEO4J_PORT,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
    )
    store = Neo4jStore(config)
    yield store
    store.conn.run("MATCH (n) DETACH DELETE n")
    store.close()

def test_insert_and_get_graph(neo4j_store):
    """Test if graph data can be successfully inserted and retrieved."""
    # Create a simple graph
    graph = MemoryGraph()
    graph.upsert_vertex(Vertex("A", {"name": "Alice"}))
    graph.upsert_vertex(Vertex("B", {"name": "Bob"}))
    graph.append_edge(Edge("A", "B", "FRIENDS", {"since": "2023"}))

    # Insert graph data
    neo4j_store.insert_graph(graph)

    # Retrieve graph data
    retrieved_graph = neo4j_store.get_graph("A")
    assert retrieved_graph.vertex_count == 2
    assert retrieved_graph.edge_count == 1
    assert retrieved_graph.get_vertex("A").props["name"] == "Alice"
    assert retrieved_graph.get_edge("A", "B", "FRIENDS").props["since"] == "2023"

def test_delete_graph(neo4j_store):
    """Test if graph data can be successfully deleted."""
    # Insert some data
    neo4j_store.conn.run("CREATE (:TestNode {id: 'node1'})-[:TEST_REL]->(:TestNode {id: 'node2'})")
    # Delete graph data
    neo4j_store.delete_graph("node1")
    # Check if the data has been deleted
    result = neo4j_store.conn.run("MATCH (n:TestNode) RETURN count(n) AS count")
    assert result[0]["count"] == 0
