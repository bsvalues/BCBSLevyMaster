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
from datetime import datetime
import traceback
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_csv(file_path, table_name, mapping=None, year_override=None):
    """
    Import data from a CSV file directly into the database.
    
    Args:
        file_path: Path to the CSV file
        table_name: Target database table
        mapping: Dictionary mapping CSV columns to database columns
        year_override: Override the year value
    """
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not found")
        return False
    
    # Use current year if not specified
    if not year_override:
        year = datetime.now().year
    else:
        year = year_override
    
    # Verify the file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read the CSV file
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Check for header row
            sample = csvfile.read(2048)
            csvfile.seek(0)
            has_header = csv.Sniffer().has_header(sample)
            
            # Parse the CSV
            reader = csv.DictReader(csvfile) if has_header else csv.reader(csvfile)
            rows = list(reader)
            
            if not rows:
                logger.error("No data found in CSV file")
                return False
            
            logger.info(f"Read {len(rows)} rows from {file_path}")
            
            # Connect to the database
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Start a transaction
                with conn.begin():
                    # Process each row
                    success_count = 0
                    error_count = 0
                    skipped_count = 0
                    
                    for row_idx, row in enumerate(rows):
                        try:
                            # Handle the mapping of columns
                            if mapping and has_header:
                                data = {}
                                for db_col, csv_col in mapping.items():
                                    if csv_col in row:
                                        data[db_col] = row[csv_col]
                                    else:
                                        logger.warning(f"Column '{csv_col}' not found in CSV header")
                                
                                # Add standard fields if not in mapping
                                if 'year' not in data and 'year' not in mapping.values():
                                    data['year'] = year
                                
                                if 'created_at' not in data and 'created_at' not in mapping.values():
                                    data['created_at'] = datetime.now()
                                
                                if 'updated_at' not in data and 'updated_at' not in mapping.values():
                                    data['updated_at'] = datetime.now()
                            else:
                                # For non-header CSVs or when no mapping is provided,
                                # just use the row as-is
                                data = row
                            
                            # Check if record already exists based on unique identifiers
                            if isinstance(data, dict) and 'property_id' in data:
                                check_year = data.get('year')
                                
                                if check_year:
                                    # For properties with year, check by property_id and year
                                    check_sql = f"SELECT COUNT(*) FROM {table_name} WHERE property_id = :property_id AND year = :year"
                                    check_params = {"property_id": data['property_id'], "year": check_year}
                                else:
                                    # Otherwise just check by property_id
                                    check_sql = f"SELECT COUNT(*) FROM {table_name} WHERE property_id = :property_id"
                                    check_params = {"property_id": data['property_id']}
                                    
                                result = conn.execute(text(check_sql), check_params)
                                if result.scalar() > 0:
                                    year_str = f" for year {check_year}" if check_year else ""
                                    logger.info(f"Record with property_id={data['property_id']}{year_str} already exists, skipping")
                                    skipped_count += 1
                                    continue
                            
                            # Generate the SQL statement
                            if isinstance(data, dict):
                                columns = ', '.join(data.keys())
                                placeholders = ', '.join(f":{col}" for col in data.keys())
                                sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                                conn.execute(text(sql), data)
                            else:
                                placeholders = ', '.join('?' for _ in data)
                                sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                                conn.execute(text(sql), data)
                            
                            success_count += 1
                            
                            # Log progress
                            if (row_idx + 1) % 100 == 0:
                                logger.info(f"Processed {row_idx + 1} rows...")
                        
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Error on row {row_idx + 1}: {str(e)}")
                            logger.debug(traceback.format_exc())
                    
                    logger.info(f"Import complete: {success_count} succeeded, {skipped_count} skipped, {error_count} failed")
                    return success_count > 0 or skipped_count > 0
    
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(description='Import data from CSV file to database')
    parser.add_argument('--file', '-f', required=True, help='CSV file path')
    parser.add_argument('--table', '-t', required=True, help='Target database table')
    parser.add_argument('--mapping', '-m', help='JSON mapping of CSV columns to database columns')
    parser.add_argument('--year', '-y', type=int, help='Year override')
    
    args = parser.parse_args()
    
    # Parse the mapping if provided
    mapping = None
    if args.mapping:
        import json
        try:
            mapping = json.loads(args.mapping)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON mapping: {args.mapping}")
            return 1
    
    success = import_csv(args.file, args.table, mapping, args.year)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())