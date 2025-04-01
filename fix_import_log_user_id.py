"""
Migration script to fix the ImportLog model by making user_id nullable.
"""

import logging
from datetime import datetime
import os

from sqlalchemy import Column, Integer, MetaData, Table, ForeignKey
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migration():
    """
    Make the user_id column in import_log table nullable.
    If it doesn't exist, create it as nullable.
    """
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False

        # Create engine
        engine = create_engine(database_url)
        
        # First check if the import_log table exists
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'import_log')"
            ))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("Table 'import_log' does not exist, nothing to migrate")
                return True
            
            # Check if user_id column exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'import_log' AND column_name = 'user_id')"
            ))
            column_exists = result.scalar()
            
            if column_exists:
                # Try to alter column to make it nullable
                logger.info("Altering 'user_id' column to make it nullable")
                conn.execute(text(
                    "ALTER TABLE import_log ALTER COLUMN user_id DROP NOT NULL"
                ))
                conn.commit()
            else:
                # Add the column as nullable
                logger.info("Adding 'user_id' column as nullable")
                conn.execute(text(
                    "ALTER TABLE import_log ADD COLUMN user_id INTEGER"
                ))
                conn.commit()
                
                # Try to add foreign key if user table exists
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user')"
                ))
                user_table_exists = result.scalar()
                
                if user_table_exists:
                    logger.info("Adding foreign key constraint to user table")
                    conn.execute(text(
                        "ALTER TABLE import_log ADD CONSTRAINT fk_import_log_user FOREIGN KEY (user_id) REFERENCES \"user\" (id)"
                    ))
                    conn.commit()
            
            logger.info("Migration completed successfully")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Database error during migration: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {str(e)}")
        return False


if __name__ == "__main__":
    run_migration()