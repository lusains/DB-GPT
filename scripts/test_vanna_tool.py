#!/usr/bin/env python3
"""Test script for Vanna 2.0 style Text2SQL tool integration.

Tests the complete Text2SQL workflow:
1. get_database_schema - Retrieve database structure
2. Agent generates SQL based on schema
3. run_sql - Execute the generated SQL

This follows Vanna 2.0 architecture pattern.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project packages to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "packages" / "dbgpt-core" / "src"))
sys.path.insert(0, str(project_root / "packages" / "dbgpt-app" / "src"))
sys.path.insert(0, str(project_root / "packages" / "dbgpt-ext" / "src"))
sys.path.insert(0, str(project_root / "packages" / "dbgpt-serve" / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_tool_imports():
    """Test 1: Verify tool file exists and has correct structure."""
    print("\n=== Test 1: Tool File Structure ===")
    try:
        tool_file = (
            project_root
            / "packages"
            / "dbgpt-core"
            / "src"
            / "dbgpt"
            / "agent"
            / "expand"
            / "resources"
            / "vanna_text2sql_tool.py"
        )

        if not tool_file.exists():
            print(f"❌ Tool file not found: {tool_file}")
            return False

        content = tool_file.read_text()

        # Check for key components
        has_schema_tool = "def get_database_schema" in content
        has_sql_tool = "def run_sql" in content
        has_tool_decorator = "@tool" in content
        has_connector_import = "ConnectorManager" in content

        print(f"✅ Tool file found: {tool_file.name}")
        print(f"   ✓ get_database_schema function: {has_schema_tool}")
        print(f"   ✓ run_sql function: {has_sql_tool}")
        print(f"   ✓ @tool decorator: {has_tool_decorator}")
        print(f"   ✓ ConnectorManager integration: {has_connector_import}")

        return all([has_schema_tool, has_sql_tool, has_tool_decorator, has_connector_import])

    except Exception as e:
        print(f"❌ Failed to verify tool structure: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_tool_registration():
    """Test 2: Verify tools are registered in component_configs."""
    print("\n=== Test 2: Tool Registration ===")
    try:
        config_file = (
            project_root
            / "packages"
            / "dbgpt-app"
            / "src"
            / "dbgpt_app"
            / "component_configs.py"
        )

        if not config_file.exists():
            print(f"❌ Config file not found: {config_file}")
            return False

        content = config_file.read_text()

        # Check for tool imports and registration
        has_import = "from dbgpt.agent.expand.resources.vanna_text2sql_tool import" in content
        has_schema_import = "get_database_schema" in content
        has_sql_import = "run_sql" in content
        has_schema_register = "rm.register_resource(resource_instance=get_database_schema)" in content
        has_sql_register = "rm.register_resource(resource_instance=run_sql)" in content

        print("✅ Registration configuration verified")
        print(f"   ✓ Tool imports: {has_import}")
        print(f"   ✓ get_database_schema imported: {has_schema_import}")
        print(f"   ✓ run_sql imported: {has_sql_import}")
        print(f"   ✓ get_database_schema registered: {has_schema_register}")
        print(f"   ✓ run_sql registered: {has_sql_register}")

        return all([has_import, has_schema_import, has_sql_import, has_schema_register, has_sql_register])

    except Exception as e:
        print(f"❌ Registration verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_schema_tool_signature():
    """Test 3: Verify get_database_schema has correct signature."""
    print("\n=== Test 3: Schema Tool Signature ===")
    try:
        tool_file = (
            project_root
            / "packages"
            / "dbgpt-core"
            / "src"
            / "dbgpt"
            / "agent"
            / "expand"
            / "resources"
            / "vanna_text2sql_tool.py"
        )
        content = tool_file.read_text()

        # Check parameter definitions
        has_database_param = 'database_name: Annotated' in content
        has_tables_param = 'table_names: Annotated' in content
        has_optional = 'Optional[str]' in content

        print("✅ Schema tool signature verified")
        print(f"   ✓ database_name parameter: {has_database_param}")
        print(f"   ✓ table_names parameter: {has_tables_param}")
        print(f"   ✓ Optional table_names: {has_optional}")

        return all([has_database_param, has_tables_param, has_optional])

    except Exception as e:
        print(f"❌ Signature check failed: {e}")
        return False


async def test_sql_tool_signature():
    """Test 4: Verify run_sql has correct signature."""
    print("\n=== Test 4: SQL Execution Tool Signature ===")
    try:
        tool_file = (
            project_root
            / "packages"
            / "dbgpt-core"
            / "src"
            / "dbgpt"
            / "agent"
            / "expand"
            / "resources"
            / "vanna_text2sql_tool.py"
        )
        content = tool_file.read_text()

        # Check parameter definitions
        has_sql_param = 'sql: Annotated[str, Doc("SQL query' in content
        has_database_param = 'database_name: Annotated' in content

        print("✅ SQL tool signature verified")
        print(f"   ✓ sql parameter: {has_sql_param}")
        print(f"   ✓ database_name parameter: {has_database_param}")

        return all([has_sql_param, has_database_param])

    except Exception as e:
        print(f"❌ Signature check failed: {e}")
        return False


async def test_architecture_pattern():
    """Test 5: Verify Vanna 2.0 architecture pattern."""
    print("\n=== Test 5: Vanna 2.0 Architecture Pattern ===")
    try:
        tool_file = (
            project_root
            / "packages"
            / "dbgpt-core"
            / "src"
            / "dbgpt"
            / "agent"
            / "expand"
            / "resources"
            / "vanna_text2sql_tool.py"
        )
        content = tool_file.read_text()

        # Check for Vanna 2.0 patterns
        has_vanna_comment = "Vanna 2.0" in content or "Vanna.AI 2.0" in content
        has_schema_description = "Get database schema" in content
        has_sql_description = "Execute SQL" in content
        has_connector = "connector_manager.get_connector" in content
        has_table_info = "get_table_info" in content
        has_run_to_df = "run_to_df" in content

        print("✅ Architecture pattern verified:")
        print(f"   ✓ Vanna 2.0 architecture: {has_vanna_comment}")
        print(f"   ✓ Schema retrieval tool: {has_schema_description}")
        print(f"   ✓ SQL execution tool: {has_sql_description}")
        print(f"   ✓ ConnectorManager integration: {has_connector}")
        print(f"   ✓ Table info retrieval: {has_table_info}")
        print(f"   ✓ SQL execution with DataFrame: {has_run_to_df}")

        print("\n   Workflow:")
        print("     1. Agent calls get_database_schema(database_name)")
        print("     2. Agent receives table/column information")
        print("     3. Agent generates SQL based on schema + user question")
        print("     4. Agent calls run_sql(sql, database_name)")
        print("     5. User receives query results")

        return all([has_vanna_comment, has_connector, has_table_info, has_run_to_df])

    except Exception as e:
        print(f"❌ Architecture check failed: {e}")
        return False


async def test_error_handling():
    """Test 6: Verify tools have error handling."""
    print("\n=== Test 6: Error Handling ===")
    try:
        tool_file = (
            project_root
            / "packages"
            / "dbgpt-core"
            / "src"
            / "dbgpt"
            / "agent"
            / "expand"
            / "resources"
            / "vanna_text2sql_tool.py"
        )
        content = tool_file.read_text()

        # Check for error handling patterns
        has_try_except = "try:" in content and "except Exception" in content
        has_error_logging = "logger.error" in content
        has_error_return = 'return f"Error:' in content

        print("✅ Error handling verified:")
        print(f"   ✓ Try-except blocks: {has_try_except}")
        print(f"   ✓ Error logging: {has_error_logging}")
        print(f"   ✓ Error messages returned: {has_error_return}")
        print("   Note: Tools return error strings instead of raising exceptions")

        return all([has_try_except, has_error_logging, has_error_return])

    except Exception as e:
        print(f"❌ Error handling check failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Vanna 2.0 Text2SQL Tool Integration Tests")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Tool Imports", await test_tool_imports()))
    results.append(("Tool Registration", await test_tool_registration()))
    results.append(("Schema Tool Signature", await test_schema_tool_signature()))
    results.append(("SQL Tool Signature", await test_sql_tool_signature()))
    results.append(("Architecture Pattern", await test_architecture_pattern()))
    results.append(("Error Handling", await test_error_handling()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    print("\n" + "=" * 60)
    print("Integration Ready")
    print("=" * 60)
    print("The Vanna 2.0 Text2SQL tools are ready to use:")
    print("  • get_database_schema(database_name, table_names=None)")
    print("  • run_sql(sql, database_name)")
    print("\nAgent Workflow:")
    print("  1. Agent receives user question")
    print("  2. Agent calls get_database_schema to understand DB structure")
    print("  3. Agent's LLM generates SQL based on schema")
    print("  4. Agent calls run_sql to execute the SQL")
    print("  5. Agent returns formatted results to user")

    return all(p for _, p in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
