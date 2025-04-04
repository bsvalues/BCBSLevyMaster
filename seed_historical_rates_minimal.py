#!/usr/bin/env python
"""
Seed Historical Rates Script

This script seeds the database with sample historical tax rate data using the
simple_csv_import utility or direct SQL insertion.
"""

import os
import sys
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

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
    
    try:
        # Connect to the database
        engine = create_engine(db_url)
        # We'll use separate connections for each operation to avoid transaction conflicts
        
        # First, check if the table exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'tax_code_historical_rate'
                )
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.warning("tax_code_historical_rate table does not exist, creating it")
                with conn.begin():
                    conn.execute(text("""
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
                    """))
                    conn.execute(text("CREATE INDEX idx_historical_rate_tax_code_id ON tax_code_historical_rate(tax_code_id)"))
                    conn.execute(text("CREATE INDEX idx_historical_rate_year ON tax_code_historical_rate(year)"))
        
        success_count = 0
        error_count = 0
        
        # For each tax code, create historical rates
        for tax_code in tax_codes:
            # Create a new connection for each tax code to avoid transaction conflicts
            with engine.connect() as conn:
                # Find the tax code in the database
                result = conn.execute(text("""
                    SELECT id, levy_rate FROM tax_code WHERE tax_code = :tax_code
                """), {"tax_code": tax_code})
                tax_code_data = result.fetchone()
                
                if not tax_code_data:
                    logger.warning(f"Tax code {tax_code} not found in the database")
                    continue
                
                tax_code_id = tax_code_data[0]
                current_rate = tax_code_data[1]
                
                # Create a batch of historical rates for this tax code
                for year in range(start_year, end_year + 1):
                    # Calculate a rate that gradually approaches the current rate
                    # This creates a realistic trend over time
                    years_diff = end_year - year + 1
                    variation = 0.85 + (0.3 * (years_diff / (end_year - start_year + 1)))
                    historical_rate = current_rate * variation
                    
                    # Start a fresh transaction for each year
                    with conn.begin():
                        try:
                            # Check if an entry for this tax code and year already exists
                            result = conn.execute(text("""
                                SELECT id FROM tax_code_historical_rate 
                                WHERE tax_code_id = :tax_code_id AND year = :year
                            """), {"tax_code_id": tax_code_id, "year": year})
                            
                            if result.fetchone():
                                # Update existing record
                                conn.execute(text("""
                                    UPDATE tax_code_historical_rate 
                                    SET levy_rate = :rate, updated_at = NOW()
                                    WHERE tax_code_id = :tax_code_id AND year = :year
                                """), {
                                    "tax_code_id": tax_code_id,
                                    "year": year,
                                    "rate": historical_rate
                                })
                            else:
                                # Insert new record
                                conn.execute(text("""
                                    INSERT INTO tax_code_historical_rate 
                                    (tax_code_id, year, levy_rate, created_at, updated_at)
                                    VALUES (:tax_code_id, :year, :rate, NOW(), NOW())
                                """), {
                                    "tax_code_id": tax_code_id,
                                    "year": year,
                                    "rate": historical_rate
                                })
                            
                            success_count += 1
                            logger.info(f"Created historical rate for tax code {tax_code}, year {year}")
                            
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Error creating historical rate for tax code {tax_code}, year {year}: {str(e)}")
        
        logger.info(f"Completed: {success_count} rates created, {error_count} errors")
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