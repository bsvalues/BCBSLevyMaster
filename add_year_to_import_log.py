"""
Migration script to add the year column to the ImportLog model.
"""

import logging
from datetime import datetime
import os
from urllib.parse import urlparse
import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get database connection string from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

def run_migration():
    """
    Add the year column to import_log table if it doesn't exist.
    """
    try:
        if not DATABASE_URL:
            logger.error("DATABASE_URL environment variable not set")
            return False

        logger.info("Starting migration to add year column to import_log table")
        
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
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'import_log' 
            AND column_name = 'year';
        """)
        exists = cursor.fetchone()
        
        if not exists:
            logger.info("Adding 'year' column to import_log table")
            cursor.execute("""
                ALTER TABLE import_log 
                ADD COLUMN year INTEGER;
            """)
            
            # Default to current year for existing records
            current_year = datetime.now().year
            cursor.execute(f"""
                UPDATE import_log
                SET year = {current_year}
                WHERE year IS NULL;
            """)
            
            # Make column not nullable after setting default values
            cursor.execute("""
                ALTER TABLE import_log 
                ALTER COLUMN year SET NOT NULL;
            """)
            
            # Add index on year column
            cursor.execute("""
                CREATE INDEX idx_import_log_year ON import_log (year);
            """)
            
            # Commit the transaction
            conn.commit()
            logger.info("Successfully added 'year' column to import_log table")
        else:
            logger.info("'year' column already exists in import_log table")
        
        # Add missing columns from ImportLog model if they don't exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'import_log';
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Define columns to add based on ImportLog model
        columns_to_add = []
        if 'record_count' not in existing_columns:
            columns_to_add.append(('record_count', 'INTEGER DEFAULT 0'))
        if 'success_count' not in existing_columns:
            columns_to_add.append(('success_count', 'INTEGER DEFAULT 0'))
        if 'error_count' not in existing_columns:
            columns_to_add.append(('error_count', 'INTEGER DEFAULT 0'))
        if 'error_details' not in existing_columns:
            columns_to_add.append(('error_details', 'TEXT'))
        if 'processing_time' not in existing_columns:
            columns_to_add.append(('processing_time', 'FLOAT'))
        if 'import_metadata' not in existing_columns:
            columns_to_add.append(('import_metadata', 'JSONB'))
        
        # Add missing columns
        for column_name, column_type in columns_to_add:
            logger.info(f"Adding column {column_name} to import_log table")
            sql = f"ALTER TABLE import_log ADD COLUMN {column_name} {column_type};"
            cursor.execute(sql)
        
        if columns_to_add:
            # Commit the transaction
            conn.commit()
            logger.info(f"Added {len(columns_to_add)} additional columns to import_log table")
        
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