"""
Minimal script to add properties for existing tax codes.

This script adds property data for existing tax codes in the database,
maintaining a simple approach to avoid model conflicts and schema issues.
"""

import os
import random
import logging
import string
from datetime import datetime
from sqlalchemy import text
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Flask app to get database session
from app import app, db
from models import TaxCode

# Fixed current year for consistency
CURRENT_YEAR = 2024

# Sample address parts for generating random addresses
STREET_NAMES = [
    "Main", "Oak", "Maple", "Cedar", "Pine", "Elm", "Washington", "Franklin", 
    "Jefferson", "Adams", "Lincoln", "Grant", "Madison", "Monroe", "Wilson"
]

STREET_TYPES = ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Way", "Ct", "Pl", "Cir"]

CITY_NAMES = [
    "Springfield", "Riverdale", "Oakwood", "Fairview", "Greenville", 
    "Millville", "Centerville", "Lakeside", "Highland", "Pleasant Valley"
]

# Sample owner names
FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Susan", "Jessica"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin"
]

# Property types
PROPERTY_TYPES = ["RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL", "AGRICULTURAL", "VACANT_LAND"]

def generate_property_id() -> str:
    """Generate a random property ID in format XXXXX-XXX-XXX."""
    return f"{random.randint(10000, 99999)}-{random.randint(100, 999)}-{random.randint(100, 999)}"

def generate_address() -> str:
    """Generate a random street address."""
    street_num = random.randint(100, 9999)
    street_name = random.choice(STREET_NAMES)
    street_type = random.choice(STREET_TYPES)
    return f"{street_num} {street_name} {street_type}"

def generate_owner_name() -> str:
    """Generate a random owner name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def get_sample_properties(tax_codes: List[TaxCode], count_per_code: int = 5) -> List[Dict[str, Any]]:
    """
    Generate sample property data for the given tax codes.
    
    Args:
        tax_codes: List of tax code objects
        count_per_code: Number of properties to generate per tax code
        
    Returns:
        List of dictionaries with property data
    """
    properties = []
    
    for tax_code in tax_codes:
        for _ in range(count_per_code):
            # Generate random assessed value between $100,000 and $750,000
            assessed_value = random.randint(100000, 750000)
            
            # Random property type
            property_type = random.choice(PROPERTY_TYPES)
            
            properties.append({
                'property_id': generate_property_id(),
                'tax_code': tax_code.tax_code,
                'address': generate_address(),
                'owner_name': generate_owner_name(),
                'property_type': property_type,
                'assessed_value': assessed_value,
                'year': CURRENT_YEAR
            })
    
    return properties

def seed_properties():
    """
    Add minimal property data for existing tax codes.
    
    Returns:
        int: 0 for success, 1 for error
    """
    try:
        logger.info("Starting minimal property data seeding...")
        
        with app.app_context():
            # Get existing tax codes to link properties
            tax_codes = TaxCode.query.filter_by(year=CURRENT_YEAR).all()
            
            if not tax_codes:
                # If no tax codes for current year, try other years
                tax_codes = TaxCode.query.all()
                
            if not tax_codes:
                logger.error("No tax codes found in the database")
                return 1
            
            logger.info(f"Found {len(tax_codes)} tax codes to use for properties")
            
            # Generate sample properties
            sample_properties = get_sample_properties(tax_codes, count_per_code=10)
            
            # Insert properties using SQL to avoid ORM issues
            for prop_data in sample_properties:
                # Using SQL to directly insert into the property table
                sql = text("""
                    INSERT INTO property (
                        property_id, assessed_value, tax_code, 
                        address, owner_name, property_type, year, 
                        created_at, updated_at
                    ) VALUES (
                        :property_id, :assessed_value, :tax_code, 
                        :address, :owner_name, :property_type, :year, 
                        :created_at, :updated_at
                    )
                """)
                
                db.session.execute(sql, {
                    'property_id': prop_data['property_id'],
                    'assessed_value': prop_data['assessed_value'],
                    'tax_code': prop_data['tax_code'],
                    'address': prop_data['address'],
                    'owner_name': prop_data['owner_name'],
                    'property_type': prop_data['property_type'],
                    'year': prop_data['year'],
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
                
                logger.info(f"Created property: {prop_data['property_id']} with assessed value {prop_data['assessed_value']}")
            
            # Commit the changes
            db.session.commit()
            
            # Get count of properties created
            result = db.session.execute(text("SELECT COUNT(*) FROM property"))
            property_count = result.scalar()
            
            logger.info(f"Minimal property data seeding completed successfully")
            logger.info(f"Total properties in database: {property_count}")
            
            return 0
    
    except Exception as e:
        logger.error(f"Error seeding properties: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = seed_properties()
    exit(exit_code)