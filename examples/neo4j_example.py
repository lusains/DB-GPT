
import os
from dbgpt_ext.datasource.conn_neo4j import Neo4jConnector

# --- Neo4j Connection Configuration ---
# It is recommended to use environment variables to store sensitive information
NEO4J_HOST = os.getenv("NEO4J_HOST", "localhost")
NEO4J_PORT = int(os.getenv("NEO4J_PORT", "7687"))
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def main():
    """
    A simple example demonstrating how to use Neo4jConnector to connect to Neo4j,
    create a simple graph, and perform some basic queries.
    """
    print("--- Connecting to Neo4j... ---")
    try:
        connector = Neo4jConnector.from_uri_db(
            host=NEO4J_HOST,
            port=NEO4J_PORT,
            user=NEO4J_USER,
            pwd=NEO4J_PASSWORD,
            db_name=NEO4J_DATABASE,
        )
        print("--- Connection successful! ---")

        # --- Clean up the database ---
        print("\n--- Cleaning up the database... ---")
        connector.run("MATCH (n) DETACH DELETE n")
        print("--- Database cleaned up! ---")

        # --- Create nodes and relationships ---
        print("\n--- Creating nodes and relationships... ---")
        create_query = """
        CREATE (p1:Person {name: 'Alice', age: 30}),
               (p2:Person {name: 'Bob', age: 35}),
               (c1:City {name: 'New York'}),
               (p1)-[:LIVES_IN]->(c1),
               (p2)-[:LIVES_IN]->(c1)
        """
        connector.run(create_query)
        print("--- Nodes and relationships created successfully! ---")

        # --- Query data ---
        print("\n--- Querying for all people living in New York... ---")
        query = """
        MATCH (p:Person)-[:LIVES_IN]->(c:City {name: 'New York'})
        RETURN p.name AS name, p.age AS age
        """
        results = connector.run(query)
        for record in results:
            print(f"  - Name: {record['name']}, Age: {record['age']}")

    except Exception as e:
        print(f"  - An error occurred: {e}")
        print("  - Please make sure Neo4j is running and the connection information is correct.")

    finally:
        if 'connector' in locals() and connector:
            connector.close()
            print("\n--- Connection closed. ---")

if __name__ == "__main__":
    main()
