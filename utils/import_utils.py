"""
Utility functions for importing data into the Levy Calculation System.

This module provides functions to:
- Detect file types
- Read data from various file formats (CSV, XLS, XLSX, XML, JSON)
- Process and validate imported data
- Map data to database models
"""

import os
import json
import logging
import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from werkzeug.datastructures import FileStorage
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import (
    TaxDistrict, TaxCode, Property, ImportLog, 
    PropertyType, ImportType, TaxCodeHistoricalRate
)


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Class to store results of an import operation."""
    total_count: int = 0
    success_count: int = 0
    error_count: int = 0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def detect_file_type(filename: str) -> str:
    """
    Detect the file type from the filename extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        File type as a string (csv, excel, xml, json)
    """
    lower_filename = filename.lower()
    
    if lower_filename.endswith('.csv'):
        return 'csv'
    elif lower_filename.endswith('.xls'):
        return 'excel'
    elif lower_filename.endswith('.xlsx'):
        return 'excel'
    elif lower_filename.endswith('.xml'):
        return 'xml'
    elif lower_filename.endswith('.json'):
        return 'json'
    elif lower_filename.endswith('.txt'):
        # Attempt to detect format from content
        return 'text'
    else:
        return None


def read_data_from_file(file_path: str, file_type: str) -> List[Dict[str, Any]]:
    """
    Read data from a file into a list of dictionaries.
    
    Args:
        file_path: Path to the file
        file_type: Type of file (csv, excel, xml, json)
        
    Returns:
        List of dictionaries containing the data
    """
    if file_type == 'csv':
        df = pd.read_csv(file_path)
        return df.to_dict('records')
    
    elif file_type == 'excel':
        df = pd.read_excel(file_path)
        return df.to_dict('records')
    
    elif file_type == 'xml':
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract data from XML based on expected structure
            data = []
            
            # Attempt to determine structure based on root element
            if root.tag.lower() in ('taxdistricts', 'districts'):
                # Process districts
                for district in root.findall('./district'):
                    district_data = {}
                    for child in district:
                        district_data[child.tag.lower()] = child.text
                    data.append(district_data)
                    
            elif root.tag.lower() in ('taxcodes', 'codes'):
                # Process tax codes
                for code in root.findall('./code'):
                    code_data = {}
                    for child in code:
                        code_data[child.tag.lower()] = child.text
                    data.append(code_data)
                    
            elif root.tag.lower() in ('properties', 'parcels'):
                # Process properties/parcels
                for prop in root.findall('./property') or root.findall('./parcel'):
                    prop_data = {}
                    for child in prop:
                        prop_data[child.tag.lower()] = child.text
                    data.append(prop_data)
            
            # If no specific structure detected, try generic approach
            if not data:
                for child in root:
                    item = {}
                    for subchild in child:
                        item[subchild.tag.lower()] = subchild.text
                    data.append(item)
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing XML: {str(e)}")
            raise ValueError(f"Could not parse XML file: {str(e)}")
    
    elif file_type == 'json':
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Ensure we have a list of dictionaries
        if isinstance(data, dict):
            # If the JSON is a dictionary, it might be a wrapper with a data array
            for key in data:
                if isinstance(data[key], list):
                    return data[key]
            # Otherwise, return a list with the single dict
            return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("JSON file must contain a dictionary or a list")
    
    elif file_type == 'text':
        # Try to detect format from content and parse accordingly
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check if it might be pipe-delimited
        if '|' in content.split('\n')[0]:
            df = pd.read_csv(file_path, sep='|')
            return df.to_dict('records')
        
        # Check if it might be tab-delimited
        elif '\t' in content.split('\n')[0]:
            df = pd.read_csv(file_path, sep='\t')
            return df.to_dict('records')
        
        # Fall back to comma-delimited
        else:
            df = pd.read_csv(file_path)
            return df.to_dict('records')
    
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def validate_data_rows(data: List[Dict[str, Any]], import_type: ImportType) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate data rows for the specified import type.
    
    Args:
        data: List of dictionaries containing the data
        import_type: Type of import (TAX_DISTRICT, TAX_CODE, etc.)
        
    Returns:
        Tuple of (valid_data, warnings)
    """
    valid_data = []
    warnings = []
    
    if not data:
        warnings.append("No data rows found in the import file")
        return valid_data, warnings
    
    for i, row in enumerate(data):
        row_num = i + 1
        row_valid = True
        
        # Check for empty or None values in required fields
        if import_type == ImportType.TAX_DISTRICT:
            if not row.get('code'):
                warnings.append(f"Row {row_num}: Missing district code")
                row_valid = False
            if not row.get('name'):
                warnings.append(f"Row {row_num}: Missing district name")
                row_valid = False
            if not row.get('district_type'):
                warnings.append(f"Row {row_num}: Missing district type")
                row_valid = False
        
        elif import_type == ImportType.TAX_CODE:
            if not row.get('code'):
                warnings.append(f"Row {row_num}: Missing tax code")
                row_valid = False
            if not row.get('year'):
                warnings.append(f"Row {row_num}: Missing year")
                row_valid = False
        
        elif import_type == ImportType.PROPERTY:
            if not row.get('parcel_id'):
                warnings.append(f"Row {row_num}: Missing parcel ID")
                row_valid = False
            if not row.get('tax_code') and not row.get('tax_code_id'):
                warnings.append(f"Row {row_num}: Missing tax code reference")
                row_valid = False
            if not row.get('year'):
                warnings.append(f"Row {row_num}: Missing year")
                row_valid = False
        
        # Add the row to valid data if it passed all checks
        if row_valid:
            valid_data.append(row)
    
    return valid_data, warnings


def validate_import_metadata(data: List[Dict[str, Any]], import_type: ImportType) -> List[str]:
    """
    Validate overall metadata for the import.
    
    Args:
        data: List of dictionaries containing the data
        import_type: Type of import
        
    Returns:
        List of warning messages
    """
    warnings = []
    
    # Check for expected columns based on import type
    if data:
        first_row = data[0]
        
        if import_type == ImportType.TAX_DISTRICT:
            expected_columns = {'code', 'name', 'district_type'}
            found_columns = set(first_row.keys())
            missing = expected_columns - found_columns
            if missing:
                warnings.append(f"Expected columns not found: {', '.join(missing)}")
        
        elif import_type == ImportType.TAX_CODE:
            expected_columns = {'code', 'year'}
            found_columns = set(first_row.keys())
            missing = expected_columns - found_columns
            if missing:
                warnings.append(f"Expected columns not found: {', '.join(missing)}")
        
        elif import_type == ImportType.PROPERTY:
            expected_columns = {'parcel_id', 'year'}
            found_columns = set(first_row.keys())
            missing = expected_columns - found_columns
            if missing:
                warnings.append(f"Expected columns not found: {', '.join(missing)}")
    
    return warnings


def process_import(data: List[Dict[str, Any]], import_type: ImportType, year: int) -> ImportResult:
    """
    Process imported data based on the import type.
    
    Args:
        data: List of dictionaries containing the data
        import_type: Type of import
        year: Year for the import
        
    Returns:
        ImportResult object with import statistics
    """
    result = ImportResult(total_count=len(data))
    
    # Validate data
    metadata_warnings = validate_import_metadata(data, import_type)
    valid_data, row_warnings = validate_data_rows(data, import_type)
    
    result.warnings = metadata_warnings + row_warnings
    
    # Process based on import type
    try:
        if import_type == ImportType.TAX_DISTRICT:
            process_tax_district_import(valid_data, result)
            
        elif import_type == ImportType.TAX_CODE:
            process_tax_code_import(valid_data, result, year)
            
        elif import_type == ImportType.PROPERTY:
            process_property_import(valid_data, result, year)
            
        elif import_type == ImportType.LEVY_RATE:
            process_levy_rate_import(valid_data, result, year)
            
        elif import_type == ImportType.ASSESSED_VALUE:
            process_assessed_value_import(valid_data, result, year)
            
        else:
            result.warnings.append(f"Unsupported import type: {import_type.name}")
    
    except SQLAlchemyError as e:
        logger.error(f"Database error during import: {str(e)}")
        db.session.rollback()
        result.warnings.append(f"Database error: {str(e)}")
        result.error_count = len(valid_data)
        
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
        db.session.rollback()
        result.warnings.append(f"Error: {str(e)}")
        result.error_count = len(valid_data)
    
    return result


def process_tax_district_import(data: List[Dict[str, Any]], result: ImportResult) -> None:
    """
    Process tax district import data.
    
    Args:
        data: Validated data rows
        result: ImportResult to update with progress
    """
    for row in data:
        try:
            # Check if district already exists
            existing = TaxDistrict.query.filter_by(code=row.get('code')).first()
            
            if existing:
                # Update existing record
                existing.name = row.get('name', existing.name)
                existing.district_type = row.get('district_type', existing.district_type)
                existing.description = row.get('description', existing.description)
                existing.county = row.get('county', existing.county)
                existing.state = row.get('state', existing.state)
                existing.statutory_limit = float(row.get('statutory_limit')) if row.get('statutory_limit') else existing.statutory_limit
                existing.is_active = bool(int(row.get('is_active', 1))) if row.get('is_active') is not None else existing.is_active
                existing.updated_at = datetime.utcnow()
                
                result.warnings.append(f"Updated existing district: {row.get('code')}")
            else:
                # Create new record
                district = TaxDistrict(
                    name=row.get('name'),
                    code=row.get('code'),
                    district_type=row.get('district_type'),
                    description=row.get('description'),
                    county=row.get('county', 'Benton'),
                    state=row.get('state', 'WA'),
                    statutory_limit=float(row.get('statutory_limit')) if row.get('statutory_limit') else None,
                    is_active=bool(int(row.get('is_active', 1))) if row.get('is_active') is not None else True
                )
                db.session.add(district)
            
            result.success_count += 1
            
        except Exception as e:
            logger.error(f"Error processing district {row.get('code')}: {str(e)}")
            result.warnings.append(f"Error processing district {row.get('code')}: {str(e)}")
            result.error_count += 1
    
    db.session.commit()


def process_tax_code_import(data: List[Dict[str, Any]], result: ImportResult, year: int) -> None:
    """
    Process tax code import data.
    
    Args:
        data: Validated data rows
        result: ImportResult to update with progress
        year: Year for the import
    """
    for row in data:
        try:
            # Use the provided year or fall back to the row's year
            row_year = int(row.get('year', year))
            
            # Check if tax code already exists for this year
            existing = TaxCode.query.filter_by(code=row.get('code'), year=row_year).first()
            
            if existing:
                # Update existing record
                existing.description = row.get('description', existing.description)
                existing.county = row.get('county', existing.county)
                existing.state = row.get('state', existing.state)
                existing.total_levy_rate = float(row.get('total_levy_rate')) if row.get('total_levy_rate') else existing.total_levy_rate
                existing.total_assessed_value = float(row.get('total_assessed_value')) if row.get('total_assessed_value') else existing.total_assessed_value
                existing.is_active = bool(int(row.get('is_active', 1))) if row.get('is_active') is not None else existing.is_active
                existing.updated_at = datetime.utcnow()
                
                # Handle districts if provided
                if row.get('districts') or row.get('district_codes'):
                    district_codes = row.get('districts', row.get('district_codes', ''))
                    if isinstance(district_codes, str):
                        district_codes = [d.strip() for d in district_codes.split(',')]
                    
                    # Find districts by code
                    districts = TaxDistrict.query.filter(TaxDistrict.code.in_(district_codes)).all()
                    
                    # Replace existing districts with new set
                    existing.tax_districts = districts
                
                result.warnings.append(f"Updated existing tax code: {row.get('code')} ({row_year})")
            else:
                # Create new record
                tax_code = TaxCode(
                    code=row.get('code'),
                    description=row.get('description'),
                    county=row.get('county', 'Benton'),
                    state=row.get('state', 'WA'),
                    year=row_year,
                    total_levy_rate=float(row.get('total_levy_rate')) if row.get('total_levy_rate') else None,
                    total_assessed_value=float(row.get('total_assessed_value')) if row.get('total_assessed_value') else None,
                    is_active=bool(int(row.get('is_active', 1))) if row.get('is_active') is not None else True
                )
                
                # Handle districts if provided
                if row.get('districts') or row.get('district_codes'):
                    district_codes = row.get('districts', row.get('district_codes', ''))
                    if isinstance(district_codes, str):
                        district_codes = [d.strip() for d in district_codes.split(',')]
                    
                    # Find districts by code
                    districts = TaxDistrict.query.filter(TaxDistrict.code.in_(district_codes)).all()
                    tax_code.tax_districts = districts
                
                db.session.add(tax_code)
            
            result.success_count += 1
            
        except Exception as e:
            logger.error(f"Error processing tax code {row.get('code')}: {str(e)}")
            result.warnings.append(f"Error processing tax code {row.get('code')}: {str(e)}")
            result.error_count += 1
    
    db.session.commit()


def process_property_import(data: List[Dict[str, Any]], result: ImportResult, year: int) -> None:
    """
    Process property import data.
    
    Args:
        data: Validated data rows
        result: ImportResult to update with progress
        year: Year for the import
    """
    for row in data:
        try:
            # Use the provided year or fall back to the row's year
            row_year = int(row.get('year', year))
            
            # Find the tax code
            tax_code = None
            if row.get('tax_code_id'):
                tax_code = TaxCode.query.get(int(row.get('tax_code_id')))
            elif row.get('tax_code'):
                tax_code = TaxCode.query.filter_by(code=row.get('tax_code'), year=row_year).first()
            
            if not tax_code:
                result.warnings.append(f"Tax code not found for property {row.get('parcel_id')}")
                result.error_count += 1
                continue
            
            # Determine property type
            property_type_str = row.get('property_type', 'residential').lower()
            try:
                property_type = PropertyType(property_type_str)
            except ValueError:
                property_type = PropertyType.OTHER
                result.warnings.append(f"Unknown property type '{property_type_str}' for {row.get('parcel_id')}, using OTHER")
            
            # Check if property already exists for this year
            existing = Property.query.filter_by(parcel_id=row.get('parcel_id'), year=row_year).first()
            
            if existing:
                # Update existing record
                existing.address = row.get('address', existing.address)
                existing.city = row.get('city', existing.city)
                existing.county = row.get('county', existing.county)
                existing.state = row.get('state', existing.state)
                existing.zip_code = row.get('zip_code', existing.zip_code)
                existing.property_type = property_type
                existing.tax_code_id = tax_code.id
                existing.assessed_value = float(row.get('assessed_value')) if row.get('assessed_value') else existing.assessed_value
                existing.land_value = float(row.get('land_value')) if row.get('land_value') else existing.land_value
                existing.improvement_value = float(row.get('improvement_value')) if row.get('improvement_value') else existing.improvement_value
                existing.square_footage = float(row.get('square_footage')) if row.get('square_footage') else existing.square_footage
                existing.longitude = float(row.get('longitude')) if row.get('longitude') else existing.longitude
                existing.latitude = float(row.get('latitude')) if row.get('latitude') else existing.latitude
                existing.updated_at = datetime.utcnow()
                
                result.warnings.append(f"Updated existing property: {row.get('parcel_id')} ({row_year})")
            else:
                # Create new record
                property = Property(
                    parcel_id=row.get('parcel_id'),
                    address=row.get('address'),
                    city=row.get('city'),
                    county=row.get('county', 'Benton'),
                    state=row.get('state', 'WA'),
                    zip_code=row.get('zip_code'),
                    property_type=property_type,
                    tax_code_id=tax_code.id,
                    assessed_value=float(row.get('assessed_value')) if row.get('assessed_value') else None,
                    year=row_year,
                    land_value=float(row.get('land_value')) if row.get('land_value') else None,
                    improvement_value=float(row.get('improvement_value')) if row.get('improvement_value') else None,
                    square_footage=float(row.get('square_footage')) if row.get('square_footage') else None,
                    longitude=float(row.get('longitude')) if row.get('longitude') else None,
                    latitude=float(row.get('latitude')) if row.get('latitude') else None
                )
                
                db.session.add(property)
            
            result.success_count += 1
            
        except Exception as e:
            logger.error(f"Error processing property {row.get('parcel_id')}: {str(e)}")
            result.warnings.append(f"Error processing property {row.get('parcel_id')}: {str(e)}")
            result.error_count += 1
    
    db.session.commit()


def process_levy_rate_import(data: List[Dict[str, Any]], result: ImportResult, year: int) -> None:
    """
    Process levy rate import data.
    
    Args:
        data: Validated data rows
        result: ImportResult to update with progress
        year: Year for the import
    """
    for row in data:
        try:
            # Use the provided year or fall back to the row's year
            row_year = int(row.get('year', year))
            
            # Find the tax code and district
            tax_code = None
            tax_district = None
            
            if row.get('tax_code_id'):
                tax_code = TaxCode.query.get(int(row.get('tax_code_id')))
            elif row.get('tax_code'):
                tax_code = TaxCode.query.filter_by(code=row.get('tax_code'), year=row_year).first()
            
            if row.get('tax_district_id'):
                tax_district = TaxDistrict.query.get(int(row.get('tax_district_id')))
            elif row.get('tax_district') or row.get('district_code'):
                district_code = row.get('tax_district', row.get('district_code'))
                tax_district = TaxDistrict.query.filter_by(code=district_code).first()
            
            if not tax_code:
                result.warnings.append(f"Tax code not found for levy rate record")
                result.error_count += 1
                continue
                
            if not tax_district:
                result.warnings.append(f"Tax district not found for levy rate record")
                result.error_count += 1
                continue
            
            # Ensure the district is associated with the tax code
            if tax_district not in tax_code.tax_districts:
                tax_code.tax_districts.append(tax_district)
            
            # Check if historical rate already exists
            existing = TaxCodeHistoricalRate.query.filter_by(
                tax_code_id=tax_code.id,
                tax_district_id=tax_district.id,
                year=row_year
            ).first()
            
            if existing:
                # Update existing record
                existing.levy_rate = float(row.get('levy_rate')) if row.get('levy_rate') else existing.levy_rate
                existing.levy_amount = float(row.get('levy_amount')) if row.get('levy_amount') else existing.levy_amount
                existing.assessed_value = float(row.get('assessed_value')) if row.get('assessed_value') else existing.assessed_value
                existing.updated_at = datetime.utcnow()
                
                result.warnings.append(f"Updated existing levy rate for {tax_code.code} - {tax_district.code} ({row_year})")
            else:
                # Create new record
                historical_rate = TaxCodeHistoricalRate(
                    tax_code_id=tax_code.id,
                    tax_district_id=tax_district.id,
                    year=row_year,
                    levy_rate=float(row.get('levy_rate')),
                    levy_amount=float(row.get('levy_amount')) if row.get('levy_amount') else None,
                    assessed_value=float(row.get('assessed_value')) if row.get('assessed_value') else None
                )
                
                db.session.add(historical_rate)
            
            result.success_count += 1
            
        except Exception as e:
            logger.error(f"Error processing levy rate: {str(e)}")
            result.warnings.append(f"Error processing levy rate: {str(e)}")
            result.error_count += 1
    
    # Update totals for affected tax codes
    affected_tax_codes = set()
    for row in data:
        try:
            row_year = int(row.get('year', year))
            
            if row.get('tax_code_id'):
                tax_code = TaxCode.query.get(int(row.get('tax_code_id')))
            elif row.get('tax_code'):
                tax_code = TaxCode.query.filter_by(code=row.get('tax_code'), year=row_year).first()
            
            if tax_code:
                affected_tax_codes.add(tax_code.id)
        except Exception:
            continue
    
    # Update totals
    for tax_code_id in affected_tax_codes:
        tax_code = TaxCode.query.get(tax_code_id)
        if tax_code:
            # Sum up the levy rates for this tax code and year
            levy_rates = TaxCodeHistoricalRate.query.filter_by(
                tax_code_id=tax_code.id,
                year=tax_code.year
            ).all()
            
            total_levy_rate = sum(r.levy_rate for r in levy_rates if r.levy_rate is not None)
            tax_code.total_levy_rate = total_levy_rate
            
            # Sum up the assessed values if available
            if all(r.assessed_value is not None for r in levy_rates):
                # If all rates have the same assessed value (should be the case), use that
                tax_code.total_assessed_value = levy_rates[0].assessed_value if levy_rates else None
    
    db.session.commit()


def process_assessed_value_import(data: List[Dict[str, Any]], result: ImportResult, year: int) -> None:
    """
    Process assessed value import data.
    
    Args:
        data: Validated data rows
        result: ImportResult to update with progress
        year: Year for the import
    """
    for row in data:
        try:
            # Use the provided year or fall back to the row's year
            row_year = int(row.get('year', year))
            
            # Find the tax code
            tax_code = None
            if row.get('tax_code_id'):
                tax_code = TaxCode.query.get(int(row.get('tax_code_id')))
            elif row.get('tax_code'):
                tax_code = TaxCode.query.filter_by(code=row.get('tax_code'), year=row_year).first()
            
            if not tax_code:
                result.warnings.append(f"Tax code not found for assessed value record")
                result.error_count += 1
                continue
            
            # Update the tax code's assessed value
            if row.get('assessed_value'):
                tax_code.total_assessed_value = float(row.get('assessed_value'))
                
                # Also update all historical rates for this tax code/year
                historical_rates = TaxCodeHistoricalRate.query.filter_by(
                    tax_code_id=tax_code.id,
                    year=row_year
                ).all()
                
                for rate in historical_rates:
                    rate.assessed_value = tax_code.total_assessed_value
                
                result.warnings.append(f"Updated assessed value for {tax_code.code} ({row_year})")
                result.success_count += 1
            else:
                result.warnings.append(f"No assessed value provided for {tax_code.code}")
                result.error_count += 1
            
        except Exception as e:
            logger.error(f"Error processing assessed value: {str(e)}")
            result.warnings.append(f"Error processing assessed value: {str(e)}")
            result.error_count += 1
    
    db.session.commit()