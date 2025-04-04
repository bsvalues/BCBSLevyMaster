"""
Minimal script to add tax districts and tax codes.

This script adds a few tax districts and tax codes to the database
while avoiding primary key conflicts and addressing schema issues.
"""

import os
import sys
import logging
import random
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample district data
SAMPLE_DISTRICTS = [
    {"code": "10001", "name": "North County School District", "year": 2024},
    {"code": "10002", "name": "South County Fire Protection", "year": 2024},
    {"code": "10003", "name": "Westside Library District", "year": 2024},
    {"code": "10004", "name": "Central Park District", "year": 2024},
    {"code": "10005", "name": "East County Water Reclamation", "year": 2024}
]

def get_sample_tax_codes(district_ids):
    """
    Generate sample tax codes for the given district IDs.
    
    Args:
        district_ids: Dictionary mapping district codes to their IDs
        
    Returns:
        List of dictionaries with tax code data
    """
    tax_codes = []
    current_year = 2024
    
    for district_code, district_id in district_ids.items():
        for i in range(1, 4):  # Generate 3 tax codes per district
            # Generate somewhat realistic tax rate (between 0.01 and 0.10)
            rate = round(random.uniform(0.01, 0.10), 6)
            
            # Generate somewhat realistic assessed value (between $1M and $50M)
            value = round(random.uniform(1_000_000, 50_000_000), 2)
            
            tax_codes.append({
                "code": f"{district_code}-{i:03d}",
                "district_id": district_id,
                "rate": rate,
                "value": value,
                "year": current_year
            })
    
    return tax_codes

def seed_districts_and_tax_codes():
    """
    Add minimal tax districts and tax codes to the database.
    
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
        
        # Check if we already have data
        count_query = text("SELECT COUNT(*) FROM tax_district")
        district_count = session.execute(count_query).scalar() or 0
        
        count_query = text("SELECT COUNT(*) FROM tax_code")
        tax_code_count = session.execute(count_query).scalar() or 0
        
        if district_count > 0 and tax_code_count > 0:
            logger.info(f"Database already has data: {district_count} districts, {tax_code_count} tax codes")
            
            # Get existing district IDs for reference
            district_ids = {}
            for district in SAMPLE_DISTRICTS:
                query = text("""
                    SELECT id FROM tax_district WHERE district_code = :code
                """)
                result = session.execute(query, {"code": district["code"]}).first()
                if result:
                    district_ids[district["code"]] = result[0]
            
            # Return success and district IDs for possible use in tax code creation
            return 0, district_ids
        
        # 1. Create tax districts
        logger.info("Creating tax districts...")
        district_ids = {}
        
        for district_data in SAMPLE_DISTRICTS:
            # Check if district already exists
            check_query = text("""
                SELECT id FROM tax_district 
                WHERE district_code = :code
            """)
            existing = session.execute(check_query, {"code": district_data["code"]}).first()
            
            if existing:
                district_id = existing[0]
                logger.info(f"District already exists: {district_data['name']} ({district_data['code']}), ID: {district_id}")
                district_ids[district_data["code"]] = district_id
                continue
            
            # Insert new district - get the next available ID
            # First find the max ID in the table to avoid conflicts
            max_id_query = text("SELECT COALESCE(MAX(id), 0) + 1 FROM tax_district")
            next_id = session.execute(max_id_query).scalar()
            
            now = datetime.utcnow()
            insert_query = text("""
                INSERT INTO tax_district 
                (id, district_name, district_code, is_active, created_at, updated_at, year) 
                VALUES 
                (:id, :name, :code, :active, :created_at, :updated_at, :year)
                RETURNING id
            """)
            
            result = session.execute(insert_query, {
                "id": next_id,
                "name": district_data["name"],
                "code": district_data["code"],
                "active": True, 
                "created_at": now,
                "updated_at": now,
                "year": district_data["year"]
            })
            
            district_id = result.scalar()
            district_ids[district_data["code"]] = district_id
            logger.info(f"Created district: {district_data['name']} ({district_data['code']}), ID: {district_id}")
        
        session.commit()
        
        # 2. Create tax codes
        logger.info("Creating tax codes...")
        tax_code_data = get_sample_tax_codes(district_ids)
        tax_code_ids = []
        
        for tc_data in tax_code_data:
            # Check if tax code already exists
            check_query = text("""
                SELECT id FROM tax_code 
                WHERE tax_code = :code AND year = :year
            """)
            existing = session.execute(check_query, {
                "code": tc_data["code"], 
                "year": tc_data["year"]
            }).first()
            
            if existing:
                tax_code_id = existing[0]
                logger.info(f"Tax code already exists: {tc_data['code']} for year {tc_data['year']}, ID: {tax_code_id}")
                tax_code_ids.append(tax_code_id)
                continue
            
            # Calculate levy amount
            levy_amount = tc_data["rate"] * tc_data["value"]
            
            # Insert new tax code - get the next available ID
            max_id_query = text("SELECT COALESCE(MAX(id), 0) + 1 FROM tax_code")
            next_id = session.execute(max_id_query).scalar()
            
            now = datetime.utcnow()
            insert_query = text("""
                INSERT INTO tax_code 
                (id, tax_code, tax_district_id, total_assessed_value, total_levy_amount, 
                effective_tax_rate, year, created_at, updated_at) 
                VALUES 
                (:id, :code, :district_id, :value, :levy_amount, :rate, :year, :created_at, :updated_at)
                RETURNING id
            """)
            
            result = session.execute(insert_query, {
                "id": next_id,
                "code": tc_data["code"],
                "district_id": tc_data["district_id"],
                "value": tc_data["value"],
                "levy_amount": levy_amount,
                "rate": tc_data["rate"],
                "year": tc_data["year"],
                "created_at": now,
                "updated_at": now
            })
            
            tax_code_id = result.scalar()
            tax_code_ids.append(tax_code_id)
            logger.info(f"Created tax code: {tc_data['code']} with rate {tc_data['rate']:.6f}, ID: {tax_code_id}")
        
        session.commit()
        
        logger.info("Minimal data seeding completed successfully")
        logger.info(f"Created/updated {len(district_ids)} districts, {len(tax_code_ids)} tax codes")
        
        return 0, district_ids
        
    except Exception as e:
        logger.error(f"Error seeding districts and tax codes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1, {}
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    logger.info("Starting minimal district and tax code seeding...")
    exit_code, _ = seed_districts_and_tax_codes()
    sys.exit(exit_code)