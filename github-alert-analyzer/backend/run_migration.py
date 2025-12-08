#!/usr/bin/env python3
"""
Migration script to add manifest_path column to alerts table.
Run this script from the backend directory.
"""
import sys
from pathlib import Path

# Add the parent directory to the path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text


def run_migration():
    """Run the migration to add manifest_path column."""
    print("Starting migration: Add manifest_path column to alerts table")
    
    migration_sql = """
    -- Add manifest_path column
    ALTER TABLE alerts ADD COLUMN IF NOT EXISTS manifest_path VARCHAR(500);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(migration_sql))
            conn.commit()
            print("✅ Successfully added manifest_path column to alerts table")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
