"""
Comprehensive seeding script to add all necessary minimal data.

This script runs all minimal data seeding scripts in the proper order,
ensuring that the database has the minimal required data for the application
to function properly while avoiding conflicts with ORM models.
"""

import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_all_seeders():
    """
    Run all minimal data seeding scripts in sequence.
    
    Returns:
        int: 0 for success, 1 for error
    """
    start_time = datetime.now()
    logger.info(f"Starting comprehensive minimal data seeding at {start_time}")
    
    try:
        # Import and run the district and tax code seeder
        logger.info("Step 1: Seeding districts and tax codes...")
        from seed_districts_minimal import seed_districts_and_tax_codes
        result = seed_districts_and_tax_codes()
        
        if isinstance(result, tuple):
            status_districts = result[0]
        else:
            status_districts = result
            
        if status_districts != 0:
            logger.error("Failed to seed districts and tax codes")
            return 1
        
        # Import and run the historical rates seeder
        logger.info("Step 2: Seeding historical rates...")
        from seed_historical_rates_minimal import seed_historical_rates
        status_rates = seed_historical_rates()
        
        if status_rates != 0:
            logger.error("Failed to seed historical rates")
            return 1
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Comprehensive minimal data seeding completed successfully in {duration:.2f} seconds")
        return 0
        
    except Exception as e:
        logger.error(f"Error during comprehensive minimal data seeding: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = run_all_seeders()
    sys.exit(exit_code)