#!/usr/bin/env python
"""
Insert Tax Codes Script

This script adds tax code entries for existing districts in the database.
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

def insert_tax_codes(district_ids, levy_rate=1000.0, levy_amount=None, year=None):
    """
    Insert tax codes for the specified districts.
    
    Args:
        district_ids: List of district IDs to add tax codes for
        levy_rate: The levy rate to use
        levy_amount: The levy amount to use (optional)
        year: Year to use for the tax codes (defaults to current year)
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
            # Start a transaction
            with conn.begin():
                # Get the current maximum ID for tax_code
                result = conn.execute(text("SELECT MAX(id) FROM tax_code"))
                max_id = result.scalar() or 0
                logger.info(f"Current maximum tax code ID: {max_id}")
                
                # Insert tax codes for each district
                success_count = 0
                for i, district_id in enumerate(district_ids):
                    # Find the district ID in the tax_district table
                    result = conn.execute(
                        text("SELECT id FROM tax_district WHERE tax_district_id = :district_id AND year = :year"),
                        {"district_id": district_id, "year": year}
                    )
                    db_district_id = result.scalar()
                    
                    if not db_district_id:
                        logger.warning(f"District {district_id} not found for year {year}")
                        continue
                    
                    new_id = max_id + i + 1
                    try:
                        # Insert with explicit ID that is higher than the max
                        conn.execute(
                            text("""
                                INSERT INTO tax_code
                                (id, tax_code, year, tax_district_id, levy_rate, levy_amount, created_at, updated_at)
                                VALUES
                                (:id, :tax_code, :year, :district_id, :rate, :amount, NOW(), NOW())
                            """),
                            {
                                "id": new_id,
                                "tax_code": district_id,
                                "year": year,
                                "district_id": db_district_id,
                                "rate": levy_rate,
                                "amount": levy_amount
                            }
                        )
                        logger.info(f"Inserted tax code for district {district_id} with ID {new_id}")
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error inserting tax code for district {district_id}: {str(e)}")
                
                # Update the sequence to be higher than our highest ID
                if success_count > 0:
                    try:
                        conn.execute(
                            text(f"ALTER SEQUENCE tax_code_id_seq RESTART WITH {max_id + len(district_ids) + 1}")
                        )
                        logger.info(f"Updated sequence to start with {max_id + len(district_ids) + 1}")
                    except Exception as e:
                        logger.error(f"Error updating sequence: {str(e)}")
                
                logger.info(f"Successfully inserted {success_count} out of {len(district_ids)} tax codes")
                return success_count > 0
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return False

def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(description='Insert tax codes for existing districts')
    parser.add_argument('--ids', '-i', nargs='+', required=True, help='District IDs to add tax codes for')
    parser.add_argument('--rate', '-r', type=float, default=1000.0, help='Levy rate to use')
    parser.add_argument('--amount', '-a', type=float, help='Levy amount to use')
    parser.add_argument('--year', '-y', type=int, help='Year for the tax codes')
    
    args = parser.parse_args()
    
    success = insert_tax_codes(args.ids, args.rate, args.amount, args.year)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())