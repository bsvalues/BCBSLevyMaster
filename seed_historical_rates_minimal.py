"""
Minimal script to add historical rate data for existing tax codes.

This script adds historical rate data for existing tax codes in the database,
maintaining a simple approach to avoid model conflicts and schema issues.
"""

import os
import sys
import logging
from datetime import datetime
import random

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_historical_years(current_year=2024, num_years=5):
    """Generate a list of historical years."""
    return list(range(current_year - num_years, current_year + 1))

def seed_historical_rates():
    """
    Add historical rate data for existing tax codes.
    
    Returns:
        int: 0 for success, 1 for error
    """
    try:
        # Connect to the database
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable is not set")
            return 1
        
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get all current tax codes
        tax_codes_query = text("""
            SELECT id, tax_code, effective_tax_rate, total_assessed_value, year 
            FROM tax_code
            WHERE year = 2024
        """)
        
        tax_codes = list(session.execute(tax_codes_query))
        
        if not tax_codes:
            logger.warning("No tax codes found for the current year.")
            return 0
        
        # Get historical years (excluding current year which is in tax_code table)
        historical_years = [year for year in get_historical_years() if year != 2024]
        
        # Counter for added records
        total_added = 0
        
        # Iterate through each tax code
        for tax_code in tax_codes:
            tax_code_id = tax_code.id
            base_rate = tax_code.effective_tax_rate
            base_value = tax_code.total_assessed_value
            tax_code_name = tax_code.tax_code
            current_year = tax_code.year
            
            # Create entries for each historical year
            for year in historical_years:
                # Skip if a historical record already exists for this code and year
                check_query = text("""
                    SELECT COUNT(*) FROM tax_code_historical_rate 
                    WHERE tax_code_id = :tax_code_id AND year = :year
                """)
                existing_count = session.execute(
                    check_query, 
                    {"tax_code_id": tax_code_id, "year": year}
                ).scalar()
                
                if existing_count > 0:
                    logger.info(f"Historical rate for tax code {tax_code_name} and year {year} already exists")
                    continue
                
                # Create synthetic rate with variations for prior years
                year_diff = current_year - year
                # Rate tends to decrease going backwards in time
                rate = base_rate * (1.0 - (year_diff * 0.02))  # 2% decrease per year going backwards
                rate = max(0.01, min(0.2, rate))  # Ensure rate stays in reasonable bounds
                
                # Values tend to be lower in prior years
                assessed_value = base_value * (1.0 - (year_diff * 0.03))  # 3% decrease per year going backwards
                
                # Calculate levy amount
                levy_amount = rate * assessed_value
                
                # Insert record using direct SQL to avoid ORM model mismatch
                now = datetime.utcnow()
                insert_query = text("""
                    INSERT INTO tax_code_historical_rate 
                    (tax_code_id, year, levy_rate, levy_amount, total_assessed_value, created_at, updated_at)
                    VALUES 
                    (:tax_code_id, :year, :levy_rate, :levy_amount, :total_assessed_value, :created_at, :updated_at)
                """)
                
                session.execute(insert_query, {
                    "tax_code_id": tax_code_id,
                    "year": year,
                    "levy_rate": rate,
                    "levy_amount": levy_amount,
                    "total_assessed_value": assessed_value,
                    "created_at": now,
                    "updated_at": now
                })
                
                total_added += 1
                
                logger.info(f"Created historical rate for {tax_code_name} in {year}: {rate:.6f}")
            
        # Commit all changes
        session.commit()
        
        logger.info(f"Successfully added {total_added} historical rate records")
        return 0
        
    except Exception as e:
        logger.error(f"Error seeding historical rates: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    logger.info("Starting minimal historical rate seeding...")
    exit_code = seed_historical_rates()
    sys.exit(exit_code)