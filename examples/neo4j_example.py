import asyncio
from typing import List

from dbgpt.storage.graph_store.graph import Edge, Graph, Vertex
from dbgpt_ext.storage.graph_store.neo4j_store import Neo4jStore


async def main():
    # Create a Neo4jStore instance
    neo4j_store = Neo4jStore()

    # Create a graph
    graph = Graph("test_graph")
    v1 = Vertex("1", "node1")
    v2 = Vertex("2", "node2")
    graph.add_vertex(v1)
    graph.add_vertex(v2)
    edge = Edge("1", "2", "edge1")
    graph.add_edge(edge)

    # Add the graph to the store
    await neo4j_store.add_graph(graph)

    # Get the graph from the store
    retrieved_graph = await neo4j_store.get_graph("test_graph")
    print(retrieved_graph)

    # Get all graph names
    graph_names = await neo4j_store.get_all_graph_names()
    print(graph_names)

    # Delete the graph from the store
    await neo4j_store.delete_graph("test_graph")


if __name__ == "__main__":
    asyncio.run(main())
