"""
Advanced Import Script for Levy Data

This script allows you to import levy data from various file formats (TXT, XLS, XLSX, CSV, XML, JSON)
into the database using the enhanced Levy Export Parser. It automatically detects the file format,
extracts the data, and inserts it into the tax_district table in the database.

Usage:
    python import_levy_sample.py [options]

Options:
    --yes, -y             Skip confirmation prompt and proceed with import
    --file, -f PATH       Specify a file path to import (default: attached_assets/Levy Expot.txt)
    --year, -Y YEAR       Override the year in the file (default: use year from file)
    --sample, -s          Use sample files in attached_assets folder
    --all-samples, -a     Import all sample files in attached_assets folder
    --dry-run, -d         Parse the file but don't import to database
    --verbose, -v         Show verbose output during import

Examples:
    # Import the default file (attached_assets/Levy Expot.txt) with confirmation
    python import_levy_sample.py

    # Import the default file without confirmation
    python import_levy_sample.py --yes

    # Import a specific file with confirmation
    python import_levy_sample.py --file path/to/your/file.txt

    # Import a specific file without confirmation and override the year
    python import_levy_sample.py --file path/to/your/file.xlsx --yes --year 2025

    # Import all sample files in attached_assets folder
    python import_levy_sample.py --all-samples --yes

    # Parse a file without importing it (dry run)
    python import_levy_sample.py --file path/to/your/file.csv --dry-run
"""
import os
import sys
import json
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

def import_levy_data(file_path=None, year_override=None, dry_run=False, verbose=False):
    """
    Import levy data from a file.
    
    Args:
        file_path: Path to the file to import, defaults to DEFAULT_SAMPLE_FILE_PATH
        year_override: Override the year in the file (optional)
        dry_run: Parse the file but don't import to database
        verbose: Show verbose output during import
        
    Returns:
        Tuple of (success: bool, records_count: int, success_count: int, error_count: int)
    """
    file_path = file_path or DEFAULT_SAMPLE_FILE_PATH
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False, 0, 0, 0
    
    try:
        # Detect file format
        file_format = LevyExportParser.detect_format(file_path)
        logger.info(f"Detected format: {file_format.name}")
        
        if file_format == LevyExportFormat.UNKNOWN:
            logger.error(f"Unsupported file format for {file_path}")
            return False, 0, 0, 0
        
        # Parse the file
        levy_data = LevyExportParser.parse_file(file_path)
        
        # Override year if specified
        if year_override:
            for record in levy_data.records:
                record.data['year'] = year_override
        
        # Log summary information
        record_count = len(levy_data)
        logger.info(f"Parsed {record_count} records from {file_path}")
        logger.info(f"Years: {levy_data.get_years()}")
        
        if verbose:
            logger.info(f"Tax Districts: {levy_data.get_tax_districts()[:10]}..." if len(levy_data.get_tax_districts()) > 10 else levy_data.get_tax_districts())
            logger.info(f"Levy Codes: {levy_data.get_levy_codes()[:10]}..." if len(levy_data.get_levy_codes()) > 10 else levy_data.get_levy_codes())
            
            # Print sample records
            if record_count > 0:
                sample_record = levy_data.records[0]
                logger.info(f"Sample record: {sample_record.data}")
        
        # If dry run, just return success without importing
        if dry_run:
            logger.info(f"Dry run completed - {record_count} records would be imported")
            return True, record_count, 0, 0
        
        # Process each record
        success_count = 0
        error_count = 0
        
        for i, record in enumerate(levy_data.records):
            # Start a new transaction for each record
            try:
                year = record['year']
                tax_district_id = record['tax_district_id']
                levy_code = record['levy_cd']
                levy_code_linked = record.get('levy_cd_linked', '')
                levy_rate = record.get('levy_rate')
                levy_amount = record.get('levy_amount')
                assessed_value = record.get('assessed_value')
                
                if verbose:
                    logger.info(f"Processing record {i+1}/{record_count}: {year}/{levy_code}")
                
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
                        (id, year, district_code, district_name, is_active, 
                         tax_district_id, levy_code, created_at, updated_at)
                        VALUES 
                        (:id, :year, :district_code, :district_name, TRUE,
                         :tax_district_id, :levy_code, :created_at, :updated_at)
                        ON CONFLICT (district_code, year) DO NOTHING
                    """
                    
                    db.session.execute(text(insert_query), {
                        'id': next_id,
                        'year': year,
                        'district_code': levy_code,
                        'district_name': f"District {levy_code}",
                        'tax_district_id': int(levy_code) if levy_code.isdigit() else None,
                        'levy_code': levy_code,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                else:
                    # If record exists, update the linked_levy_code if available
                    if levy_code_linked:
                        update_query = """
                            UPDATE tax_district
                            SET linked_levy_code = :linked_levy_code,
                                updated_at = :updated_at
                            WHERE id = :id
                        """
                        
                        db.session.execute(text(update_query), {
                            'id': existing_id,
                            'linked_levy_code': levy_code_linked,
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
                            (id, year, district_code, district_name, is_active, 
                             tax_district_id, levy_code, linked_levy_code, created_at, updated_at)
                            VALUES 
                            (:id, :year, :district_code, :district_name, TRUE,
                             :tax_district_id, :levy_code, :linked_levy_code, :created_at, :updated_at)
                            ON CONFLICT (district_code, year) DO NOTHING
                        """
                        
                        db.session.execute(text(linked_insert_query), {
                            'id': next_id,
                            'year': year,
                            'district_code': levy_code_linked,
                            'district_name': f"District {levy_code_linked}",
                            'tax_district_id': int(levy_code_linked) if levy_code_linked.isdigit() else None,
                            'levy_code': levy_code_linked,
                            'linked_levy_code': levy_code,  # Cross-reference back to the original
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        })
                
                # Commit after each record to avoid transaction issues
                db.session.commit()
                success_count += 1
                
                if verbose or (i % 10 == 0 and record_count > 20):
                    logger.info(f"Imported record {i+1}/{record_count}: {year}/{levy_code}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error importing record {i+1}: {str(e)}")
                error_count += 1
        
        # Create an import log entry
        try:
            # First check if the import_metadata column exists
            check_column_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'import_log' AND column_name = 'import_metadata'
            """
            has_metadata_column = db.session.execute(text(check_column_query)).scalar() is not None
            
            # Prepare the metadata
            import_metadata = {
                'file_format': file_format.name,
                'source': os.path.basename(file_path),
                'year_detected': levy_data.get_years(),
                'tax_districts_count': len(levy_data.get_tax_districts()),
                'levy_codes_count': len(levy_data.get_levy_codes()),
                'start_time': datetime.utcnow().isoformat(),
                'year_override': year_override is not None
            }
            
            # Build the query based on available columns
            if has_metadata_column:
                log_query = """
                    INSERT INTO import_log
                    (filename, year, import_type, records_imported, records_skipped, status,
                     record_count, success_count, error_count, import_date, import_metadata)
                    VALUES
                    (:filename, :year, :import_type, :records_imported, :records_skipped, :status,
                     :record_count, :success_count, :error_count, :import_date, :import_metadata)
                """
                
                params = {
                    'filename': os.path.basename(file_path),
                    'year': levy_data.get_years()[0] if levy_data.get_years() else datetime.now().year,
                    'import_type': f"levy_{file_format.name.lower()}",
                    'records_imported': success_count,
                    'records_skipped': record_count - success_count,
                    'status': 'completed' if error_count == 0 else 'completed_with_errors',
                    'record_count': record_count,
                    'success_count': success_count,
                    'error_count': error_count,
                    'import_date': datetime.utcnow(),
                    'import_metadata': json.dumps(import_metadata)
                }
            else:
                # Fallback query without import_metadata column
                log_query = """
                    INSERT INTO import_log
                    (filename, year, import_type, records_imported, records_skipped, status,
                     record_count, success_count, error_count, import_date)
                    VALUES
                    (:filename, :year, :import_type, :records_imported, :records_skipped, :status,
                     :record_count, :success_count, :error_count, :import_date)
                """
                
                params = {
                    'filename': os.path.basename(file_path),
                    'year': levy_data.get_years()[0] if levy_data.get_years() else datetime.now().year,
                    'import_type': f"levy_{file_format.name.lower()}",
                    'records_imported': success_count,
                    'records_skipped': record_count - success_count,
                    'status': 'completed' if error_count == 0 else 'completed_with_errors',
                    'record_count': record_count,
                    'success_count': success_count,
                    'error_count': error_count,
                    'import_date': datetime.utcnow()
                }
            
            # Execute the query with appropriate parameters
            db.session.execute(text(log_query), params)
            db.session.commit()
            logger.info(f"Created import log entry")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating import log: {str(e)}")
            logger.exception(e)  # Log the full stack trace
        
        logger.info(f"Import completed: {success_count} successes, {error_count} errors out of {record_count} records")
        return True, record_count, success_count, error_count
    except Exception as e:
        logger.error(f"Error parsing file: {str(e)}")
        return False, 0, 0, 0

def find_sample_files():
    """Find all sample levy export files in the attached_assets directory."""
    sample_files = []
    for ext in ['txt', 'xls', 'xlsx', 'csv', 'xml', 'json']:
        pattern = f'attached_assets/*.{ext}'
        sample_files.extend(glob.glob(pattern))
    return sample_files

if __name__ == "__main__":
    # Import additional modules
    import glob
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Import levy data from various file formats')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--file', '-f', type=str, help=f'File path to import (default: {DEFAULT_SAMPLE_FILE_PATH})')
    parser.add_argument('--year', '-Y', type=int, help='Override the year in the file')
    parser.add_argument('--sample', '-s', action='store_true', help='Use sample files in attached_assets folder')
    parser.add_argument('--all-samples', '-a', action='store_true', help='Import all sample files in attached_assets folder')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Parse the file but don\'t import to database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output during import')
    args = parser.parse_args()
    
    # Create the Flask app and context
    app = create_app()
    
    with app.app_context():
        files_to_import = []
        
        # Determine which files to import
        if args.all_samples:
            files_to_import = find_sample_files()
            logger.info(f"Found {len(files_to_import)} sample files to import")
        elif args.sample:
            # Find the best sample file (prioritize formats with more data)
            sample_files = find_sample_files()
            if sample_files:
                # Prefer xlsx/xls over other formats if available
                for ext in ['.xlsx', '.xls', '.xml', '.csv', '.txt']:
                    for file in sample_files:
                        if file.endswith(ext):
                            files_to_import = [file]
                            break
                    if files_to_import:
                        break
                
                # If no preferred format found, use the first sample file
                if not files_to_import:
                    files_to_import = [sample_files[0]]
                
                logger.info(f"Selected sample file: {files_to_import[0]}")
            else:
                logger.error("No sample files found in attached_assets directory")
                sys.exit(1)
        elif args.file:
            if os.path.exists(args.file):
                files_to_import = [args.file]
            else:
                logger.error(f"File not found: {args.file}")
                sys.exit(1)
        else:
            # Use default file
            if os.path.exists(DEFAULT_SAMPLE_FILE_PATH):
                files_to_import = [DEFAULT_SAMPLE_FILE_PATH]
            else:
                logger.error(f"Default sample file not found: {DEFAULT_SAMPLE_FILE_PATH}")
                logger.info("Checking for other sample files...")
                
                sample_files = find_sample_files()
                if sample_files:
                    files_to_import = [sample_files[0]]
                    logger.info(f"Using alternate sample file: {files_to_import[0]}")
                else:
                    logger.error("No sample files found in attached_assets directory")
                    sys.exit(1)
        
        # Check if we have existing data
        if not args.dry_run:
            try:
                check_query = "SELECT COUNT(*) FROM tax_district"
                count = db.session.execute(text(check_query)).scalar()
                
                if count > 0 and not args.yes:
                    logger.warning(f"Found {count} existing tax district records in the database")
                    response = input("Do you want to proceed with importing data? [y/N]: ")
                    if response.lower() != 'y':
                        logger.info("Import cancelled")
                        sys.exit(0)
                elif count > 0 and args.yes:
                    logger.warning(f"Found {count} existing tax district records in the database, proceeding anyway (--yes flag)")
            except Exception as e:
                logger.warning(f"Error checking for existing data: {str(e)}")
        
        # Process each file
        total_records = 0
        total_success = 0
        total_errors = 0
        success_files = 0
        error_files = 0
        
        for file_path in files_to_import:
            logger.info(f"\nStarting import of file: {file_path}")
            
            # Import the data
            success, records, successes, errors = import_levy_data(
                file_path=file_path,
                year_override=args.year,
                dry_run=args.dry_run,
                verbose=args.verbose
            )
            
            total_records += records
            total_success += successes
            total_errors += errors
            
            if success:
                success_files += 1
                if args.dry_run:
                    logger.info(f"Dry run completed successfully for {file_path}")
                else:
                    logger.info(f"Import completed successfully for {file_path}")
            else:
                error_files += 1
                logger.error(f"Import failed for {file_path}")
        
        # Print summary if multiple files were imported
        if len(files_to_import) > 1:
            logger.info("\n" + "=" * 50)
            logger.info(f"Import Summary - Files: {len(files_to_import)}")
            logger.info(f"Successful Files: {success_files}")
            logger.info(f"Failed Files: {error_files}")
            logger.info(f"Total Records Processed: {total_records}")
            logger.info(f"Total Records Successfully Imported: {total_success}")
            logger.info(f"Total Records Failed to Import: {total_errors}")
            logger.info("=" * 50)
        
        # Exit with appropriate status code
        if error_files > 0:
            sys.exit(1)
        else:
            sys.exit(0)