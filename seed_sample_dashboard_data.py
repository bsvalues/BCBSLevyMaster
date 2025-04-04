"""
Seed sample data for the dashboard.

This script creates sample data for the dashboard, including tax districts,
tax codes, properties, and import logs.
"""

import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import func, inspect

from app import app, db
from models import TaxDistrict, TaxCode, Property, ImportLog, User, PropertyType, ImportType

# Configure logger
logger = logging.getLogger(__name__)


def seed_tax_districts(year=2025, count=10):
    """
    Seed sample tax districts.
    
    Args:
        year: Tax year
        count: Number of districts to create
    """
    logger.info(f"Seeding {count} tax districts for year {year}")
    
    district_types = ['SCHOOL', 'FIRE', 'COUNTY', 'CITY', 'HOSPITAL', 'LIBRARY', 'PORT']
    counties = ['BENTON', 'KING', 'PIERCE', 'SPOKANE', 'CLARK']
    
    # Get the admin user (used for created_by)
    admin = User.query.filter_by(username='admin').first()
    
    for i in range(1, count + 1):
        district_type = random.choice(district_types)
        county = random.choice(counties)
        
        district = TaxDistrict(
            district_name=f"{county} {district_type} DISTRICT {i}",
            district_code=f"{district_type[:3]}{i:03d}",
            district_type=district_type,
            county=county,
            state='WA',
            description=f"Sample {district_type.lower()} district in {county.lower()} county",
            is_active=True,
            contact_name=f"Contact {i}",
            contact_email=f"contact{i}@example.com",
            contact_phone=f"(555) 555-{i:04d}",
            statutory_limit=random.uniform(1.0, 5.0),
            year=year,
            created_by_id=admin.id if admin else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(district)
    
    db.session.commit()
    logger.info(f"Successfully seeded {count} tax districts")


def seed_tax_codes(year=2025, codes_per_district=3):
    """
    Seed sample tax codes.
    
    Args:
        year: Tax year
        codes_per_district: Number of tax codes per district
    """
    logger.info(f"Seeding tax codes for year {year}")
    
    # Get districts for the year
    districts = TaxDistrict.query.filter_by(year=year).all()
    
    if not districts:
        logger.warning(f"No districts found for year {year}")
        return
    
    # Get the admin user (used for created_by)
    admin = User.query.filter_by(username='admin').first()
    
    total_count = 0
    for district in districts:
        for i in range(1, codes_per_district + 1):
            # Generate random values for assessed value and levy amount
            assessed_value = random.uniform(10000000, 500000000)
            levy_amount = assessed_value * random.uniform(0.001, 0.005)
            effective_rate = (levy_amount / assessed_value) * 1000  # Per $1,000 of assessed value
            
            tax_code = TaxCode(
                tax_code=f"{district.district_code}-{i:02d}",
                tax_district_id=district.id,
                description=f"Tax code {i} for {district.district_name}",
                total_assessed_value=assessed_value,
                total_levy_amount=levy_amount,
                effective_tax_rate=effective_rate,
                year=year,
                created_by_id=admin.id if admin else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(tax_code)
            total_count += 1
    
    db.session.commit()
    logger.info(f"Successfully seeded {total_count} tax codes")


def seed_properties(year=2025, properties_per_code=10):
    """
    Seed sample properties.
    
    Args:
        year: Tax year
        properties_per_code: Number of properties per tax code
    """
    logger.info(f"Seeding properties for year {year}")
    
    # Get tax codes for the year
    tax_codes = TaxCode.query.filter_by(year=year).all()
    
    if not tax_codes:
        logger.warning(f"No tax codes found for year {year}")
        return
    
    # Get the admin user (used for created_by)
    admin = User.query.filter_by(username='admin').first()
    
    # Property types
    property_types = list(PropertyType)
    
    total_count = 0
    for tax_code in tax_codes:
        for i in range(1, properties_per_code + 1):
            # Generate a random property
            assessed_value = random.uniform(100000, 2000000)
            market_value = assessed_value * random.uniform(1.1, 1.5)
            land_value = assessed_value * random.uniform(0.3, 0.6)
            building_value = assessed_value - land_value
            tax_exempt = random.random() < 0.05  # 5% chance of being tax exempt
            
            exemption_amount = 0
            if tax_exempt:
                exemption_amount = assessed_value
            
            taxable_value = assessed_value - exemption_amount
            tax_amount = (taxable_value / 1000) * tax_code.effective_tax_rate
            
            property_type = random.choice(property_types)
            
            parcel_id = f"{tax_code.tax_code}-{i:04d}"
            
            property = Property(
                parcel_id=parcel_id,
                tax_code_id=tax_code.id,
                owner_name=f"Owner {parcel_id}",
                property_address=f"{random.randint(100, 9999)} Main St",
                city=f"City {random.randint(1, 20)}",
                state="WA",
                zip_code=f"98{random.randint(100, 999)}",
                property_type=property_type,
                assessed_value=assessed_value,
                market_value=market_value,
                land_value=land_value,
                building_value=building_value,
                tax_exempt=tax_exempt,
                exemption_amount=exemption_amount,
                taxable_value=taxable_value,
                tax_amount=tax_amount,
                longitude=random.uniform(-123.0, -117.0),
                latitude=random.uniform(45.0, 49.0),
                year=year,
                created_by_id=admin.id if admin else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(property)
            total_count += 1
            
            # Commit in batches to avoid memory issues
            if total_count % 100 == 0:
                db.session.commit()
    
    db.session.commit()
    logger.info(f"Successfully seeded {total_count} properties")


def seed_import_logs(year=2025, count=10):
    """
    Seed sample import logs with schema compatibility handling.
    
    Args:
        year: Tax year
        count: Number of import logs to create
    """
    logger.info(f"Seeding {count} import logs for year {year}")
    
    # Check if ImportLog schema has the required columns
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    
    try:
        # Check if import_log table exists
        if 'import_log' not in inspector.get_table_names():
            logger.warning("ImportLog table does not exist, skipping import log seeding")
            return
            
        import_log_columns = {column['name'] for column in inspector.get_columns('import_log')}
        logger.info(f"ImportLog columns: {import_log_columns}")
        
        # Get the admin user
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            logger.warning("Admin user not found")
            return
            
        # Handle ImportType - check if it's an Enum or a String in the schema
        import_type_values = []
        try:
            # Try to use the Enum
            import_types = list(ImportType)
            import_type_values = [import_type for import_type in import_types]
        except (NameError, TypeError):
            # Fallback to strings if ImportType is not an Enum
            import_type_values = ['TXT', 'XLS', 'XLSX', 'XML']
        
        # Status options
        statuses = ['SUCCESS', 'ERROR', 'PENDING', 'PROCESSING']
        
        for i in range(1, count + 1):
            # Random import details
            import_type_value = random.choice(import_type_values)
            status = random.choice(statuses)
            record_count = random.randint(10, 1000)
            
            success_count = 0
            error_count = 0
            error_details = None
            
            if status == 'SUCCESS':
                success_count = record_count
            elif status == 'ERROR':
                success_count = random.randint(0, record_count - 1)
                error_count = record_count - success_count
                error_details = "Sample error details for testing"
            elif status == 'PROCESSING':
                success_count = random.randint(0, record_count - 1)
                error_count = 0
            
            # Random date within the last month
            days_ago = random.randint(0, 30)
            created_at = datetime.utcnow() - timedelta(days=days_ago)
            
            # Processing time between 0.5 and 60 seconds
            processing_time = random.uniform(0.5, 60.0)
            
            # Create base import log data with minimal required fields
            import_log_data = {}
            
            # Map field names to values, only adding if field exists in schema
            field_map = {
                'user_id': admin.id,
                'filename': f"sample_import_{getattr(import_type_value, 'name', str(import_type_value)).lower()}_{i}.csv",
                'file_name': f"sample_import_{getattr(import_type_value, 'name', str(import_type_value)).lower()}_{i}.csv",
                'import_type': import_type_value,
                'record_count': record_count,
                'success_count': success_count,
                'error_count': error_count,
                'status': status,
                'error_details': error_details,
                'processing_time': processing_time,
                'year': year,
                'created_by_id': admin.id,
                'updated_by_id': admin.id,
                'created_at': created_at,
                'updated_at': created_at,
                'district_id': None  # Will be filled if needed
            }
            
            # Handle metadata/import_metadata field variants
            if 'import_metadata' in import_log_columns:
                field_map['import_metadata'] = {
                    "source": "Sample data",
                    "format": "CSV",
                    "version": "1.0"
                }
            elif 'metadata' in import_log_columns:
                field_map['metadata'] = {
                    "source": "Sample data",
                    "format": "CSV",
                    "version": "1.0"
                }
            
            # Add district_id if required
            if 'district_id' in import_log_columns:
                # Try to get a random tax district
                district = TaxDistrict.query.filter_by(year=year).order_by(func.random()).first()
                if district:
                    field_map['district_id'] = district.id
                else:
                    # Skip this import log if district_id is required but no districts exist
                    if field_map.get('district_id') is None:
                        logger.warning("No tax districts found for required district_id, skipping import log")
                        continue
            
            # Add fields that exist in the schema
            for field, value in field_map.items():
                if field in import_log_columns:
                    import_log_data[field] = value
            
            # Create import log instance
            try:
                import_log = ImportLog(**import_log_data)
                db.session.add(import_log)
            except TypeError as e:
                logger.error(f"Error creating import log: {str(e)}")
                logger.debug(f"Attempted with fields: {list(import_log_data.keys())}")
                continue
        
        db.session.commit()
        logger.info(f"Successfully seeded {count} import logs")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding import logs: {str(e)}")
        logger.warning("Skipping import log seeding due to error")


def seed_all_sample_data(force=False):
    """
    Seed all sample data for the dashboard.
    
    Args:
        force: If True, seed data even if it already exists
    """
    logger.info("Starting to seed sample dashboard data")
    
    current_year = datetime.now().year
    
    # Check if data already exists
    existing_districts = TaxDistrict.query.filter_by(year=current_year).count()
    if existing_districts > 0 and not force:
        logger.info(f"Sample data already exists for year {current_year}")
        return
        
    # If force is True and data exists, delete existing data
    if existing_districts > 0 and force:
        logger.info(f"Deleting existing sample data for year {current_year}")
        try:
            # Delete in the correct order to avoid foreign key constraints
            Property.query.filter_by(year=current_year).delete()
            TaxCode.query.filter_by(year=current_year).delete()
            TaxDistrict.query.filter_by(year=current_year).delete()
            
            # Check if ImportLog has year column before filtering by it
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            import_log_columns = [column['name'] for column in inspector.get_columns('import_log')]
            
            if 'year' in import_log_columns:
                ImportLog.query.filter_by(year=current_year).delete()
            else:
                logger.warning("ImportLog does not have 'year' column, skipping deletion of import logs")
                
            db.session.commit()
            logger.info("Existing data deleted successfully")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting existing data: {str(e)}")
            logger.info("Will proceed with creating new data anyway")
    
    try:
        # Seed tax districts
        seed_tax_districts(year=current_year, count=10)
        
        # Seed tax codes
        seed_tax_codes(year=current_year, codes_per_district=3)
        
        # Seed properties
        seed_properties(year=current_year, properties_per_code=10)
        
        # Seed import logs
        seed_import_logs(year=current_year, count=10)
        
        logger.info("Successfully seeded all sample dashboard data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding sample data: {str(e)}")
        raise


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    import sys
    
    # Check for force flag
    force = False
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        force = True
        print("Forcing reset of sample data...")
    
    # Create application context
    with app.app_context():
        seed_all_sample_data(force=force)