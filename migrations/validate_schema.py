#!/usr/bin/env python3
"""
Schema Validation Script

This script validates the time-series schema SQL syntax and structure
without requiring a full database setup.
"""

import re
import sys
from pathlib import Path

def validate_sql_syntax(sql_content: str) -> bool:
    """
    Basic SQL syntax validation for the schema.
    
    Args:
        sql_content: SQL content to validate
        
    Returns:
        bool: True if syntax appears valid, False otherwise
    """
    errors = []
    
    # Check for balanced parentheses
    paren_count = sql_content.count('(') - sql_content.count(')')
    if paren_count != 0:
        errors.append(f"Unbalanced parentheses: {paren_count} extra opening" if paren_count > 0 else f"{abs(paren_count)} extra closing")
    
    # Check for required table creation statements
    required_tables = ['miner_metrics', 'miner_status']
    for table in required_tables:
        if f"CREATE TABLE IF NOT EXISTS {table}" not in sql_content:
            errors.append(f"Missing CREATE TABLE statement for {table}")
    
    # Check for required indexes
    required_indexes = [
        'idx_miner_metrics_miner_time',
        'idx_miner_metrics_type_time',
        'idx_miner_status_miner_time'
    ]
    for index in required_indexes:
        if f"CREATE INDEX IF NOT EXISTS {index}" not in sql_content:
            errors.append(f"Missing CREATE INDEX statement for {index}")
    
    # Check for foreign key constraints
    if "FOREIGN KEY" not in sql_content:
        errors.append("Missing FOREIGN KEY constraints")
    
    # Check for proper column definitions
    required_columns = {
        'miner_metrics': ['id', 'miner_id', 'timestamp', 'metric_type', 'value', 'unit'],
        'miner_status': ['id', 'miner_id', 'timestamp', 'status_data']
    }
    
    for table, columns in required_columns.items():
        for column in columns:
            # Simple check - look for column name in table definition
            table_pattern = rf"CREATE TABLE IF NOT EXISTS {table}\s*\((.*?)\);"
            match = re.search(table_pattern, sql_content, re.DOTALL | re.IGNORECASE)
            if match:
                table_def = match.group(1)
                if column not in table_def:
                    errors.append(f"Missing column {column} in table {table}")
    
    if errors:
        print("SQL Validation Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("SQL syntax validation passed!")
    return True


def validate_migration_script(script_path: Path) -> bool:
    """
    Validate the migration script structure.
    
    Args:
        script_path: Path to the migration script
        
    Returns:
        bool: True if script structure is valid, False otherwise
    """
    if not script_path.exists():
        print(f"Migration script not found: {script_path}")
        return False
    
    content = script_path.read_text()
    
    # Check for required functions
    required_functions = [
        'create_timeseries_tables',
        'create_timeseries_indexes',
        'verify_schema_creation',
        'main'
    ]
    
    errors = []
    for func in required_functions:
        if f"async def {func}" not in content and f"def {func}" not in content:
            errors.append(f"Missing function: {func}")
    
    # Check for proper imports
    required_imports = ['aiosqlite', 'logging', 'asyncio']
    for imp in required_imports:
        if f"import {imp}" not in content:
            errors.append(f"Missing import: {imp}")
    
    # Check for error handling
    if "try:" not in content or "except" not in content:
        errors.append("Missing error handling")
    
    if errors:
        print("Migration Script Validation Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("Migration script validation passed!")
    return True


def main():
    """
    Main validation function.
    """
    print("Validating Time-Series Schema...")
    
    # Validate SQL schema file
    schema_path = Path(__file__).parent / "timeseries_schema.sql"
    if schema_path.exists():
        sql_content = schema_path.read_text()
        sql_valid = validate_sql_syntax(sql_content)
    else:
        print(f"Schema file not found: {schema_path}")
        sql_valid = False
    
    # Validate migration script
    migration_path = Path(__file__).parent / "create_timeseries_schema.py"
    script_valid = validate_migration_script(migration_path)
    
    # Overall validation result
    if sql_valid and script_valid:
        print("\n✅ All validations passed! Schema is ready for deployment.")
        return True
    else:
        print("\n❌ Validation failed. Please fix the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)