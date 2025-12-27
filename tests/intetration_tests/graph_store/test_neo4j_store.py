import pytest
from dbgpt_ext.storage.graph_store.neo4j_store import Neo4jStore

@pytest.fixture
def neo4j_store():
    # Setup Neo4jStore for testing
    # Make sure you have a Neo4j instance running
    store = Neo4jStore()
    yield store
    # Teardown: Clean up the graph after tests
    store.delete_graph("test_graph")

from dbgpt.storage.graph_store.graph import Graph, Vertex, Edge

def test_graph_operations(neo4j_store):
    # Test adding and retrieving a graph
    graph = Graph("test_graph")
    v1 = Vertex("1", "node1")
    v2 = Vertex("2", "node2")
    graph.add_vertex(v1)
    graph.add_vertex(v2)
    edge = Edge("1", "2", "edge1")
    graph.add_edge(edge)

    assert neo4j_store.get_graph("test_graph") is None
    neo4j_store.add_graph(graph)
    retrieved_graph = neo4j_store.get_graph("test_graph")
    assert retrieved_graph is not None
    assert retrieved_graph.vertex_count == 2
    assert retrieved_graph.edge_count == 1

def test_vertex_operations(neo4j_store):
    # Test adding and retrieving vertices
    graph = Graph("test_graph")
    v1 = Vertex("test_vertex", "test_name")
    graph.add_vertex(v1)
    neo4j_store.add_graph(graph)

    vertex = neo4j_store.get_vertex("test_graph", "test_vertex")
    assert vertex is not None
    assert vertex.name == "test_name"

def test_edge_operations(neo4j_store):
    # Test adding and retrieving edges
    graph = Graph("test_graph")
    v1 = Vertex("test_vertex1")
    v2 = Vertex("test_vertex2")
    graph.add_vertex(v1)
    graph.add_vertex(v2)
    edge = Edge("test_vertex1", "test_vertex2", "test_edge", relation="test_relation")
    graph.add_edge(edge)
    neo4j_store.add_graph(graph)

    retrieved_edge = neo4j_store.get_edge("test_graph", "test_edge")
    assert retrieved_edge is not None
    assert retrieved_edge.get_prop("relation") == "test_relation"
