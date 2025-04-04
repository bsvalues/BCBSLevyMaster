"""
Migration script to add missing columns to the tax_district table.

This script adds tax_district_id, levy_code, and linked_levy_code columns
to the tax_district table to match the model definition using direct SQL execution.
"""
import os
import logging
import psycopg2
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database connection string from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

def run_migration():
    """
    Add tax_district_id, levy_code, and linked_levy_code columns to the tax_district table.
    """
    try:
        if not DATABASE_URL:
            logger.error("DATABASE_URL environment variable not set")
            return False

        logger.info("Starting migration to add columns to tax_district table")
        
        # Parse the DATABASE_URL to extract connection parameters
        parsed_url = urlparse(DATABASE_URL)
        db_params = {
            'dbname': parsed_url.path[1:],
            'user': parsed_url.username,
            'password': parsed_url.password,
            'host': parsed_url.hostname,
            'port': parsed_url.port
        }
        
        # Connect to the database directly with psycopg2
        conn = psycopg2.connect(**db_params)
        conn.autocommit = False  # Start transaction
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tax_district' 
            AND column_name IN ('tax_district_id', 'levy_code', 'linked_levy_code');
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Define columns to add
        columns_to_add = []
        if 'tax_district_id' not in existing_columns:
            columns_to_add.append(('tax_district_id', 'INTEGER'))
        if 'levy_code' not in existing_columns:
            columns_to_add.append(('levy_code', 'VARCHAR(16)'))
        if 'linked_levy_code' not in existing_columns:
            columns_to_add.append(('linked_levy_code', 'VARCHAR(16)'))
        
        # Add missing columns
        for column_name, column_type in columns_to_add:
            logger.info(f"Adding column {column_name} to tax_district table")
            sql = f"ALTER TABLE tax_district ADD COLUMN {column_name} {column_type};"
            cursor.execute(sql)
        
        # Commit the transaction
        conn.commit()
        logger.info(f"Added {len(columns_to_add)} columns to tax_district table")
        
        # Close the connection
        cursor.close()
        conn.close()
        
        return True
            
    except Exception as e:
        logger.error(f"Error in migration: {str(e)}")
        # If there was an error, attempt to rollback
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    success = run_migration()
    exit_code = 0 if success else 1
    exit(exit_code)