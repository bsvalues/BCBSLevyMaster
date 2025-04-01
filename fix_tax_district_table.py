"""
Migration script to fix the tax_district table structure.
"""
import os
import sys
import logging
from datetime import datetime

from sqlalchemy import (
    text, Table, Column, Integer, String, Float, Boolean, Text, 
    DateTime, MetaData, ForeignKey, UniqueConstraint, create_engine, inspect
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    sys.exit(1)

def run_migration():
    """
    Fix the tax_district table to match the model schema.
    """
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create metadata
        metadata = MetaData()
        
        # Define the intermediate table structure
        temp_table = Table(
            'tax_district_temp', metadata,
            Column('id', Integer, primary_key=True),
            Column('year', Integer, nullable=False, index=True),
            Column('district_name', String(128), nullable=False),
            Column('district_code', String(16), nullable=True),  # Make nullable for migration
            Column('district_type', String(64), nullable=True),
            Column('county', String(64), nullable=True),
            Column('state', String(2), nullable=True),
            Column('description', Text, nullable=True),
            Column('is_active', Boolean, default=True),
            Column('contact_name', String(128), nullable=True),
            Column('contact_email', String(128), nullable=True),
            Column('contact_phone', String(20), nullable=True),
            Column('statutory_limit', Float, nullable=True),
            Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
            Column('updated_at', DateTime, default=datetime.utcnow, nullable=False),
            Column('created_by_id', Integer, nullable=True),
            Column('updated_by_id', Integer, nullable=True),
        )
        
        with engine.begin() as conn:
            # Check if the tax_district table already has the correct structure
            inspector = inspect(engine)
            if 'tax_district' in inspector.get_table_names():
                columns = {col['name']: col for col in inspector.get_columns('tax_district')}
                if 'district_code' in columns and 'district_name' in columns:
                    logger.info("tax_district table already has the correct structure")
                    return
                    
            # Create the intermediate table
            temp_table.create(conn, checkfirst=True)
            logger.info("Created temporary table tax_district_temp")
            
            # First check for duplicate district_code/year combinations
            check_duplicates_query = text("""
                SELECT district_code, year, COUNT(*) 
                FROM (
                    SELECT 
                        COALESCE(levy_code, tax_district_id) as district_code, 
                        year
                    FROM tax_district
                ) t
                GROUP BY district_code, year
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC;
            """)
            
            results = conn.execute(check_duplicates_query).fetchall()
            
            if results:
                logger.info(f"Found {len(results)} duplicate district_code/year combinations")
                
                # Update district_codes for duplicates by appending the row ID
                for district_code, year, count in results:
                    logger.info(f"Fixing {count} duplicates for {district_code}/{year}")
                    
                    fix_duplicates_query = text(f"""
                        WITH duplicates AS (
                            SELECT id, ROW_NUMBER() OVER (ORDER BY id) as row_num
                            FROM tax_district
                            WHERE (COALESCE(levy_code, tax_district_id) = :district_code) AND (year = :year)
                            ORDER BY id
                        )
                        UPDATE tax_district
                        SET levy_code = CASE 
                                WHEN d.row_num > 1 THEN :district_code || '_' || d.row_num
                                ELSE levy_code
                              END
                        FROM duplicates d
                        WHERE tax_district.id = d.id;
                    """)
                    
                    conn.execute(fix_duplicates_query, {"district_code": district_code, "year": year})
                
                logger.info("Fixed duplicate district_code/year combinations")
            
            # Copy data from the original table with fixed district codes
            copy_data_query = text("""
                INSERT INTO tax_district_temp (
                    id, year, district_name, district_code, statutory_limit, 
                    created_at, updated_at
                )
                SELECT 
                    id, year, district_name, 
                    COALESCE(levy_code, tax_district_id) as district_code, 
                    statutory_limit, created_at, updated_at
                FROM tax_district;
            """)
            
            conn.execute(copy_data_query)
            logger.info("Copied data to temporary table")
            
            # Rename tables
            conn.execute(text("ALTER TABLE tax_district RENAME TO tax_district_old;"))
            conn.execute(text("ALTER TABLE tax_district_temp RENAME TO tax_district;"))
            logger.info("Renamed tables")
            
            # Add indexes
            conn.execute(text("CREATE INDEX idx_tax_district_year ON tax_district(year);"))
            logger.info("Added indexes")
            
            # Make district_code not nullable after data is migrated
            conn.execute(text("ALTER TABLE tax_district ALTER COLUMN district_code SET NOT NULL;"))
            logger.info("Made district_code not nullable")
            
            # Create unique constraint - now should work with duplicates fixed
            conn.execute(text("""
                ALTER TABLE tax_district 
                ADD CONSTRAINT uix_district_code_year 
                UNIQUE (district_code, year);
            """))
            logger.info("Added unique constraint")
            
        logger.info("Migration completed successfully")
    except SQLAlchemyError as e:
        logger.error(f"Database error during migration: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()