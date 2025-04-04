"""
Migration script to add missing columns to the tax_code table.
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Float, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """
    Add missing columns to the tax_code table if they don't exist:
    - total_levy_amount
    - effective_tax_rate
    """
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False

        # Connect to the database
        engine = create_engine(database_url)
        conn = engine.connect()
        
        # Create a metadata object
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        # Check if table exists
        if 'tax_code' not in metadata.tables:
            logger.error("tax_code table does not exist")
            return False
            
        # Get tax_code table
        tax_code = metadata.tables['tax_code']
        
        # Check if total_levy_amount column already exists
        if 'total_levy_amount' not in tax_code.columns:
            logger.info("Adding total_levy_amount column to tax_code table")
            conn.execute(text("ALTER TABLE tax_code ADD COLUMN total_levy_amount FLOAT DEFAULT 0.0"))
        else:
            logger.info("total_levy_amount column already exists")
            
        # Check if effective_tax_rate column already exists
        if 'effective_tax_rate' not in tax_code.columns:
            logger.info("Adding effective_tax_rate column to tax_code table")
            conn.execute(text("ALTER TABLE tax_code ADD COLUMN effective_tax_rate FLOAT DEFAULT 0.0"))
        else:
            logger.info("effective_tax_rate column already exists")
            
        # Check if created_by_id column already exists
        if 'created_by_id' not in tax_code.columns:
            logger.info("Adding created_by_id column to tax_code table")
            conn.execute(text("ALTER TABLE tax_code ADD COLUMN created_by_id INTEGER"))
        else:
            logger.info("created_by_id column already exists")
            
        # Check if updated_by_id column already exists
        if 'updated_by_id' not in tax_code.columns:
            logger.info("Adding updated_by_id column to tax_code table")
            conn.execute(text("ALTER TABLE tax_code ADD COLUMN updated_by_id INTEGER"))
        else:
            logger.info("updated_by_id column already exists")

        # Commit transaction
        conn.commit()
        
        logger.info("Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in migration: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)