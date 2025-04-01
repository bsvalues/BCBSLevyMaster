#!/usr/bin/env python3
"""
Seed the database with sample data for testing and development.
"""

import os
import csv
import pandas as pd
from datetime import datetime
from app import app, db
from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog
from utils.district_utils import import_district_text_file

def seed_properties():
    """Import sample property data from CSV."""
    property_count = Property.query.count()
    if property_count > 0:
        print(f"Database already has {property_count} properties. Skipping property seed.")
        return
    
    csv_path = os.path.join('static', 'sample_property_data.csv')
    
    if not os.path.exists(csv_path):
        print(f"Sample property data not found at {csv_path}")
        return
    
    imported = 0
    skipped = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Check if property already exists
                existing = Property.query.filter_by(property_id=row['property_id']).first()
                if existing:
                    skipped += 1
                    continue
                
                # Create new property
                prop = Property(
                    property_id=row['property_id'],
                    assessed_value=float(row['assessed_value']),
                    tax_code=row['tax_code']
                )
                db.session.add(prop)
                imported += 1
            except Exception as e:
                print(f"Error importing property {row.get('property_id')}: {str(e)}")
                skipped += 1
    
    # Commit changes
    db.session.commit()
    
    # Log the import
    import_log = ImportLog(
        filename='sample_property_data.csv',
        rows_imported=imported,
        rows_skipped=skipped,
        import_type='property'
    )
    db.session.add(import_log)
    db.session.commit()
    
    print(f"Imported {imported} properties, skipped {skipped}")

def seed_tax_codes():
    """Import sample tax code data from CSV."""
    tax_code_count = TaxCode.query.count()
    if tax_code_count > 0:
        print(f"Database already has {tax_code_count} tax codes. Skipping tax code seed.")
        return
    
    csv_path = os.path.join('static', 'sample_tax_codes.csv')
    
    if not os.path.exists(csv_path):
        print(f"Sample tax code data not found at {csv_path}")
        return
    
    imported = 0
    skipped = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Check if tax code already exists
                existing = TaxCode.query.filter_by(code=row['code']).first()
                if existing:
                    skipped += 1
                    continue
                
                # Create new tax code
                tax_code = TaxCode(
                    code=row['code'],
                    levy_amount=float(row['levy_amount']),
                    levy_rate=float(row['levy_rate']),
                    previous_year_rate=float(row['previous_year_rate']),
                    total_assessed_value=float(row['total_assessed_value'])
                )
                db.session.add(tax_code)
                imported += 1
            except Exception as e:
                print(f"Error importing tax code {row.get('code')}: {str(e)}")
                skipped += 1
    
    # Commit changes
    db.session.commit()
    print(f"Imported {imported} tax codes, skipped {skipped}")

def seed_tax_districts():
    """Import sample tax district data from the provided text file."""
    district_count = TaxDistrict.query.count()
    if district_count > 0:
        print(f"Database already has {district_count} tax districts. Skipping district seed.")
        return
    
    txt_path = os.path.join('attached_assets', 'Levy Expot.txt')
    
    if not os.path.exists(txt_path):
        print(f"Sample district data not found at {txt_path}")
        return
    
    # Use the existing import function
    result = import_district_text_file(txt_path)
    
    if result['success']:
        print(f"Imported {result['imported']} tax districts, skipped {result['skipped']}")
    else:
        print(f"Failed to import tax districts: {result['warnings']}")

def seed_export_log():
    """Create a sample export log entry."""
    export_count = ExportLog.query.count()
    if export_count > 0:
        print(f"Database already has {export_count} export logs. Skipping export log seed.")
        return
    
    export_log = ExportLog(
        filename='sample_tax_roll_20250401.csv',
        rows_exported=12,
        export_date=datetime.utcnow()
    )
    db.session.add(export_log)
    db.session.commit()
    print("Added sample export log")

if __name__ == '__main__':
    with app.app_context():
        print("Starting database seed...")
        seed_properties()
        seed_tax_codes()
        seed_tax_districts()
        seed_export_log()
        print("Database seed completed.")