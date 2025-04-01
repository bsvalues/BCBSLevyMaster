import csv
import pandas as pd
from io import StringIO
from sqlalchemy import func
from app import db
from models import Property, TaxCode

def validate_csv_columns(file_path):
    """
    Validate that the CSV file has all required columns.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Tuple of (is_valid, missing_columns)
    """
    required_columns = ['property_id', 'assessed_value', 'tax_code']
    
    with open(file_path, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader, None)
        
        if not headers:
            return False, ['File is empty or has no headers']
        
        # Convert headers to lowercase for case-insensitive comparison
        headers = [h.lower() for h in headers]
        
        missing_columns = [col for col in required_columns if col not in headers]
        
        return len(missing_columns) == 0, missing_columns

def validate_and_import_csv(file_path):
    """
    Validate and import data from a CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Dict containing import results
    """
    result = {
        'success': False,
        'imported': 0,
        'skipped': 0,
        'warnings': []
    }
    
    # Validate CSV columns
    is_valid, missing_columns = validate_csv_columns(file_path)
    
    if not is_valid:
        result['warnings'].append(f"Missing required columns: {', '.join(missing_columns)}")
        return result
    
    # Use pandas for efficient data processing
    try:
        df = pd.read_csv(file_path)
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Clean up the data
        df = df.dropna(subset=['property_id', 'assessed_value', 'tax_code'])
        
        # Convert property_id to string and other type validations
        df['property_id'] = df['property_id'].astype(str)
        
        try:
            df['assessed_value'] = pd.to_numeric(df['assessed_value'])
        except ValueError:
            result['warnings'].append("Some assessed values are not valid numbers. Non-numeric values will be skipped.")
            df = df[pd.to_numeric(df['assessed_value'], errors='coerce').notna()]
            df['assessed_value'] = pd.to_numeric(df['assessed_value'])
        
        df['tax_code'] = df['tax_code'].astype(str)
        
        # Get existing property_ids to avoid duplicates
        existing_property_ids = {p[0] for p in db.session.query(Property.property_id).all()}
        
        # Insert new properties
        new_properties = []
        skipped_count = 0
        
        for _, row in df.iterrows():
            if row['property_id'] in existing_property_ids:
                # Update existing property
                property_obj = Property.query.filter_by(property_id=row['property_id']).first()
                property_obj.assessed_value = row['assessed_value']
                property_obj.tax_code = row['tax_code']
                db.session.add(property_obj)
            else:
                # Create new property
                new_property = Property(
                    property_id=row['property_id'],
                    assessed_value=row['assessed_value'],
                    tax_code=row['tax_code']
                )
                new_properties.append(new_property)
                existing_property_ids.add(row['property_id'])
        
        # Bulk insert new properties
        if new_properties:
            db.session.bulk_save_objects(new_properties)
        
        # Update tax code aggregates
        update_tax_code_totals()
        
        # Commit changes
        db.session.commit()
        
        result['imported'] = len(new_properties) + (len(df) - len(new_properties) - skipped_count)
        result['skipped'] = skipped_count
        result['success'] = True
        
    except Exception as e:
        db.session.rollback()
        result['warnings'].append(f"Error importing data: {str(e)}")
    
    return result

def update_tax_code_totals():
    """
    Update the TaxCode table with aggregated assessed values.
    """
    # Get all unique tax codes with their total assessed value
    tax_code_totals = db.session.query(
        Property.tax_code, 
        func.sum(Property.assessed_value).label('total_assessed_value')
    ).group_by(Property.tax_code).all()
    
    # Update or create TaxCode entries
    for tax_code, total_assessed_value in tax_code_totals:
        tax_code_obj = TaxCode.query.filter_by(code=tax_code).first()
        
        if tax_code_obj:
            tax_code_obj.total_assessed_value = total_assessed_value
        else:
            tax_code_obj = TaxCode(
                code=tax_code,
                total_assessed_value=total_assessed_value
            )
        
        db.session.add(tax_code_obj)
