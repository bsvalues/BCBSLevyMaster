#!/usr/bin/env python
"""
Seed Properties Script

This script seeds the database with sample property data using the
simple_csv_import utility.
"""

import os
import sys
import json
import logging
from simple_csv_import import import_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def seed_properties(file_path='static/sample_property_data.csv', year=None):
    """
    Seed properties from a CSV file.
    
    Args:
        file_path: Path to the CSV file with property data
        year: Year to use for the properties
    """
    # Mapping from CSV columns to database columns
    mapping = {
        'property_id': 'property_id',
        'address': 'address',
        'tax_code': 'tax_code',
        'assessed_value': 'assessed_value',
        'property_type': 'property_type',
        'year': 'year',
        'owner_name': 'owner_name'
    }
    
    # Run the import
    return import_csv(file_path, 'property', mapping, year)

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed sample property data')
    parser.add_argument('--file', '-f', default='static/sample_property_data.csv', help='CSV file path')
    parser.add_argument('--year', '-y', type=int, help='Year override')
    
    args = parser.parse_args()
    
    success = seed_properties(args.file, args.year)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())