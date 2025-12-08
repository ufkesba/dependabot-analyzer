"""Add final_summary column to analysis_workflows table."""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

engine = create_engine(DATABASE_URL)

def run_migration():
    """Add final_summary column to analysis_workflows table."""
    with engine.connect() as conn:
        # Add final_summary column
        conn.execute(text("""
            ALTER TABLE analysis_workflows 
            ADD COLUMN IF NOT EXISTS final_summary TEXT;
        """))
        conn.commit()
        print("✅ Migration completed: Added final_summary column to analysis_workflows")

if __name__ == "__main__":
    run_migration()
