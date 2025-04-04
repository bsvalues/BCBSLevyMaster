"""
Seed sample data for the Levy Calculation System.

This script adds sample tax districts, tax codes, and properties to the database
for testing and development purposes.
"""

import os
import sys
import logging
import random
from datetime import datetime

from app import create_app
from models import db, TaxDistrict, TaxCode, Property, TaxCodeHistoricalRate, User
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
NUM_DISTRICTS = 5
NUM_CODES_PER_DISTRICT = 3
NUM_PROPERTIES = 20
SAMPLE_YEARS = [2022, 2023, 2024]


def generate_district_names():
    """Generate a list of sample district names."""
    return [
        "North County School District",
        "Southport Fire Protection District",
        "Eastlake Water District",
        "Westview Park District",
        "Central Library District",
        "Mountain View Hospital District",
        "Riverside Sanitation District",
        "Valley Agricultural District",
        "Metro Transit District",
        "Coastal Conservation District"
    ]


def seed_tax_districts():
    """
    Seed sample tax districts.
    
    Returns:
        List of created TaxDistrict objects
    """
    logger.info("Seeding tax districts...")
    
    # Check if we already have districts
    existing_count = TaxDistrict.query.count()
    if existing_count > 0:
        logger.warning(f"Found {existing_count} existing tax districts")
        # Just create new districts regardless
        
    # Generate district codes and names
    district_names = generate_district_names()
    districts = []
    
    # Create districts for each year
    for year in SAMPLE_YEARS:
        for i in range(min(NUM_DISTRICTS, len(district_names))):
            district_code = f"{10000 + i:05d}"
            district_name = district_names[i]
            
            # Check if district already exists for this year
            existing = TaxDistrict.query.filter_by(
                district_code=district_code,
                year=year
            ).first()
            
            if existing:
                logger.info(f"District {district_code} for year {year} already exists")
                districts.append(existing)
                continue
            
            district = TaxDistrict(
                district_code=district_code,
                district_name=district_name,
                year=year,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(district)
            districts.append(district)
            logger.info(f"Created district: {district_name} ({district_code}) for year {year}")
    
    db.session.commit()
    logger.info(f"Created {len(districts)} tax districts")
    return districts


def seed_tax_codes(districts):
    """
    Seed sample tax codes for the given districts.
    
    Args:
        districts: List of TaxDistrict objects
        
    Returns:
        List of created TaxCode objects
    """
    logger.info("Seeding tax codes...")
    
    # Check if we already have tax codes
    existing_count = TaxCode.query.count()
    if existing_count > 0:
        logger.warning(f"Found {existing_count} existing tax codes")
        # Just create new tax codes regardless
    
    tax_codes = []
    
    for district in districts:
        for i in range(NUM_CODES_PER_DISTRICT):
            # Generate a tax code based on district code with a suffix
            tax_code_value = f"{district.district_code}-{i+1:02d}"
            
            # Check if code already exists
            existing = TaxCode.query.filter_by(tax_code=tax_code_value).first()
            if existing:
                logger.info(f"Tax code {tax_code_value} already exists")
                tax_codes.append(existing)
                continue
            
            # Generate sample rate and values
            levy_rate = round(random.uniform(0.01, 0.15), 6)
            total_assessed_value = round(random.uniform(10000000, 100000000), 2)
            total_levy_amount = round(levy_rate * total_assessed_value, 2)
            
            # Create tax code
            tax_code = TaxCode(
                tax_code=tax_code_value,
                tax_district_id=district.id,
                total_assessed_value=total_assessed_value,
                total_levy_amount=total_levy_amount,
                effective_tax_rate=levy_rate,
                year=district.year,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(tax_code)
            tax_codes.append(tax_code)
            logger.info(f"Created tax code: {tax_code_value} with rate {levy_rate:.6f}")
    
    db.session.commit()
    logger.info(f"Created {len(tax_codes)} tax codes")
    return tax_codes


def seed_properties(tax_codes):
    """
    Seed sample properties.
    
    Args:
        tax_codes: List of TaxCode objects
        
    Returns:
        List of created Property objects
    """
    logger.info("Seeding properties...")
    
    # Check if we already have properties
    existing_count = Property.query.count()
    if existing_count > 0:
        logger.warning(f"Found {existing_count} existing properties")
        # Just create new properties regardless
    
    properties = []
    
    # Generate property data
    street_names = ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine Rd", "Elm Blvd", "Washington Ave"]
    
    for i in range(NUM_PROPERTIES):
        # Select a random tax code
        tax_code = random.choice(tax_codes)
        
        # Generate a property address
        house_number = random.randint(100, 9999)
        street_name = random.choice(street_names)
        address = f"{house_number} {street_name}"
        
        # Generate a PIN (Property Index Number)
        pin = f"{random.randint(10, 99)}-{random.randint(10, 99)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        
        # Generate property values
        assessed_value = round(random.uniform(100000, 1000000), 2)
        
        # Calculate taxes based on tax code effective rate
        property_tax = round(assessed_value * tax_code.effective_tax_rate, 2)
        
        # Create property
        property = Property(
            pin=pin,
            address=address,
            tax_code_id=tax_code.id,
            assessed_value=assessed_value,
            property_tax=property_tax,
            year=tax_code.year,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(property)
        properties.append(property)
        logger.info(f"Created property: {pin} at {address} with value {assessed_value:.2f}")
    
    db.session.commit()
    logger.info(f"Created {len(properties)} properties")
    return properties


def seed_historical_rates(tax_codes):
    """
    Seed historical rate data for the given tax codes.
    
    Args:
        tax_codes: List of TaxCode objects
        
    Returns:
        Dictionary with counts of created records by year
    """
    logger.info("Seeding historical rate data...")
    
    # Check if we already have historical rates
    existing_count = TaxCodeHistoricalRate.query.count()
    if existing_count > 0:
        logger.warning(f"Found {existing_count} existing historical rate records")
        # Just create new historical rates regardless
    
    # Define years for historical data
    historical_years = list(range(2019, max(SAMPLE_YEARS) + 1))
    
    results = {"total_added": 0}
    
    # Create historical entries for each tax code
    for tax_code in tax_codes:
        # Get the base rate from the tax code
        base_rate = tax_code.effective_tax_rate or 0.05
        base_value = tax_code.total_assessed_value or 10000000
        
        # Only create historical data for current year tax codes
        if tax_code.year != max(SAMPLE_YEARS):
            continue
        
        # Create entries for each historical year
        for i, year in enumerate(historical_years):
            # Skip if a historical record already exists for this code and year
            existing = TaxCodeHistoricalRate.query.filter_by(
                tax_code_id=tax_code.id, 
                year=year
            ).first()
            
            if existing:
                logger.info(f"Historical rate for tax code {tax_code.tax_code} and year {year} already exists")
                continue
            
            # Create synthetic rate with variations for prior years
            year_index = i
            
            # Rate tends to increase over time with minor fluctuations
            trend_factor = 1.0 - (max(SAMPLE_YEARS) - year) * 0.02  # 2% decrease per year going backwards
            random_factor = 1.0 + random.uniform(-0.05, 0.05)  # ±5% random variation
            rate = base_rate * trend_factor * random_factor
            rate = max(0.001, min(0.2, rate))  # Ensure rate stays in reasonable bounds
            
            # Values tend to be lower in prior years
            value_trend = 1.0 - (max(SAMPLE_YEARS) - year) * 0.03  # 3% decrease per year going backwards
            value_random = 1.0 + random.uniform(-0.1, 0.1)  # ±10% random variation
            assessed_value = base_value * value_trend * value_random
            
            # Calculate levy amount
            levy_amount = rate * assessed_value
            
            # Create historical rate record
            historical_rate = TaxCodeHistoricalRate(
                tax_code_id=tax_code.id,
                year=year,
                levy_rate=rate,
                levy_amount=levy_amount,
                total_assessed_value=assessed_value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(historical_rate)
            
            # Track results
            if year not in results:
                results[year] = 0
            results[year] += 1
            results["total_added"] += 1
            
            logger.info(f"Created historical rate for {tax_code.tax_code} in {year}: {rate:.6f}")
    
    db.session.commit()
    logger.info(f"Added {results['total_added']} historical rate records")
    return results


def main():
    """Main function."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Seed sample data for the Levy Calculation System")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip all confirmation prompts")
    parser.add_argument("--force", "-f", action="store_true", help="Force seeding even if data exists")
    args = parser.parse_args()
    
    # Override input function if auto-confirm is enabled
    if args.yes:
        global input
        original_input = input
        input = lambda prompt: "y"
    
    # Create Flask app
    app = create_app()
    
    # Use app context for database operations
    with app.app_context():
        logger.info("Starting sample data seeding...")
        
        try:
            # Create sample data
            districts = seed_tax_districts()
            tax_codes = seed_tax_codes(districts)
            properties = seed_properties(tax_codes)
            historical_results = seed_historical_rates(tax_codes)
            
            logger.info("Sample data seeding completed successfully")
            logger.info(f"Created/found {len(districts)} districts, {len(tax_codes)} tax codes, {len(properties)} properties")
            logger.info(f"Added {historical_results.get('total_added', 0)} historical rate records")
            
            return 0
        except Exception as e:
            logger.error(f"Error seeding sample data: {str(e)}")
            return 1


if __name__ == "__main__":
    sys.exit(main())