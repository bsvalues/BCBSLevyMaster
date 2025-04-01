"""
Script to seed database with test data for development and testing.
"""
import logging
from datetime import datetime

from app import app, db
from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_tax_codes():
    """Seed test tax codes with rates and assessed values."""
    logger.info("Seeding tax codes...")
    
    tax_codes = [
        {
            'code': 'TC-001',
            'levy_amount': 100000.0,
            'levy_rate': 10.0,
            'previous_year_rate': 9.5,
            'total_assessed_value': 10000000.0
        },
        {
            'code': 'TC-002',
            'levy_amount': 75000.0,
            'levy_rate': 15.0,
            'previous_year_rate': 14.5,
            'total_assessed_value': 5000000.0
        },
        {
            'code': 'TC-003',
            'levy_amount': 140000.0,
            'levy_rate': 7.0,
            'previous_year_rate': 7.5,
            'total_assessed_value': 20000000.0
        },
        {
            'code': 'TC-004',
            'levy_amount': 50000.0,
            'levy_rate': 5.0,
            'previous_year_rate': 4.95,
            'total_assessed_value': 10000000.0
        },
        {
            'code': 'TC-005',
            'levy_amount': 25000.0,
            'levy_rate': 5.0,
            'previous_year_rate': 5.1,
            'total_assessed_value': 5000000.0
        }
    ]
    
    for tc_data in tax_codes:
        tax_code = TaxCode.query.filter_by(code=tc_data['code']).first()
        if tax_code:
            # Update existing tax code
            for key, value in tc_data.items():
                setattr(tax_code, key, value)
        else:
            # Create new tax code
            tax_code = TaxCode(**tc_data)
            db.session.add(tax_code)
    
    db.session.commit()
    logger.info(f"Seeded {len(tax_codes)} tax codes")


def seed_properties():
    """Seed test properties."""
    logger.info("Seeding properties...")
    
    # Make sure tax codes exist
    tax_codes = TaxCode.query.all()
    if not tax_codes:
        seed_tax_codes()
        tax_codes = TaxCode.query.all()
    
    # Create properties for each tax code
    properties = []
    for tax_code in tax_codes:
        # Create 5 properties for each tax code
        for i in range(1, 6):
            property_id = f"PROP-{tax_code.code}-{i}"
            assessed_value = 200000.0 + (i * 50000.0)  # Vary the values
            
            prop = Property.query.filter_by(property_id=property_id).first()
            if prop:
                # Update existing property
                prop.assessed_value = assessed_value
                prop.tax_code = tax_code.code
            else:
                # Create new property
                prop = Property(
                    property_id=property_id,
                    assessed_value=assessed_value,
                    tax_code=tax_code.code
                )
                db.session.add(prop)
                properties.append(prop)
    
    db.session.commit()
    logger.info(f"Seeded {len(properties)} properties")


def seed_tax_districts():
    """Seed test tax districts."""
    logger.info("Seeding tax districts...")
    
    # Current year and previous year
    current_year = datetime.now().year
    previous_year = current_year - 1
    
    # Create some district relationships
    districts = [
        {
            'tax_district_id': 1,
            'year': current_year,
            'levy_code': 'TC-001',
            'linked_levy_code': 'TC-002'
        },
        {
            'tax_district_id': 1,
            'year': current_year,
            'levy_code': 'TC-001',
            'linked_levy_code': 'TC-003'
        },
        {
            'tax_district_id': 2,
            'year': current_year,
            'levy_code': 'TC-002',
            'linked_levy_code': 'TC-004'
        },
        {
            'tax_district_id': 3,
            'year': current_year,
            'levy_code': 'TC-003',
            'linked_levy_code': 'TC-005'
        },
        # Previous year relationships
        {
            'tax_district_id': 1,
            'year': previous_year,
            'levy_code': 'TC-001',
            'linked_levy_code': 'TC-002'
        },
        {
            'tax_district_id': 2,
            'year': previous_year,
            'levy_code': 'TC-002',
            'linked_levy_code': 'TC-004'
        },
    ]
    
    for district_data in districts:
        # Check if the relationship already exists
        district = TaxDistrict.query.filter_by(
            tax_district_id=district_data['tax_district_id'],
            year=district_data['year'],
            levy_code=district_data['levy_code'],
            linked_levy_code=district_data['linked_levy_code']
        ).first()
        
        if not district:
            district = TaxDistrict(**district_data)
            db.session.add(district)
    
    db.session.commit()
    logger.info(f"Seeded {len(districts)} tax district relationships")


def seed_logs():
    """Seed test import/export logs."""
    logger.info("Seeding logs...")
    
    # Import logs
    import_logs = [
        {
            'filename': 'properties_import.csv',
            'rows_imported': 25,
            'rows_skipped': 2,
            'warnings': 'Some rows had missing data',
            'import_type': 'property',
            'import_date': datetime.now()
        },
        {
            'filename': 'districts_import.txt',
            'rows_imported': 10,
            'rows_skipped': 0,
            'warnings': None,
            'import_type': 'district',
            'import_date': datetime.now()
        }
    ]
    
    for log_data in import_logs:
        log = ImportLog(**log_data)
        db.session.add(log)
    
    # Export logs
    export_logs = [
        {
            'filename': 'tax_roll_export.csv',
            'rows_exported': 25,
            'export_date': datetime.now()
        }
    ]
    
    for log_data in export_logs:
        log = ExportLog(**log_data)
        db.session.add(log)
    
    db.session.commit()
    logger.info(f"Seeded {len(import_logs)} import logs and {len(export_logs)} export logs")


def seed_all():
    """Seed all test data."""
    with app.app_context():
        seed_tax_codes()
        seed_properties()
        seed_tax_districts()
        seed_logs()
        logger.info("All test data seeded successfully")


if __name__ == "__main__":
    seed_all()