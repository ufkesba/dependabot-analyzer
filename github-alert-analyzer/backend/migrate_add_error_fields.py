"""Migration to add error tracking fields to analysis_workflows table."""
from app.core.database import engine
from sqlalchemy import text

def run_migration():
    """Add error_message and error_details columns to analysis_workflows."""
    with engine.connect() as conn:
        try:
            # Add error_message column
            conn.execute(text(
                "ALTER TABLE analysis_workflows ADD COLUMN IF NOT EXISTS error_message VARCHAR(500)"
            ))
            print("✅ Added error_message column")
            
            # Add error_details column
            conn.execute(text(
                "ALTER TABLE analysis_workflows ADD COLUMN IF NOT EXISTS error_details TEXT"
            ))
            print("✅ Added error_details column")
            
            conn.commit()
            print("✅ Migration completed successfully")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
