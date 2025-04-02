"""
Import sample levy export data into the database.

This script imports the sample levy export files from the attached_assets folder
into the database. It detects the format of the files and uses the appropriate
parser to extract the data.
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from models import db, TaxDistrict, TaxCode, ImportType, User
from utils.levy_export_parser import LevyExportParser, LevyExportFormat

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_levy_data(file_path, year_override=None):
    """
    Import levy data from a file.
    
    Args:
        file_path: Path to the levy export file
        year_override: Override the year in the file (optional)
        
    Returns:
        Tuple of (success, error_message, record_count)
    """
    try:
        # Detect file format
        file_format = LevyExportParser.detect_format(file_path)
        
        if file_format == LevyExportFormat.UNKNOWN:
            return False, f"Unknown file format for {file_path}", 0
        
        # Parse the file
        levy_data = LevyExportParser.parse_file(file_path)
        
        record_count = len(levy_data)
        if record_count == 0:
            return False, f"No records found in file {file_path}", 0
        
        # Process the data
        success_count = 0
        error_count = 0
        
        # Add/update tax districts and tax codes
        for record in levy_data.records:
            try:
                year = year_override or record['year']
                tax_district_id = record['tax_district_id']
                levy_code = record['levy_cd']
                levy_code_linked = record.get('levy_cd_linked')
                
                # Check if tax district exists using raw SQL
                check_query = text("""
                    SELECT 1 FROM tax_district 
                    WHERE year = :year AND district_code = :district_code
                    LIMIT 1
                """)
                
                result = db.session.execute(check_query, {
                    'year': year,
                    'district_code': levy_code
                }).scalar()
                
                if not result:
                    # Create new tax district using raw SQL
                    insert_query = text("""
                        INSERT INTO tax_district 
                        (year, district_code, district_name, is_active, created_at, updated_at)
                        VALUES 
                        (:year, :district_code, :district_name, TRUE, :created_at, :updated_at)
                        ON CONFLICT (district_code, year) DO NOTHING
                    """)
                    
                    db.session.execute(insert_query, {
                        'year': year,
                        'district_code': levy_code,
                        'district_name': levy_code,  # Use code as name if not provided
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                
                # Link levy codes
                if levy_code_linked:
                    # Check if linked tax district exists
                    check_linked_query = text("""
                        SELECT 1 FROM tax_district 
                        WHERE year = :year AND district_code = :district_code
                        LIMIT 1
                    """)
                    
                    linked_result = db.session.execute(check_linked_query, {
                        'year': year,
                        'district_code': levy_code_linked
                    }).scalar()
                    
                    if not linked_result:
                        # Create new linked tax district
                        insert_linked_query = text("""
                            INSERT INTO tax_district 
                            (year, district_code, district_name, is_active, created_at, updated_at)
                            VALUES 
                            (:year, :district_code, :district_name, TRUE, :created_at, :updated_at)
                            ON CONFLICT (district_code, year) DO NOTHING
                        """)
                        
                        db.session.execute(insert_linked_query, {
                            'year': year,
                            'district_code': levy_code_linked,
                            'district_name': levy_code_linked,  # Use code as name if not provided
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        })
                
                success_count += 1
            except Exception as e:
                logger.error(f"Error processing record: {str(e)}")
                error_count += 1
        
        # Log the import using a direct SQL insert
        # First check if the import_log table exists and has the right structure
        try:
            # Create a simple log entry with year and filename only
            import_metadata = json.dumps({
                'file_format': file_format.name,
                'parser': 'LevyExportParser',
                'years': levy_data.get_years(),
                'tax_districts': len(levy_data.get_tax_districts()),
                'levy_codes': len(levy_data.get_levy_codes())
            })
            
            # Attempt to link to admin user if it exists
            admin_user = db.session.query(User).filter(User.is_admin == True).first()
            user_id = admin_user.id if admin_user else None
            
            # Insert a new log entry
            insert_stmt = text("""
                INSERT INTO import_log 
                (filename, year, created_at, updated_at) 
                VALUES (:filename, :year, :created_at, :updated_at)
            """)
            
            db.session.execute(insert_stmt, {
                'filename': os.path.basename(file_path),
                'year': year_override or levy_data.get_years()[0],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to create import log: {str(e)}")
            # Continue even if logging fails
        
        return True, f"Successfully imported {success_count} records from {file_path}", record_count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing levy data: {str(e)}")
        return False, str(e), 0

def import_all_sample_files():
    """
    Import all sample levy export files.
    
    Returns:
        List of tuples with import results
    """
    results = []
    sample_files = [
        Path('attached_assets/Levy Expot.txt'),
        Path('attached_assets/Levy Expot.xlsx'),
        Path('attached_assets/Levy Expot.xls'),
    ]
    
    for file_path in sample_files:
        if file_path.exists():
            logger.info(f"Importing {file_path}...")
            success, message, count = import_levy_data(str(file_path))
            results.append((file_path, success, message, count))
        else:
            logger.warning(f"Sample file not found: {file_path}")
    
    return results

if __name__ == "__main__":
    # Create the Flask app
    app = create_app()
    
    # Use app context for database operations
    with app.app_context():
        logger.info("Starting import of sample levy export files...")
        
        # Check if we already have data in the database
        try:
            # Use raw SQL to check for existing tax districts
            check_query = text("""
                SELECT COUNT(*) FROM tax_district
            """)
            result = db.session.execute(check_query).scalar()
            
            if result > 0:
                logger.warning(f"Found {result} existing tax district records in the database")
                response = input("Do you want to proceed with importing sample data? [y/N]: ")
                if response.lower() != 'y':
                    logger.info("Import cancelled")
                    sys.exit(0)
        except Exception as e:
            logger.warning(f"Error checking for existing data: {str(e)}")
            # Continue with import even if check fails
        
        # Import all sample files
        results = import_all_sample_files()
        
        # Display results
        logger.info("\nImport results:")
        for file_path, success, message, count in results:
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"{status}: {file_path} - {message} ({count} records)")
        
        logger.info("Sample data import completed")