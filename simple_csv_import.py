#!/usr/bin/env python
"""
Simple CSV Import Script

This script provides a lightweight way to import a CSV file directly into the database
without going through the full import process. It uses SQLAlchemy to directly insert records.
"""

import os
import sys
import csv
import logging
import argparse
import traceback
from datetime import datetime
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_csv(file_path, year_override=None):
    """
    Import data from a CSV file directly into the database.
    
    Args:
        file_path: Path to the CSV file
        year_override: Override the year value
    """
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not found")
        return False

    # Connect to the database
    try:
        engine = create_engine(db_url)
        conn = engine.connect()
        # Start a transaction that we can manage
        trans = conn.begin()
        logger.info("Connected to database successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return False

    try:
        # Read CSV file
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Print fieldnames for debugging
            logger.info(f"CSV field names: {reader.fieldnames}")
            
            # Track stats
            records_count = 0
            success_count = 0
            error_count = 0
            
            # Process each row
            for row in reader:
                records_count += 1
                
                # Get values, with fallbacks for missing fields
                tax_district_id = row.get('tax_district_id', '')
                levy_cd = row.get('levy_cd', tax_district_id)
                levy_cd_linked = row.get('levy_cd_linked', '')
                
                # Try to parse numeric fields
                try:
                    levy_rate = float(row.get('levy_rate', 0)) if row.get('levy_rate') else None
                except (ValueError, TypeError):
                    levy_rate = None
                
                try:
                    levy_amount = float(row.get('levy_amount', 0)) if row.get('levy_amount') else None
                except (ValueError, TypeError):
                    levy_amount = None
                
                # Use provided year, or try to get from CSV, or use current year
                if year_override:
                    year = year_override
                else:
                    try:
                        year = int(row.get('year', datetime.now().year))
                    except (ValueError, TypeError):
                        year = datetime.now().year
                
                # Skip if no tax_district_id or levy_cd
                if not tax_district_id and not levy_cd:
                    logger.warning(f"Skipping row {records_count}: Missing tax_district_id and levy_cd")
                    error_count += 1
                    continue
                
                # If we have levy_cd but no tax_district_id, use levy_cd
                if not tax_district_id and levy_cd:
                    tax_district_id = levy_cd
                
                # If we have tax_district_id but no levy_cd, use tax_district_id
                if tax_district_id and not levy_cd:
                    levy_cd = tax_district_id
                
                # Print row for debugging
                logger.debug(f"Processing row: {row}")
                
                try:
                    # Check if record already exists
                    result = conn.execute(
                        text("SELECT id FROM tax_district WHERE tax_district_id = :district_id AND year = :year"),
                        {"district_id": tax_district_id, "year": year}
                    )
                    existing_id = result.scalar()
                    
                    if existing_id:
                        # Update existing record
                        conn.execute(
                            text("""
                                UPDATE tax_district 
                                SET levy_code = :levy_cd, 
                                    linked_levy_code = :levy_cd_linked,
                                    updated_at = NOW()
                                WHERE id = :id
                            """),
                            {
                                "levy_cd": levy_cd,
                                "levy_cd_linked": levy_cd_linked,
                                "id": existing_id
                            }
                        )
                        logger.info(f"Updated tax district: {tax_district_id}")
                    else:
                        # Insert new record with DEFAULT for id to use the sequence
                        conn.execute(
                            text("""
                                INSERT INTO tax_district 
                                (id, year, district_name, district_code, is_active, created_at, updated_at, tax_district_id, levy_code, linked_levy_code) 
                                VALUES 
                                (DEFAULT, :year, :name, :code, TRUE, NOW(), NOW(), :district_id, :levy_cd, :levy_cd_linked)
                            """),
                            {
                                "year": year,
                                "name": f"District {tax_district_id}",
                                "code": levy_cd,
                                "district_id": tax_district_id,
                                "levy_cd": levy_cd,
                                "levy_cd_linked": levy_cd_linked
                            }
                        )
                        logger.info(f"Inserted new tax district: {tax_district_id}")
                    
                    # Now add/update the tax code entry if levy_rate is provided
                    if levy_rate is not None:
                        # Check if tax code exists
                        result = conn.execute(
                            text("SELECT id FROM tax_code WHERE code = :code AND year = :year"),
                            {"code": levy_cd, "year": year}
                        )
                        existing_code_id = result.scalar()
                        
                        if existing_code_id:
                            # Update existing tax code
                            conn.execute(
                                text("""
                                    UPDATE tax_code 
                                    SET levy_rate = :rate, 
                                        levy_amount = :amount,
                                        updated_at = NOW()
                                    WHERE id = :id
                                """),
                                {
                                    "rate": levy_rate,
                                    "amount": levy_amount,
                                    "id": existing_code_id
                                }
                            )
                            logger.info(f"Updated tax code: {levy_cd}")
                        else:
                            # Insert new tax code
                            district_result = conn.execute(
                                text("SELECT id FROM tax_district WHERE tax_district_id = :district_id AND year = :year"),
                                {"district_id": tax_district_id, "year": year}
                            )
                            district_id = district_result.scalar()
                            
                            if district_id:
                                conn.execute(
                                    text("""
                                        INSERT INTO tax_code 
                                        (id, code, year, district_id, levy_rate, levy_amount, is_active, created_at, updated_at) 
                                        VALUES 
                                        (DEFAULT, :code, :year, :district_id, :rate, :amount, TRUE, NOW(), NOW())
                                    """),
                                    {
                                        "code": levy_cd,
                                        "year": year,
                                        "district_id": district_id,
                                        "rate": levy_rate,
                                        "amount": levy_amount
                                    }
                                )
                                logger.info(f"Inserted new tax code: {levy_cd}")
                    
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error processing row {records_count}: {str(e)}")
                    error_count += 1
            
            # Create import log entry
            try:
                conn.execute(
                    text("""
                        INSERT INTO import_log 
                        (id, import_type, filename, status, record_count, success_count, error_count, import_date, metadata, year) 
                        VALUES 
                        (DEFAULT, 'csv', :filename, 'completed', :records, :success, :errors, NOW(), :metadata, :year)
                    """),
                    {
                        "filename": os.path.basename(file_path),
                        "records": records_count,
                        "success": success_count,
                        "errors": error_count,
                        "metadata": '{"source": "simple_csv_import.py"}',
                        "year": year_override or datetime.now().year
                    }
                )
                logger.info("Created import log entry")
            except Exception as e:
                logger.error(f"Error creating import log: {str(e)}")
            
            logger.info(f"Import completed: {success_count} successes, {error_count} errors out of {records_count} records")
            return True
    
    except Exception as e:
        logger.error(f"Error importing CSV file: {str(e)}")
        logger.error(traceback.format_exc())
        # Rollback the transaction on error
        try:
            trans.rollback()
            logger.info("Transaction rolled back due to error")
        except Exception as rollback_err:
            logger.error(f"Error rolling back transaction: {str(rollback_err)}")
        return False
    else:
        # If we got here without exceptions, commit the transaction
        try:
            trans.commit()
            logger.info("Transaction committed successfully")
        except Exception as commit_err:
            logger.error(f"Error committing transaction: {str(commit_err)}")
            return False
    
    finally:
        conn.close()
        logger.info("Database connection closed")

def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(description='Import CSV data directly into the database')
    parser.add_argument('--file', '-f', required=True, help='Path to the CSV file')
    parser.add_argument('--year', '-y', type=int, help='Override the year value')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        logger.error(f"File not found: {args.file}")
        return 1
    
    success = import_csv(args.file, args.year)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())