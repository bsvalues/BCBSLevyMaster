#!/usr/bin/env python
"""
Direct District Insert Script

This script provides a direct way to insert tax districts into the database
using raw SQL queries. It bypasses the normal import process and directly
inserts records with specified values.
"""

import os
import sys
import logging
import argparse
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def insert_districts(district_ids, year=None):
    """
    Insert tax districts directly into the database.
    
    Args:
        district_ids: List of district IDs to insert
        year: Year to use for the districts (defaults to current year)
    """
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not found")
        return False
    
    # Use current year if not specified
    from datetime import datetime
    if not year:
        year = datetime.now().year
    
    # Connect to the database
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Create a new transaction for everything
            with conn.begin():
                # Get the current maximum ID
                result = conn.execute(text("SELECT MAX(id) FROM tax_district"))
                max_id = result.scalar() or 0
                logger.info(f"Current maximum tax district ID: {max_id}")
                
                # Filter out districts that already exist for this year
                existing_districts = []
                for district_id in district_ids:
                    result = conn.execute(
                        text("SELECT district_code FROM tax_district WHERE district_code = :code AND year = :year"),
                        {"code": district_id, "year": year}
                    )
                    if result.fetchone():
                        existing_districts.append(district_id)
                        logger.info(f"District {district_id} already exists for year {year}, skipping")
                
                # Only process districts that don't already exist
                new_districts = [d for d in district_ids if d not in existing_districts]
                
                if not new_districts:
                    logger.info("All districts already exist for the specified year")
                    return True
                
                # Insert each new district
                success_count = 0
                skipped_count = len(existing_districts)
                
                for i, district_id in enumerate(new_districts):
                    new_id = max_id + i + 1
                    try:
                        # Insert with explicit ID that is higher than the max
                        conn.execute(
                            text("""
                                INSERT INTO tax_district
                                (id, year, district_name, district_code, is_active,
                                created_at, updated_at, tax_district_id, levy_code)
                                VALUES
                                (:id, :year, :name, :code, TRUE, NOW(), NOW(), :district_id, :levy_cd)
                            """),
                            {
                                "id": new_id,
                                "year": year,
                                "name": f"District {district_id}",
                                "code": district_id,
                                "district_id": district_id,
                                "levy_cd": district_id
                            }
                        )
                        logger.info(f"Inserted district {district_id} with ID {new_id}")
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error inserting district {district_id}: {str(e)}")
                
                # Update the sequence to be higher than our highest ID
                if success_count > 0:
                    try:
                        conn.execute(
                            text(f"ALTER SEQUENCE tax_district_temp_id_seq RESTART WITH {max_id + len(new_districts) + 1}")
                        )
                        logger.info(f"Updated sequence to start with {max_id + len(new_districts) + 1}")
                    except Exception as e:
                        logger.error(f"Error updating sequence: {str(e)}")
            
            logger.info(f"Successfully inserted {success_count} districts, skipped {skipped_count} existing districts")
            return success_count > 0 or skipped_count > 0
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return False

def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(description='Insert tax districts directly into the database')
    parser.add_argument('--ids', '-i', nargs='+', required=True, help='District IDs to insert')
    parser.add_argument('--year', '-y', type=int, help='Year for the districts')
    
    args = parser.parse_args()
    
    success = insert_districts(args.ids, args.year)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())