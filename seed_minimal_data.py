"""
Seed minimal data for the Levy Calculation System.

This script adds a few tax districts and tax codes to the database quickly.
"""

import logging
import sys
from datetime import datetime

from app import create_app
from models import db, TaxDistrict, TaxCode, TaxCodeHistoricalRate
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample districts
SAMPLE_DISTRICTS = [
    {
        "code": "10001",
        "name": "North County School District",
        "year": 2024
    },
    {
        "code": "10002",
        "name": "Southport Fire Protection District",
        "year": 2024
    },
    {
        "code": "10003",
        "name": "Eastlake Water District",
        "year": 2024
    }
]

# Sample tax codes (2 per district)
def get_sample_tax_codes(districts):
    tax_codes = []
    for district in districts:
        for i in range(2):
            tax_codes.append({
                "code": f"{district.district_code}-{i+1:02d}",
                "district_id": district.id,
                "rate": 0.05 + (i * 0.02),  # 5% and 7% rates
                "value": 50000000 + (i * 10000000),  # $50M and $60M assessed values
                "year": district.year
            })
    return tax_codes

# Sample historical rates
def get_historical_years():
    return [2019, 2020, 2021, 2022, 2023, 2024]

def main():
    """Main function."""
    # Create Flask app
    app = create_app()
    
    # Use app context for database operations
    with app.app_context():
        logger.info("Starting minimal data seeding...")
        
        try:
            # First check if we already have data, using direct SQL for historical count
            # to avoid model-database schema mismatch
            district_count = TaxDistrict.query.count()
            tax_code_count = TaxCode.query.count()
            
            # Use direct SQL to check for historical rates
            historical_count_result = db.session.execute(text("SELECT COUNT(*) FROM tax_code_historical_rate"))
            historical_count = historical_count_result.scalar() or 0
            
            if district_count > 0 and tax_code_count > 0 and historical_count > 0:
                logger.info(f"Database already has data: {district_count} districts, {tax_code_count} tax codes, {historical_count} historical rates")
                return 0
            
            # 1. Create tax districts - using SQLAlchemy ORM directly without low-level operations
            logger.info("Creating tax districts...")
            districts = []
            
            for district_data in SAMPLE_DISTRICTS:
                # Check if district already exists
                existing_district = TaxDistrict.query.filter_by(
                    district_code=district_data["code"]
                ).first()
                
                if existing_district:
                    logger.info(f"District already exists: {district_data['name']} ({district_data['code']})")
                    districts.append(existing_district)
                    continue
                
                # Create new district
                district = TaxDistrict()
                district.district_code = district_data["code"]
                district.district_name = district_data["name"]
                district.year = district_data["year"]
                district.is_active = True
                district.created_at = datetime.utcnow()
                district.updated_at = datetime.utcnow()
                
                db.session.add(district)
                districts.append(district)
                logger.info(f"Created district: {district_data['name']} ({district_data['code']})")
            
            db.session.commit()
            
            # 2. Create tax codes
            logger.info("Creating tax codes...")
            tax_codes = []
            tax_code_data = get_sample_tax_codes(districts)
            
            for tc_data in tax_code_data:
                # Check if tax code already exists
                existing_tax_code = TaxCode.query.filter_by(
                    tax_code=tc_data["code"],
                    year=tc_data["year"]
                ).first()
                
                if existing_tax_code:
                    logger.info(f"Tax code already exists: {tc_data['code']} for year {tc_data['year']}")
                    tax_codes.append(existing_tax_code)
                    continue
                
                # Create new tax code
                tax_code = TaxCode()
                tax_code.tax_code = tc_data["code"]
                tax_code.tax_district_id = tc_data["district_id"]
                tax_code.total_assessed_value = tc_data["value"]
                tax_code.total_levy_amount = tc_data["rate"] * tc_data["value"]
                tax_code.effective_tax_rate = tc_data["rate"]
                tax_code.year = tc_data["year"]
                tax_code.created_at = datetime.utcnow()
                tax_code.updated_at = datetime.utcnow()
                
                db.session.add(tax_code)
                tax_codes.append(tax_code)
                logger.info(f"Created tax code: {tc_data['code']} with rate {tc_data['rate']:.6f}")
            
            db.session.commit()
            
            # 3. Create historical rates
            logger.info("Creating historical rates...")
            historical_years = get_historical_years()
            total_added = 0
            
            # Only create historical data for current year tax codes
            for tax_code in tax_codes:
                # Get the base rate from the tax code
                base_rate = tax_code.effective_tax_rate
                base_value = tax_code.total_assessed_value
                
                # Create entries for each historical year
                for year in historical_years:
                    # Skip current year which is already in tax_code table
                    if year == tax_code.year:
                        continue
                        
                    # Skip if a historical record already exists for this code and year
                    # Using direct SQL to avoid model mismatch
                    existing_query = text("""
                        SELECT id FROM tax_code_historical_rate 
                        WHERE tax_code_id = :tax_code_id AND year = :year
                        LIMIT 1
                    """)
                    existing_result = db.session.execute(
                        existing_query, 
                        {"tax_code_id": tax_code.id, "year": year}
                    )
                    existing = existing_result.first()
                    
                    if existing:
                        logger.info(f"Historical rate for tax code {tax_code.tax_code} and year {year} already exists")
                        continue
                    
                    # Create synthetic rate with variations for prior years
                    # Rate tends to decrease going backwards in time
                    year_diff = tax_code.year - year
                    rate = base_rate * (1.0 - (year_diff * 0.02))  # 2% decrease per year going backwards
                    rate = max(0.01, min(0.2, rate))  # Ensure rate stays in reasonable bounds
                    
                    # Values tend to be lower in prior years
                    assessed_value = base_value * (1.0 - (year_diff * 0.03))  # 3% decrease per year going backwards
                    
                    # Calculate levy amount
                    levy_amount = rate * assessed_value
                    
                    # Create historical rate record using direct SQL to avoid ORM model mismatch
                    now = datetime.utcnow()
                    
                    insert_query = text("""
                        INSERT INTO tax_code_historical_rate 
                        (tax_code_id, year, levy_rate, levy_amount, total_assessed_value, created_at, updated_at)
                        VALUES 
                        (:tax_code_id, :year, :levy_rate, :levy_amount, :total_assessed_value, :created_at, :updated_at)
                    """)
                    
                    db.session.execute(insert_query, {
                        "tax_code_id": tax_code.id,
                        "year": year,
                        "levy_rate": rate,
                        "levy_amount": levy_amount,
                        "total_assessed_value": assessed_value,
                        "created_at": now,
                        "updated_at": now
                    })
                    
                    total_added += 1
                    
                    logger.info(f"Created historical rate for {tax_code.tax_code} in {year}: {rate:.6f}")
            
            db.session.commit()
            
            logger.info("Minimal data seeding completed successfully")
            logger.info(f"Created {len(districts)} districts, {len(tax_codes)} tax codes")
            logger.info(f"Added {total_added} historical rate records")
            
            return 0
        except Exception as e:
            logger.error(f"Error seeding minimal data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)