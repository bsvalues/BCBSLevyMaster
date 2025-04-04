#!/usr/bin/env python
"""
Simple Historical Rates Seeding Script

This script seeds the database with sample historical tax rate data using
direct SQL insertion with careful transaction management.
"""

import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def seed_historical_rates(tax_codes, start_year=2020, end_year=2024):
    """
    Seed historical tax rates for a range of years.
    
    Args:
        tax_codes: List of tax code IDs to create historical rates for
        start_year: Starting year for historical data (inclusive)
        end_year: Ending year for historical data (inclusive)
    """
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not found")
        return False
    
    success_count = 0
    error_count = 0
    
    try:
        # Establish a connection to check if the table exists and create it if needed
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'tax_code_historical_rate'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.warning("tax_code_historical_rate table does not exist, creating it")
                cursor.execute("""
                    CREATE TABLE tax_code_historical_rate (
                        id SERIAL PRIMARY KEY,
                        tax_code_id INTEGER REFERENCES tax_code(id),
                        year INTEGER NOT NULL,
                        levy_rate FLOAT NOT NULL,
                        levy_amount FLOAT,
                        total_assessed_value FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tax_code_id, year)
                    )
                """)
                cursor.execute("CREATE INDEX idx_historical_rate_tax_code_id ON tax_code_historical_rate(tax_code_id)")
                cursor.execute("CREATE INDEX idx_historical_rate_year ON tax_code_historical_rate(year)")
                conn.commit()
                logger.info("Created tax_code_historical_rate table")
            else:
                logger.info("tax_code_historical_rate table already exists")
        
        conn.close()
        
        # Process each tax code with a fresh connection
        for tax_code in tax_codes:
            conn = psycopg2.connect(db_url)
            conn.autocommit = False
            
            try:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    # Find the tax code in the database
                    cursor.execute(
                        "SELECT id, levy_rate FROM tax_code WHERE tax_code = %s",
                        (tax_code,)
                    )
                    tax_code_data = cursor.fetchone()
                    
                    if not tax_code_data:
                        logger.warning(f"Tax code {tax_code} not found in the database")
                        continue
                    
                    tax_code_id = tax_code_data['id']
                    current_rate = tax_code_data['levy_rate']
                    
                    # Create historical rates for each year
                    for year in range(start_year, end_year + 1):
                        # Calculate a rate that gradually approaches the current rate
                        # This creates a realistic trend over time
                        years_diff = end_year - year + 1
                        variation = 0.85 + (0.3 * (years_diff / (end_year - start_year + 1)))
                        historical_rate = current_rate * variation
                        
                        # Check if an entry for this tax code and year already exists
                        cursor.execute(
                            "SELECT id FROM tax_code_historical_rate WHERE tax_code_id = %s AND year = %s",
                            (tax_code_id, year)
                        )
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Update existing record
                            cursor.execute(
                                "UPDATE tax_code_historical_rate SET levy_rate = %s, updated_at = NOW() WHERE tax_code_id = %s AND year = %s",
                                (historical_rate, tax_code_id, year)
                            )
                            logger.info(f"Updated historical rate for tax code {tax_code}, year {year}")
                        else:
                            # Insert new record
                            cursor.execute(
                                """
                                INSERT INTO tax_code_historical_rate 
                                (tax_code_id, year, levy_rate, created_at, updated_at)
                                VALUES (%s, %s, %s, NOW(), NOW())
                                """,
                                (tax_code_id, year, historical_rate)
                            )
                            logger.info(f"Created historical rate for tax code {tax_code}, year {year}")
                        
                        success_count += 1
                
                # Commit for this tax code
                conn.commit()
                logger.info(f"Committed changes for tax code {tax_code}")
                
            except Exception as e:
                conn.rollback()
                error_count += 1
                logger.error(f"Error processing tax code {tax_code}: {str(e)}")
            
            finally:
                conn.close()
        
        logger.info(f"Completed: {success_count} rates created/updated, {error_count} errors")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return False

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed historical tax rate data')
    parser.add_argument('--tax-codes', '-t', nargs='+', required=True, help='Tax codes to create historical rates for')
    parser.add_argument('--start-year', '-s', type=int, default=2020, help='Starting year (inclusive)')
    parser.add_argument('--end-year', '-e', type=int, default=2024, help='Ending year (inclusive)')
    
    args = parser.parse_args()
    
    success = seed_historical_rates(args.tax_codes, args.start_year, args.end_year)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())