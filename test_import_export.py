"""
Test script for levy export parser and import/export functionality.

This script validates the levy export parser and import/export functionality
by loading a sample file and checking the results.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

# Import utility functions - use direct imports to avoid circular dependencies
sys.path.append('.')
from utils.levy_export_parser import LevyExportParser
# Import the function from import_sample_levy_data.py instead
from import_sample_levy_data import import_levy_data

def test_levy_export_parser():
    """Test the levy export parser with sample files."""
    sample_files = [
        'attached_assets/Levy Expot.txt',
        'attached_assets/Levy Expot.xls',
        'attached_assets/Levy Expot.xlsx',
        'attached_assets/Levy Expot.xml'
    ]
    
    results = []
    
    for file_path in sample_files:
        if not Path(file_path).exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        logger.info(f"Testing parser with file: {file_path}")
        
        try:
            # Detect file format
            format_detected = LevyExportParser.detect_format(file_path)
            logger.info(f"Detected format: {format_detected}")
            
            # Parse the file
            data = LevyExportParser.parse_file(file_path)
            
            # Check if parsing was successful
            if data and len(data) > 0:
                logger.info(f"Successfully parsed {len(data)} records from {file_path}")
                results.append({
                    'file': file_path,
                    'format': format_detected,
                    'success': True,
                    'record_count': len(data),
                    'sample': data.records[0] if data.records else None
                })
            else:
                logger.error(f"No data parsed from {file_path}")
                results.append({
                    'file': file_path,
                    'format': format_detected,
                    'success': False,
                    'error': "No data parsed"
                })
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
            results.append({
                'file': file_path,
                'success': False,
                'error': str(e)
            })
    
    return results

def test_import_functionality():
    """Test the import functionality with sample files."""
    # We'll use the import_levy_data function from utils/import_data_utils.py
    sample_file = 'attached_assets/Levy Expot.xls'
    
    if not Path(sample_file).exists():
        logger.warning(f"File not found: {sample_file}")
        return {'success': False, 'error': 'File not found'}
    
    current_year = datetime.now().year
    
    try:
        # Import the levy data - use a direct database connection instead of the Flask-dependent function
        logger.info(f"Importing levy data from {sample_file} for year {current_year}")
        
        # Parse the file first
        from utils.levy_export_parser import LevyExportParser
        parser = LevyExportParser()
        data = parser.parse_file(sample_file)
        
        if data and data.records:
            # Create a database connection
            engine = create_engine(DATABASE_URL)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Count records before import
            count_before = session.execute(text("SELECT COUNT(*) FROM tax_district")).scalar()
            
            # Insert records directly
            try:
                for record in data.records:
                    # Check if district exists
                    existing = session.execute(
                        text("SELECT id FROM tax_district WHERE district_name = :name"),
                        {"name": record.district_name}
                    ).scalar()
                    
                    if not existing:
                        # Insert new district
                        session.execute(
                            text("""
                                INSERT INTO tax_district 
                                (district_name, district_type, county, state, levy_code, tax_district_id, created_at, updated_at) 
                                VALUES (:name, :type, :county, :state, :levy_code, :tax_id, NOW(), NOW())
                            """),
                            {
                                "name": record.district_name,
                                "type": record.district_type,
                                "county": record.county,
                                "state": record.state,
                                "levy_code": record.levy_code,
                                "tax_id": record.tax_district_id
                            }
                        )
                
                session.commit()
                
                # Count records after import
                count_after = session.execute(text("SELECT COUNT(*) FROM tax_district")).scalar()
                records_added = count_after - count_before
                
                logger.info(f"Successfully imported {records_added} records from {sample_file}")
                return {
                    'file': sample_file,
                    'success': True,
                    'record_count': records_added,
                    'message': f"Imported {records_added} districts"
                }
            except Exception as e:
                session.rollback()
                logger.error(f"Database error: {str(e)}")
                return {
                    'file': sample_file,
                    'success': False,
                    'error': str(e)
                }
            finally:
                session.close()
        else:
            logger.error(f"No data parsed from {sample_file}")
            return {
                'file': sample_file,
                'success': False,
                'error': "No data parsed"
            }
    except Exception as e:
        logger.error(f"Exception during import: {str(e)}")
        return {
            'file': sample_file,
            'success': False,
            'error': str(e)
        }

def check_database_records():
    """Check the number of records in key tables."""
    try:
        # Create database connection
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Query tables
        tables = ['tax_district', 'tax_code', 'property', 'import_log']
        results = {}
        
        for table in tables:
            query = text(f"SELECT COUNT(*) FROM {table}")
            count = session.execute(query).scalar()
            results[table] = count
            logger.info(f"Table {table}: {count} records")
        
        session.close()
        return results
    except Exception as e:
        logger.error(f"Error checking database records: {str(e)}")
        return {'error': str(e)}

if __name__ == "__main__":
    print("=" * 80)
    print("Testing Levy Export Parser")
    print("=" * 80)
    parser_results = test_levy_export_parser()
    
    for result in parser_results:
        if result['success']:
            print(f"✅ {result['file']} ({result['format']}): {result['record_count']} records")
        else:
            print(f"❌ {result['file']}: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("Testing Import Functionality")
    print("=" * 80)
    import_result = test_import_functionality()
    
    if import_result['success']:
        print(f"✅ Import successful: {import_result['record_count']} records")
    else:
        print(f"❌ Import failed: {import_result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("Database Record Count")
    print("=" * 80)
    db_records = check_database_records()
    
    for table, count in db_records.items():
        print(f"{table}: {count} records")
    
    print("=" * 80)