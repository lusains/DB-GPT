import pytest
from dbgpt.storage.graph_store.graph import MemoryGraph, Vertex, Edge, GraphElemType
from dbgpt_ext.storage.graph_store.neo4j_store import Neo4jStore, Neo4jStoreConfig
from dbgpt_ext.storage.knowledge_graph.community.neo4j_store_adapter import (
    Neo4jStoreAdapter,
)

# --- Test Connection Parameters ---
# Ensure these match your test Neo4j instance
HOST = "localhost"
PORT = 7687
USER = "neo4j"
PWD = "password"
DB_NAME = "test_graph_store"


@pytest.fixture(scope="module")
def store():
    """
    Pytest fixture to create a Neo4jStore instance for the module.
    It creates a new database for testing and cleans it up afterward.
    """
    try:
        # Connect to the system database to manage other databases
        config = Neo4jStoreConfig(
            host=HOST, port=PORT, user=USER, password=PWD, database="neo4j"
        )
        system_store = Neo4jStore(config=config)

        # Create a new database for testing
        system_store.conn.run(f"CREATE DATABASE {DB_NAME} IF NOT EXISTS")

        # Connect to the new test database
        test_config = Neo4jStoreConfig(
            host=HOST, port=PORT, user=USER, password=PWD, database=DB_NAME
        )
        test_store = Neo4jStore(config=test_config)

        yield test_store

        # --- Teardown: Clean up and drop the test database ---
        system_store.conn.run(f"DROP DATABASE {DB_NAME} IF EXISTS")
        system_store.conn.close()

    except Exception as e:
        pytest.fail(f"Failed to set up Neo4j test environment: {e}")


@pytest.fixture(scope="function")
def neo4j_adapter(store: Neo4jStore):
    """
    Pytest fixture to create a Neo4jStoreAdapter for each test function.
    This ensures each test runs in a clean state.
    """
    adapter = Neo4jStoreAdapter(store)
    adapter.truncate()  # Clear the graph before each test
    yield adapter
    adapter.truncate()  # Clean up after each test


def test_insert_and_get_triplets(neo4j_adapter: Neo4jStoreAdapter):
    """Test inserting and retrieving triplets."""
    neo4j_adapter.insert_triplet("Alice", "FRIENDS_WITH", "Bob")
    neo4j_adapter.insert_triplet("Alice", "LIVES_IN", "New York")
    neo4j_adapter.insert_triplet("Bob", "LIVES_IN", "New York")

    # Test getting triplets for a specific subject
    alice_triplets = neo4j_adapter.get_triplets("Alice")
    assert len(alice_triplets) == 2
    assert ("FRIENDS_WITH", "Bob") in alice_triplets
    assert ("LIVES_IN", "New York") in alice_triplets

    bob_triplets = neo4j_adapter.get_triplets("Bob")
    assert len(bob_triplets) == 1
    assert ("LIVES_IN", "New York") in bob_triplets


def test_query_and_graph_structure(neo4j_adapter: Neo4jStoreAdapter):
    """Test querying the graph and verifying its structure."""
    neo4j_adapter.insert_triplet("Charlie", "WORKS_AT", "DB-GPT")

    query = "MATCH (n)-[r]->(m) RETURN n, r, m"
    result_graph = neo4j_adapter.query(query)

    assert result_graph.vertex_count == 2
    assert result_graph.edge_count == 1

    # Check vertex and edge properties
    edge = list(result_graph.edges())[0]
    assert edge.name == "WORKS_AT"


def test_explore_graph(neo4j_adapter: Neo4jStoreAdapter):
    """Test graph exploration functionality."""
    # Create a small social network
    neo4j_adapter.insert_triplet("UserA", "FOLLOWS", "UserB")
    neo4j_adapter.insert_triplet("UserB", "FOLLOWS", "UserC")
    neo4j_adapter.insert_triplet("UserA", "POSTED", "Post1")

    # Explore from UserA with depth 1
    explore_result = neo4j_adapter.explore_trigraph(subs=["UserA"], depth=1, limit=5)

    # UserA, UserB, and Post1 should be present
    assert explore_result.vertex_count == 3
    # Two relationships: FOLLOWS and POSTED
    assert explore_result.edge_count == 2


def test_delete_triplet(neo4j_adapter: Neo4jStoreAdapter):
    """Test deleting a specific triplet."""
    neo4j_adapter.insert_triplet("Subject", "Predicate", "Object")

    # Ensure the triplet exists before deletion
    initial_triplets = neo4j_adapter.get_triplets("Subject")
    assert len(initial_triplets) == 1

    # Delete the triplet
    neo4j_adapter.delete_triplet("Subject", "Predicate", "Object")

    # Verify that the triplet is gone
    final_triplets = neo4j_adapter.get_triplets("Subject")
    assert len(final_triplets) == 0


def test_upsert_graph_and_verify(neo4j_adapter: Neo4jStoreAdapter):
    """Test upserting a complete graph and verifying its contents."""
    # Create a MemoryGraph object
    graph = MemoryGraph()
    v1 = Vertex("v1", props={"name": "Vertex 1", "vertex_type": GraphElemType.ENTITY.value})
    v2 = Vertex("v2", props={"name": "Vertex 2", "vertex_type": GraphElemType.ENTITY.value})
    e1 = Edge("v1", "v2", "CONNECTS", props={"edge_type": GraphElemType.RELATION.value})
    graph.upsert_vertex(v1)
    graph.upsert_vertex(v2)
    graph.append_edge(e1)

    # Upsert the graph into the adapter
    neo4j_adapter.upsert_graph(graph)

    # Verify the contents using a direct query
    result_graph = neo4j_adapter.query("MATCH (n)-[r]->(m) RETURN n, r, m")

    assert result_graph.vertex_count == 2
    assert result_graph.edge_count == 1

    retrieved_edge = list(result_graph.edges())[0]
    assert retrieved_edge.name == "CONNECTS"
