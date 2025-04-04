"""
Seed historical rate data for analysis functionality.

This script adds sample historical tax rate data to enable the advanced historical
analysis functionality by creating entries in the tax_code_historical_rate table
for multiple years.
"""
import os
import sys
import random
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from models import db, TaxCode, TaxCodeHistoricalRate, TaxDistrict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
START_YEAR = 2019
END_YEAR = 2024  # Current year as default
YEARS_TO_SEED = list(range(START_YEAR, END_YEAR + 1))
SAMPLE_SIZE = 50  # Number of tax codes to seed if none exist


def create_synthetic_rate(base_rate, year_index, variance=0.05):
    """
    Create a synthetic rate with slight variations to simulate changes over time.
    
    Args:
        base_rate: The base rate to build from
        year_index: Index of the year (0 for first year, 1 for second, etc.)
        variance: Maximum variance as percentage of base rate
        
    Returns:
        A synthetically generated rate value
    """
    # Create trend - slight increase over time with random variations
    trend_factor = 1.0 + (year_index * 0.02)  # 2% increase per year on average
    
    # Add random variation
    random_factor = 1.0 + random.uniform(-variance, variance)
    
    # Combine factors and apply to base rate
    return base_rate * trend_factor * random_factor


def seed_historical_rates():
    """
    Seed historical tax rate data.
    
    Returns:
        Dictionary with counts of records added for each year
    """
    try:
        # Get all tax codes
        tax_codes = TaxCode.query.all()
        
        if not tax_codes:
            logger.warning("No tax codes found in database. Cannot seed historical rates.")
            return {"error": "No tax codes found"}
        
        # Check if we already have historical rates
        existing_count = TaxCodeHistoricalRate.query.count()
        if existing_count > 0:
            logger.warning(f"Found {existing_count} existing historical rate records")
            response = input("Do you want to proceed with seeding more historical rate data? [y/N]: ")
            if response.lower() != 'y':
                logger.info("Seeding cancelled by user")
                return {"status": "cancelled"}
        
        # Limit to a reasonable sample size if we have too many tax codes
        if len(tax_codes) > SAMPLE_SIZE:
            logger.info(f"Limiting to {SAMPLE_SIZE} tax codes for seeding historical data")
            tax_codes = random.sample(tax_codes, SAMPLE_SIZE)
        
        results = {"total_added": 0}
        
        # Create historical rate entries for each tax code and year
        for year in YEARS_TO_SEED:
            year_count = 0
            
            for tax_code in tax_codes:
                # Skip if a historical record already exists for this code and year
                existing = TaxCodeHistoricalRate.query.filter_by(
                    tax_code_id=tax_code.id, 
                    year=year
                ).first()
                
                if existing:
                    continue
                
                # Use the current rate as a base or generate one if not available
                base_rate = tax_code.levy_rate or random.uniform(0.01, 0.15)
                
                # Create synthetic rate with variations
                year_index = YEARS_TO_SEED.index(year)
                synthetic_rate = create_synthetic_rate(base_rate, year_index)
                
                # Generate synthetic assessed values
                base_assessed_value = random.uniform(1000000, 50000000)
                assessed_value = base_assessed_value * (1 + year_index * 0.03)  # 3% growth per year
                
                # Calculate levy amount
                levy_amount = assessed_value * synthetic_rate
                
                # Create historical rate record
                historical_rate = TaxCodeHistoricalRate(
                    tax_code_id=tax_code.id,
                    year=year,
                    levy_rate=synthetic_rate,
                    levy_amount=levy_amount,
                    total_assessed_value=assessed_value,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Add and commit
                db.session.add(historical_rate)
                year_count += 1
                
                # Commit in batches to avoid memory issues
                if year_count % 100 == 0:
                    db.session.commit()
            
            # Commit remaining records for this year
            db.session.commit()
            
            results[year] = year_count
            results["total_added"] += year_count
            
            logger.info(f"Added {year_count} historical rate records for {year}")
        
        return results
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding historical rates: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Create the Flask app
    app = create_app()
    
    # Use app context for database operations
    with app.app_context():
        logger.info(f"Starting seeding of historical tax rate data for years {YEARS_TO_SEED}...")
        
        # Seed historical rates
        results = seed_historical_rates()
        
        # Display results
        if "error" in results:
            logger.error(f"Seeding failed: {results['error']}")
        elif "status" in results and results["status"] == "cancelled":
            logger.info("Seeding cancelled by user")
        else:
            logger.info(f"\nSuccessfully added {results['total_added']} historical rate records:")
            for year in YEARS_TO_SEED:
                if year in results:
                    logger.info(f"  {year}: {results[year]} records")
        
        logger.info("Historical rate seeding completed")