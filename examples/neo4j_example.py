#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from dbgpt_ext.datasource.conn_neo4j import PNeo4jConnector

# This is a placeholder for a real Neo4j instance.
# For testing purposes, you can use a local Neo4j instance or a free cloud instance.
# The following command can be used to run a Neo4j container for testing:
# docker run -d --name neo4j-example -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:4.4
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


def main():
    """Main function to demonstrate the Neo4j connector."""
    try:
        # Create a Neo4j connector
        connector = PNeo4jConnector(
            uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD
        )

        # Connect to the database
        connector.connect()

        # Run a query
        result = connector.run("MATCH (n) RETURN n LIMIT 5")

        # Print the result
        print("Query result:", result)

        # Get table names
        table_names = connector.get_table_names()
        print("Table names:", table_names)

        # Get table info
        if table_names:
            table_info = connector.get_table_info(table_names[0])
            print(f"Table info for '{table_names[0]}':", table_info)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        if "connector" in locals() and connector:
            connector.close()


if __name__ == "__main__":
    main()
