from app import app, db
from sqlalchemy import text
import sys

def run_migration():
    """
    Add the import_type column to the import_log table.
    """
    try:
        with app.app_context():
            # Add the import_type column if it doesn't exist
            db.session.execute(text("""
                ALTER TABLE import_log 
                ADD COLUMN IF NOT EXISTS import_type VARCHAR(50) NULL
            """))
            db.session.commit()
            print("Migration successful: Added import_type column to import_log table")
            return True
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)