#!/usr/bin/env python
"""
Seed All Minimal Data Script

This script calls all the minimal seeding scripts to populate the database
with a complete minimal dataset for testing and development.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to seed all minimal data."""
    parser = argparse.ArgumentParser(description='Seed all minimal data for testing')
    parser.add_argument('--year', '-y', type=int, default=datetime.now().year, help='Year for data')
    parser.add_argument('--skip-districts', action='store_true', help='Skip district creation')
    parser.add_argument('--skip-tax-codes', action='store_true', help='Skip tax code creation')
    parser.add_argument('--skip-properties', action='store_true', help='Skip property creation')
    parser.add_argument('--skip-historical', action='store_true', help='Skip historical rates')
    parser.add_argument('--district-ids', nargs='+', default=['801', '802', '803', '804', '805'], help='District IDs to create')
    
    args = parser.parse_args()
    
    success = True
    
    # Insert tax districts
    if not args.skip_districts:
        logger.info("Inserting tax districts...")
        try:
            from direct_district_insert import insert_districts
            result = insert_districts(args.district_ids, args.year)
            if not result:
                logger.error("Failed to insert tax districts")
                success = False
            else:
                logger.info("Successfully inserted tax districts")
        except Exception as e:
            logger.error(f"Error inserting tax districts: {str(e)}")
            success = False
    
    # Insert tax codes
    if not args.skip_tax_codes and success:
        logger.info("Inserting tax codes...")
        try:
            from insert_tax_codes import insert_tax_codes
            result = insert_tax_codes(args.district_ids, 2500.0, None, args.year)
            if not result:
                logger.error("Failed to insert tax codes")
                success = False
            else:
                logger.info("Successfully inserted tax codes")
        except Exception as e:
            logger.error(f"Error inserting tax codes: {str(e)}")
            success = False
    
    # Seed properties
    if not args.skip_properties and success:
        logger.info("Seeding properties...")
        try:
            from seed_properties_minimal import seed_properties
            result = seed_properties('static/sample_property_simple.csv', args.year)
            if not result:
                logger.error("Failed to seed properties")
                success = False
            else:
                logger.info("Successfully seeded properties")
        except Exception as e:
            logger.error(f"Error seeding properties: {str(e)}")
            success = False
    
    # Seed historical rates
    if not args.skip_historical and success:
        logger.info("Seeding historical rates...")
        try:
            # Run the simplified historical rates seeding
            import subprocess
            cmd = [
                sys.executable, 
                "seed_historical_rates_simple.py", 
                "--tax-codes"
            ] + args.district_ids + [
                "--start-year", str(args.year - 5),
                "--end-year", str(args.year - 1)
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd)
            
            if result.returncode != 0:
                logger.error(f"Historical rates seeding process exited with code {result.returncode}")
                success = False
            else:
                logger.info("Successfully seeded historical rates")
        except Exception as e:
            logger.error(f"Error seeding historical rates: {str(e)}")
            success = False
    
    if success:
        logger.info("All minimal data seeded successfully!")
    else:
        logger.error("Minimal data seeding completed with errors")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())