"""
A simple script to import levy sample data from the attached_assets folder.

This script allows you to import levy data from a text or Excel file into the database.
It uses the LevyExportParser to parse the file and extract the data, then inserts
it into the tax_district table in the database.

Usage:
    python import_levy_sample.py [options]

Options:
    --yes, -y             Skip confirmation prompt and proceed with import
    --file, -f PATH       Specify a file path to import (default: attached_assets/Levy Expot.txt)

Examples:
    # Import the default file (attached_assets/Levy Expot.txt) with confirmation
    python import_levy_sample.py

    # Import the default file without confirmation
    python import_levy_sample.py --yes

    # Import a specific file with confirmation
    python import_levy_sample.py --file path/to/your/file.txt

    # Import a specific file without confirmation
    python import_levy_sample.py --file path/to/your/file.xlsx --yes
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

from sqlalchemy import text
from app import create_app, db
from utils.levy_export_parser import LevyExportParser, LevyExportFormat

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default file path to import if none specified
DEFAULT_SAMPLE_FILE_PATH = 'attached_assets/Levy Expot.txt'

def import_levy_data(file_path=None):
    """
    Import levy data from a file.
    
    Args:
        file_path: Path to the file to import, defaults to DEFAULT_SAMPLE_FILE_PATH
    """
    file_path = file_path or DEFAULT_SAMPLE_FILE_PATH
    if not os.path.exists(file_path):
        logger.error(f"Sample file not found: {file_path}")
        return False
    
    try:
        # Parse the file
        file_format = LevyExportParser.detect_format(file_path)
        logger.info(f"Detected format: {file_format.name}")
        
        levy_data = LevyExportParser.parse_file(file_path)
        logger.info(f"Parsed {len(levy_data)} records")
        logger.info(f"Years: {levy_data.get_years()}")
        logger.info(f"Tax Districts: {len(levy_data.get_tax_districts())}")
        logger.info(f"Levy Codes: {len(levy_data.get_levy_codes())}")
        
        # Process each record
        record_count = 0
        success_count = 0
        error_count = 0
        
        for record in levy_data.records:
            # Start a new transaction for each record
            try:
                year = record['year']
                tax_district_id = record['tax_district_id']
                levy_code = record['levy_cd']
                levy_code_linked = record.get('levy_cd_linked', '')
                
                # Check if the tax district already exists
                check_query = """
                    SELECT id FROM tax_district 
                    WHERE year = :year AND district_code = :district_code
                    LIMIT 1
                """
                
                existing_id = db.session.execute(text(check_query), {
                    'year': year,
                    'district_code': levy_code
                }).scalar()
                
                if not existing_id:
                    # If no existing record, get the maximum ID
                    max_id_query = "SELECT COALESCE(MAX(id), 0) + 1 FROM tax_district"
                    next_id = db.session.execute(text(max_id_query)).scalar()
                    
                    # Insert the tax district with a specific ID
                    insert_query = """
                        INSERT INTO tax_district 
                        (id, year, district_code, district_name, is_active, created_at, updated_at)
                        VALUES 
                        (:id, :year, :district_code, :district_name, TRUE, :created_at, :updated_at)
                        ON CONFLICT (district_code, year) DO NOTHING
                    """
                    
                    db.session.execute(text(insert_query), {
                        'id': next_id,
                        'year': year,
                        'district_code': levy_code,
                        'district_name': levy_code,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                
                # If there's a linked code, insert that too
                if levy_code_linked:
                    # Check if linked district already exists
                    linked_check_query = """
                        SELECT id FROM tax_district 
                        WHERE year = :year AND district_code = :district_code
                        LIMIT 1
                    """
                    
                    linked_existing_id = db.session.execute(text(linked_check_query), {
                        'year': year,
                        'district_code': levy_code_linked
                    }).scalar()
                    
                    if not linked_existing_id:
                        # If no existing record, get the maximum ID
                        max_id_query = "SELECT COALESCE(MAX(id), 0) + 1 FROM tax_district"
                        next_id = db.session.execute(text(max_id_query)).scalar()
                        
                        # Insert the linked tax district with a specific ID
                        linked_insert_query = """
                            INSERT INTO tax_district 
                            (id, year, district_code, district_name, is_active, created_at, updated_at)
                            VALUES 
                            (:id, :year, :district_code, :district_name, TRUE, :created_at, :updated_at)
                            ON CONFLICT (district_code, year) DO NOTHING
                        """
                        
                        db.session.execute(text(linked_insert_query), {
                            'id': next_id,
                            'year': year,
                            'district_code': levy_code_linked,
                            'district_name': levy_code_linked,
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        })
                
                # Commit after each record to avoid transaction issues
                db.session.commit()
                success_count += 1
                logger.info(f"Imported record {record_count+1}: {year}/{levy_code}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error importing record {record_count+1}: {str(e)}")
                error_count += 1
            
            record_count += 1
        
        # Create an import log entry
        try:
            log_query = """
                INSERT INTO import_log
                (filename, year, created_at, updated_at)
                VALUES
                (:filename, :year, :created_at, :updated_at)
            """
            
            db.session.execute(text(log_query), {
                'filename': os.path.basename(file_path),
                'year': levy_data.get_years()[0] if levy_data.get_years() else datetime.now().year,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            db.session.commit()
            logger.info(f"Created import log entry")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating import log: {str(e)}")
        
        logger.info(f"Import completed: {success_count} successes, {error_count} errors")
        return True
    except Exception as e:
        logger.error(f"Error parsing file: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Import levy sample data')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--file', '-f', type=str, help=f'File path to import (default: {DEFAULT_SAMPLE_FILE_PATH})')
    args = parser.parse_args()
    
    # Create the Flask app and context
    app = create_app()
    
    # Get the file path from arguments or use default
    file_path = args.file or DEFAULT_SAMPLE_FILE_PATH
    
    with app.app_context():
        logger.info(f"Starting import of file: {file_path}")
        
        # Check if the file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            sys.exit(1)
        
        # Check if we have existing data
        try:
            check_query = "SELECT COUNT(*) FROM tax_district"
            count = db.session.execute(text(check_query)).scalar()
            
            if count > 0 and not args.yes:
                logger.warning(f"Found {count} existing tax district records in the database")
                response = input("Do you want to proceed with importing sample data? [y/N]: ")
                if response.lower() != 'y':
                    logger.info("Import cancelled")
                    sys.exit(0)
            elif count > 0 and args.yes:
                logger.warning(f"Found {count} existing tax district records in the database, proceeding anyway (--yes flag)")
        except Exception as e:
            logger.warning(f"Error checking for existing data: {str(e)}")
        
        # Import the data
        if import_levy_data(file_path):
            logger.info("Import completed successfully")
        else:
            logger.error("Import failed")
            sys.exit(1)