"""
This is an example of how to use the Neo4jConnector.

To run this example, you need to have a Neo4j instance running.
You can use Docker to start a Neo4j instance:
docker run -d \
    --name neo4j-example \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:4.4
"""

import os
from dbgpt_ext.datasource.conn_neo4j import Neo4jConnector

def main():
    """Main function for the Neo4j example."""
    # --- Connection Parameters ---
    # Replace with your Neo4j instance details
    # You can also use environment variables for sensitive data
    host = os.getenv("NEO4J_HOST", "localhost")
    port = int(os.getenv("NEO4J_PORT", 7687))
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    print(f"Connecting to Neo4j at {host}:{port}...")

    try:
        # --- 1. Create a connector ---
        connector = Neo4jConnector.from_uri_db(host, port, user, password, database)
        print("Successfully connected to Neo4j.")

        # --- 2. Clean up previous data ---
        print("\nCleaning up previous data...")
        connector.run("MATCH (n) DETACH DELETE n")
        print("Previous data cleaned up.")

        # --- 3. Add data ---
        print("\nAdding data (nodes and relationships)...")
        # Create nodes
        connector.run("CREATE (:Person {name: 'Alice', age: 30})")
        connector.run("CREATE (:Person {name: 'Bob', age: 35})")
        connector.run("CREATE (:City {name: 'New York'})")
        print("- Nodes created: 2 Persons, 1 City")

        # Create relationships
        connector.run(
            "MATCH (p1:Person {name: 'Alice'}), (p2:Person {name: 'Bob'}) "
            "CREATE (p1)-[:FRIENDS_WITH]->(p2)"
        )
        connector.run(
            "MATCH (p:Person {name: 'Alice'}), (c:City {name: 'New York'}) "
            "CREATE (p)-[:LIVES_IN]->(c)"
        )
        print("- Relationships created: 1 FRIENDS_WITH, 1 LIVES_IN")

        # --- 4. Query data ---
        print("\nQuerying data...")
        print("\n--- Friends ---")
        friends_result = connector.run(
            "MATCH (p:Person)-[:FRIENDS_WITH]->(friend) RETURN p.name, friend.name"
        )
        for record in friends_result:
            print(f"{record['p.name']} is friends with {record['friend.name']}")

        print("\n--- Location ---")
        location_result = connector.run(
            "MATCH (p:Person)-[:LIVES_IN]->(c:City) RETURN p.name, c.name"
        )
        for record in location_result:
            print(f"{record['p.name']} lives in {record['c.name']}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print(
            "\nPlease ensure your Neo4j instance is running and the connection "
            "details are correct."
        )
    finally:
        # --- 5. Close the connection ---
        if 'connector' in locals() and connector:
            connector.close()
            print("\nConnection closed.")

if __name__ == "__main__":
    main()
