#!/usr/bin/env python3
"""Vanna Training Script.

This script trains the Vanna store with:
- DDL statements (from database or file)
- TTL ontology file
- Mapping JSON (generates SQL examples from schema mapping)
- Business documents

Usage:
    python scripts/vanna_training.py --db-name ontology --ttl assets/schema/1216.ttl
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/dbgpt-ext/src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/dbgpt-core/src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/dbgpt-serve/src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_ttl_file(ttl_path: str) -> str:
    """Load TTL ontology file content."""
    with open(ttl_path, "r", encoding="utf-8") as f:
        return f.read()


def load_mapping_json(mapping_path: str) -> list:
    """Load database-to-TTL mapping JSON."""
    with open(mapping_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_ddl_from_mapping(mapping: list, dialect: str = "mysql") -> list:
    """Generate DDL statements from mapping JSON.

    Args:
        mapping: List of table mappings
        dialect: SQL dialect (mysql, postgresql, etc.)

    Returns:
        List of DDL statements
    """
    ddl_statements = []

    for table in mapping:
        table_name = table["table_name"]
        columns = table.get("columns", [])

        # Build column definitions
        col_defs = []
        for col in columns:
            col_name = col["column_name"]
            prop_type = col.get("property_type", "DataProperty")

            # Infer SQL type from property type and naming conventions
            if col_name.endswith("_id"):
                sql_type = "VARCHAR(255)"
            elif col_name.endswith("_time") or col_name.endswith("_date"):
                sql_type = "DATE"
            elif col_name.endswith("_amount") or col_name.endswith("_cost") or col_name.endswith("_price"):
                sql_type = "DECIMAL(20, 4)"
            elif col_name.endswith("_hours"):
                sql_type = "DECIMAL(20, 4)"
            elif prop_type == "ObjectProperty":
                sql_type = "VARCHAR(255)"  # Foreign key reference
            else:
                sql_type = "TEXT"

            col_defs.append(f'    "{col_name}" {sql_type}')

        ddl = f'CREATE TABLE `{table_name}` (\n' + ",\n".join(col_defs) + "\n);"
        ddl_statements.append(ddl)

    return ddl_statements


def generate_documentation_from_ttl(ttl_content: str) -> list:
    """Extract documentation from TTL ontology.

    Parses rdfs:comment, ex:description, ex:rules annotations.

    Returns:
        List of documentation strings
    """
    docs = []

    # Simple regex-based extraction of comments and descriptions
    import re

    # Extract class comments
    class_pattern = r'ex:(\w+)\s+rdf:type\s+owl:Class[^.]*rdfs:comment\s+"([^"]+)"'
    for match in re.finditer(class_pattern, ttl_content, re.DOTALL):
        class_name, comment = match.groups()
        docs.append(f"类 {class_name}: {comment}")

    # Extract property descriptions
    prop_pattern = r'ex:(\w+)\s+rdf:type\s+owl:\w+Property[^.]*rdfs:comment\s+"([^"]+)"'
    for match in re.finditer(prop_pattern, ttl_content, re.DOTALL):
        prop_name, comment = match.groups()
        docs.append(f"属性 {prop_name}: {comment}")

    # Extract rules
    rules_pattern = r'ex:rules\s+"([^"]+)"'
    for match in re.finditer(rules_pattern, ttl_content):
        docs.append(f"规则: {match.group(1)}")

    return docs


def train_vanna(
    db_name: str,
    ttl_path: str = None,
    mapping_path: str = None,
    ddl_file: str = None,
    chroma_path: str = "./vanna_data",
):
    """Train Vanna store with schema and ontology data.

    Args:
        db_name: Target database name
        ttl_path: Path to TTL ontology file
        mapping_path: Path to mapping JSON file
        ddl_file: Path to DDL SQL file (optional, auto-generates from mapping if not provided)
        chroma_path: ChromaDB persistence path
    """
    from dbgpt_ext.vanna import VannaConfig, ChromaDBVannaStore

    # Initialize embedding function
    try:
        from dbgpt_serve.vanna.api.endpoints import get_embedding_fn
        embedding_fn = get_embedding_fn()
    except Exception as e:
        logger.warning(f"Failed to get embedding function from serve: {e}")
        # Fallback to simple embedder for testing
        class SimpleEmbedder:
            def embed_documents(self, texts):
                return [[0.1] * 384 for _ in texts]
            def embed_query(self, text):
                return [0.1] * 384
        embedding_fn = SimpleEmbedder()
        logger.info("Using simple embedder fallback")

    # Initialize store
    config = VannaConfig(chroma_path=chroma_path)
    store = ChromaDBVannaStore(config, embedding_fn)

    stats = {"ddl": 0, "ontology": 0, "documentation": 0}

    # 1. Train DDL
    if ddl_file and os.path.exists(ddl_file):
        logger.info(f"Loading DDL from file: {ddl_file}")
        with open(ddl_file, "r", encoding="utf-8") as f:
            ddl_content = f.read()
        # Split by semicolon for multiple statements
        for ddl in ddl_content.split(";"):
            ddl = ddl.strip()
            if ddl and ddl.upper().startswith("CREATE"):
                store.add_ddl(db_name, ddl + ";")
                stats["ddl"] += 1
    elif mapping_path and os.path.exists(mapping_path):
        logger.info(f"Generating DDL from mapping: {mapping_path}")
        mapping = load_mapping_json(mapping_path)
        ddl_statements = generate_ddl_from_mapping(mapping)
        for ddl in ddl_statements:
            store.add_ddl(db_name, ddl)
            stats["ddl"] += 1

    # 2. Train Ontology (TTL)
    if ttl_path and os.path.exists(ttl_path):
        logger.info(f"Loading ontology from: {ttl_path}")
        ttl_content = load_ttl_file(ttl_path)
        onto_id = store.add_ontology(
            db_name=db_name,
            content=ttl_content,
            format="ttl",
            description="Project cost ontology"
        )
        stats["ontology"] = 1
        logger.info(f"Added ontology: {onto_id}")

        # Extract documentation from TTL
        docs = generate_documentation_from_ttl(ttl_content)
        for doc in docs:
            store.add_documentation(db_name, doc)
            stats["documentation"] += 1

    # 3. Add table-column documentation from mapping
    if mapping_path and os.path.exists(mapping_path):
        mapping = load_mapping_json(mapping_path)
        for table in mapping:
            table_name = table["table_name"]
            mapped_class = table.get("mapped_class", "")

            # Create table documentation
            doc = f"表 {table_name} 映射到本体类 {mapped_class}\n"
            doc += "字段映射:\n"
            for col in table.get("columns", []):
                col_name = col["column_name"]
                mapped_prop = col.get("mapped_property", "")
                prop_type = col.get("property_type", "")
                doc += f"  - {col_name} -> {mapped_prop} ({prop_type})\n"

            store.add_documentation(db_name, doc)
            stats["documentation"] += 1

    logger.info(f"Training complete: {stats}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Train Vanna store with schema and ontology")
    parser.add_argument("--db-name", required=True, help="Target database name")
    parser.add_argument("--ttl", help="Path to TTL ontology file")
    parser.add_argument("--mapping", help="Path to mapping JSON file")
    parser.add_argument("--ddl", help="Path to DDL SQL file")
    parser.add_argument("--chroma-path", default="./vanna_data", help="ChromaDB path")

    args = parser.parse_args()

    # Default paths if not specified
    base_path = Path(__file__).parent.parent / "assets/schema"
    ttl_path = args.ttl or str(base_path / "1216.ttl")
    mapping_path = args.mapping or str(base_path / "db_to_ttl_mapping.json")

    stats = train_vanna(
        db_name=args.db_name,
        ttl_path=ttl_path,
        mapping_path=mapping_path,
        ddl_file=args.ddl,
        chroma_path=args.chroma_path,
    )

    print(f"\n✅ Training complete for database '{args.db_name}':")
    print(f"   - DDL statements: {stats['ddl']}")
    print(f"   - Ontology files: {stats['ontology']}")
    print(f"   - Documentation: {stats['documentation']}")


if __name__ == "__main__":
    main()
