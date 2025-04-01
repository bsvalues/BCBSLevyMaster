"""
Utility to generate test compliance data for testing the statutory compliance reports.
"""
import logging
from datetime import datetime, timedelta
import random

from app import db
from models import TaxCode, Property, TaxDistrict, ImportLog, ExportLog

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_test_compliance_data():
    """
    Generate test data for compliance reports.
    
    This function adds realistic compliance data to existing tax codes:
    - Sets previous_year_rate values
    - Ensures some tax codes have compliance issues
    - Creates sample import logs for testing deadline compliance
    
    Returns:
        Dict with summary of updates made
    """
    results = {
        'tax_codes_updated': 0,
        'compliant_tax_codes': 0,
        'non_compliant_tax_codes': 0,
        'import_logs_created': 0
    }
    
    # Get all tax codes
    tax_codes = TaxCode.query.all()
    
    if not tax_codes:
        logger.warning("No tax codes found. Please import tax codes first.")
        return {'error': 'No tax codes found'}
    
    # Update tax codes with previous year rates and compliance data
    for i, tax_code in enumerate(tax_codes):
        # Only update if rate exists
        if tax_code.levy_rate:
            # Set previous_year_rate (slightly lower than current to show increase)
            # Make 80% compliant (rate increase <= 1%) and 20% non-compliant
            is_compliant = i % 5 != 0  # Make every 5th tax code non-compliant
            
            if is_compliant:
                # Compliant: Previous rate is 0.5% to 1% lower than current
                decrease_factor = random.uniform(0.005, 0.01)
                previous_rate = tax_code.levy_rate / (1 + decrease_factor)
                results['compliant_tax_codes'] += 1
            else:
                # Non-compliant: Previous rate is more than 1% lower than current
                decrease_factor = random.uniform(0.02, 0.05)  # 2% to 5% increase
                previous_rate = tax_code.levy_rate / (1 + decrease_factor)
                results['non_compliant_tax_codes'] += 1
            
            tax_code.previous_year_rate = round(previous_rate, 4)
            results['tax_codes_updated'] += 1
    
    # Create recent import logs for testing deadline compliance
    now = datetime.now()
    
    # Create property import log from 30 days ago
    property_import = ImportLog(
        filename="property_data_test.csv",
        rows_imported=random.randint(1000, 5000),
        rows_skipped=random.randint(10, 50),
        import_date=now - timedelta(days=30),
        import_type='property'
    )
    db.session.add(property_import)
    results['import_logs_created'] += 1
    
    # Create district import log from 45 days ago
    district_import = ImportLog(
        filename="district_data_test.xml",
        rows_imported=random.randint(50, 200),
        rows_skipped=random.randint(0, 10),
        import_date=now - timedelta(days=45),
        import_type='district'
    )
    db.session.add(district_import)
    results['import_logs_created'] += 1
    
    # Create export log
    export_log = ExportLog(
        filename="tax_roll_test.csv",
        rows_exported=random.randint(1000, 5000),
        export_date=now - timedelta(days=15)
    )
    db.session.add(export_log)
    
    # Commit changes
    db.session.commit()
    
    logger.info(f"Generated test compliance data: {results}")
    
    return results

if __name__ == "__main__":
    # This allows running this script directly
    from app import app
    with app.app_context():
        generate_test_compliance_data()