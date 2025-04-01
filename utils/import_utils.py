"""
Import Utilities

This module provides functionality for importing data from various file formats
into the application, with validation and error handling.

Features:
- Import from Excel, CSV, and other file formats
- Validate imported data
- Generate import logs and reports
- Handle errors and warnings
- Track imported data through the ImportLog model
"""

import os
import csv
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union
from io import StringIO, BytesIO
from werkzeug.datastructures import FileStorage

from app import db
from models import Property, TaxCode, TaxDistrict, ImportLog
from utils.validation_framework import (
    ValidationError, create_property_validator, create_tax_code_validator,
    create_tax_district_validator, create_import_validator
)


logger = logging.getLogger(__name__)


class ImportResult:
    """Class to hold the result of an import operation."""
    
    def __init__(self):
        self.success = True
        self.imported_count = 0
        self.skipped_count = 0
        self.error_messages = []
        self.warning_messages = []
        self.import_log_id = None  # Will be set to int when log is created
    
    def add_error(self, message: str):
        """Add an error message and mark import as failed."""
        self.success = False
        self.error_messages.append(message)
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warning_messages.append(message)
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the result as a dictionary."""
        return {
            'success': self.success,
            'imported_count': self.imported_count,
            'skipped_count': self.skipped_count,
            'errors': self.error_messages,
            'warnings': self.warning_messages,
            'import_log_id': self.import_log_id
        }


def detect_file_type(file: FileStorage) -> str:
    """
    Detect the type of file based on extension and content.
    
    Args:
        file: The uploaded file
        
    Returns:
        str: The detected file type (csv, excel, text)
        
    Raises:
        ValueError: If file type is not supported
    """
    filename = file.filename.lower()
    
    if filename.endswith('.csv'):
        return 'csv'
    elif filename.endswith(('.xls', '.xlsx')):
        return 'excel'
    elif filename.endswith('.txt'):
        return 'text'
    elif filename.endswith('.xml'):
        return 'xml'
    else:
        raise ValueError(f"Unsupported file type: {filename}")


def read_data_from_file(file: FileStorage) -> Tuple[List[Dict[str, Any]], str]:
    """
    Read data from a file into a list of dictionaries.
    
    Args:
        file: The uploaded file
        
    Returns:
        Tuple: (list of data dictionaries, file_type)
        
    Raises:
        ValueError: If file cannot be read
    """
    file_type = detect_file_type(file)
    data = []
    
    try:
        if file_type == 'csv':
            # Read CSV file
            stream = StringIO(file.read().decode('utf-8'))
            reader = csv.DictReader(stream)
            data = [row for row in reader]
            
        elif file_type == 'excel':
            # Read Excel file
            stream = BytesIO(file.read())
            df = pd.read_excel(stream)
            data = df.to_dict('records')
            
        elif file_type == 'text':
            # Read text file with tab or pipe delimiter
            stream = StringIO(file.read().decode('utf-8'))
            sample = stream.read(1024)
            stream.seek(0)
            
            # Detect delimiter
            if '\t' in sample:
                delimiter = '\t'
            elif '|' in sample:
                delimiter = '|'
            else:
                delimiter = ','
                
            reader = csv.DictReader(stream, delimiter=delimiter)
            data = [row for row in reader]
            
        elif file_type == 'xml':
            # Read XML file - this would need a more complex parser
            # depending on the XML structure
            # For now, just raise a not implemented error
            raise NotImplementedError("XML import is not implemented yet")
            
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise ValueError(f"Could not read file: {str(e)}")
    
    return data, file_type


def validate_import_metadata(filename: str, data: List[Dict[str, Any]], import_type: str) -> None:
    """
    Validate the import metadata.
    
    Args:
        filename: The name of the imported file
        data: The data to be imported
        import_type: The type of data being imported
        
    Raises:
        ValidationError: If validation fails
    """
    # Get column names from first row
    columns = list(data[0].keys()) if data else []
    
    # Create metadata object
    metadata = {
        "filename": filename,
        "row_count": len(data),
        "columns": columns,
        "data_type": import_type
    }
    
    # Validate metadata
    validator = create_import_validator()
    validator.validate(metadata)


def validate_data_rows(data: List[Dict[str, Any]], import_type: str, strict: bool = False) -> Union[List[Dict[str, Any]], bool]:
    """
    Validate all data rows.
    
    Args:
        data: The data to validate
        import_type: The type of data being imported
        strict: If True, raises an error on first validation failure
        
    Returns:
        List: List of validation errors
        
    Raises:
        ValidationError: If validation fails and strict=True
    """
    # Choose validator based on import type
    if import_type == 'property':
        validator = create_property_validator()
    elif import_type == 'tax_code':
        validator = create_tax_code_validator()
    elif import_type == 'tax_district':
        validator = create_tax_district_validator()
    else:
        raise ValueError(f"Unsupported import type: {import_type}")
    
    # Validate all rows
    return validator.validate_collection(data, strict=strict)


def import_property_data(data: List[Dict[str, Any]], result: ImportResult) -> None:
    """
    Import property data into the database.
    
    Args:
        data: The property data to import
        result: The ImportResult object to update
    """
    for idx, row in enumerate(data):
        try:
            # Convert keys to lowercase and trim whitespace
            row = {k.lower().strip(): v for k, v in row.items()}
            
            # Check for required fields
            property_id = row.get('property_id', row.get('pin', row.get('parcel_id')))
            assessed_value = row.get('assessed_value', row.get('value'))
            tax_code = row.get('tax_code', row.get('code'))
            
            if not all([property_id, assessed_value, tax_code]):
                result.add_warning(f"Row {idx+1}: Missing required fields")
                result.skipped_count += 1
                continue
                
            # Convert to appropriate types
            try:
                assessed_value = float(assessed_value)
            except (ValueError, TypeError):
                result.add_warning(f"Row {idx+1}: Invalid assessed value: {assessed_value}")
                result.skipped_count += 1
                continue
                
            # Check if property already exists
            existing = Property.query.filter_by(property_id=property_id).first()
            
            if existing:
                # Update existing property
                existing.assessed_value = assessed_value
                existing.tax_code = tax_code
                existing.updated_at = datetime.utcnow()
            else:
                # Create new property
                new_property = Property(
                    property_id=property_id,
                    assessed_value=assessed_value,
                    tax_code=tax_code
                )
                db.session.add(new_property)
            
            result.imported_count += 1
                
        except Exception as e:
            result.add_warning(f"Row {idx+1}: Error processing row: {str(e)}")
            result.skipped_count += 1
            continue
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        result.add_error(f"Database error: {str(e)}")


def import_tax_code_data(data: List[Dict[str, Any]], result: ImportResult) -> None:
    """
    Import tax code data into the database.
    
    Args:
        data: The tax code data to import
        result: The ImportResult object to update
    """
    for idx, row in enumerate(data):
        try:
            # Convert keys to lowercase and trim whitespace
            row = {k.lower().strip(): v for k, v in row.items()}
            
            # Check for required fields
            code = row.get('code', row.get('tax_code'))
            levy_rate = row.get('levy_rate', row.get('rate'))
            
            if not all([code, levy_rate]):
                result.add_warning(f"Row {idx+1}: Missing required fields")
                result.skipped_count += 1
                continue
                
            # Convert to appropriate types
            try:
                levy_rate = float(levy_rate)
                levy_amount = row.get('levy_amount')
                if levy_amount:
                    levy_amount = float(levy_amount)
                    
                total_assessed_value = row.get('total_assessed_value', row.get('assessed_value'))
                if total_assessed_value:
                    total_assessed_value = float(total_assessed_value)
                    
                previous_year_rate = row.get('previous_year_rate')
                if previous_year_rate:
                    previous_year_rate = float(previous_year_rate)
            except (ValueError, TypeError) as e:
                result.add_warning(f"Row {idx+1}: Invalid numeric value: {str(e)}")
                result.skipped_count += 1
                continue
                
            # Check if tax code already exists
            existing = TaxCode.query.filter_by(code=code).first()
            
            if existing:
                # Update existing tax code
                existing.levy_rate = levy_rate
                if levy_amount:
                    existing.levy_amount = levy_amount
                if total_assessed_value:
                    existing.total_assessed_value = total_assessed_value
                if previous_year_rate:
                    existing.previous_year_rate = previous_year_rate
                existing.updated_at = datetime.utcnow()
            else:
                # Create new tax code
                new_tax_code = TaxCode(
                    code=code,
                    levy_rate=levy_rate,
                    levy_amount=levy_amount,
                    total_assessed_value=total_assessed_value,
                    previous_year_rate=previous_year_rate
                )
                db.session.add(new_tax_code)
            
            result.imported_count += 1
                
        except Exception as e:
            result.add_warning(f"Row {idx+1}: Error processing row: {str(e)}")
            result.skipped_count += 1
            continue
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        result.add_error(f"Database error: {str(e)}")


def import_tax_district_data(data: List[Dict[str, Any]], result: ImportResult) -> None:
    """
    Import tax district data into the database.
    
    Args:
        data: The tax district data to import
        result: The ImportResult object to update
    """
    for idx, row in enumerate(data):
        try:
            # Convert keys to lowercase and trim whitespace
            row = {k.lower().strip(): v for k, v in row.items()}
            
            # Check for required fields
            tax_district_id = row.get('tax_district_id', row.get('district_id'))
            year = row.get('year', datetime.now().year)  # Default to current year if not specified
            levy_code = row.get('levy_code', row.get('code'))
            linked_levy_code = row.get('linked_levy_code', row.get('linked_code'))
            
            if not all([tax_district_id, levy_code, linked_levy_code]):
                result.add_warning(f"Row {idx+1}: Missing required fields")
                result.skipped_count += 1
                continue
                
            # Convert to appropriate types
            try:
                tax_district_id = int(tax_district_id)
                year = int(year)
            except (ValueError, TypeError) as e:
                result.add_warning(f"Row {idx+1}: Invalid numeric value: {str(e)}")
                result.skipped_count += 1
                continue
                
            # Check if tax district relationship already exists
            existing = TaxDistrict.query.filter_by(
                tax_district_id=tax_district_id,
                year=year,
                levy_code=levy_code,
                linked_levy_code=linked_levy_code
            ).first()
            
            if existing:
                # Update existing tax district relationship
                existing.updated_at = datetime.utcnow()
            else:
                # Create new tax district relationship
                new_tax_district = TaxDistrict(
                    tax_district_id=tax_district_id,
                    year=year,
                    levy_code=levy_code,
                    linked_levy_code=linked_levy_code
                )
                db.session.add(new_tax_district)
            
            result.imported_count += 1
                
        except Exception as e:
            result.add_warning(f"Row {idx+1}: Error processing row: {str(e)}")
            result.skipped_count += 1
            continue
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        result.add_error(f"Database error: {str(e)}")


def create_import_log(filename: str, import_type: str, result: ImportResult) -> Optional[int]:
    """
    Create an import log entry.
    
    Args:
        filename: The name of the imported file
        import_type: The type of data imported
        result: The ImportResult object
        
    Returns:
        int: The ID of the created import log
    """
    # Create warnings text
    warnings_text = None
    if result.warning_messages:
        warnings_text = "\n".join(result.warning_messages)
    
    # Create import log
    import_log = ImportLog(
        filename=filename,
        rows_imported=result.imported_count,
        rows_skipped=result.skipped_count,
        warnings=warnings_text,
        import_type=import_type
    )
    
    db.session.add(import_log)
    
    try:
        db.session.commit()
        return import_log.id
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating import log: {str(e)}")
        return None


def process_import(
    file: FileStorage, 
    import_type: str, 
    validate_only: bool = False
) -> ImportResult:
    """
    Process an import from a file.
    
    Args:
        file: The uploaded file
        import_type: The type of data to import (property, tax_code, tax_district)
        validate_only: If True, only validates data without importing
        
    Returns:
        ImportResult: The result of the import
    """
    result = ImportResult()
    
    try:
        # Read data from file
        data, file_type = read_data_from_file(file)
        
        if not data:
            result.add_error("No data found in file")
            return result
            
        # Validate import metadata
        try:
            validate_import_metadata(file.filename, data, import_type)
        except ValidationError as e:
            result.add_error(f"Import metadata validation failed: {str(e)}")
            return result
            
        # Validate data rows
        validation_result = validate_data_rows(data, import_type, strict=False)
        
        # Check if we have validation errors (not a boolean True)
        if validation_result and not isinstance(validation_result, bool):
            # We have a list of validation errors
            validation_errors = validation_result
            
            # Add validation errors as warnings
            for error in validation_errors:
                result.add_warning(f"Row {error.get('row', '?')}: {error.get('error')}")
                result.skipped_count += 1
            
            # Filter out invalid rows
            valid_indices = [i for i, d in enumerate(data) if i not in [e.get('row') for e in validation_errors]]
            data = [data[i] for i in valid_indices]
        
        # If validation only, don't import
        if validate_only:
            result.imported_count = len(data)
            return result
            
        # Import data based on type
        if import_type == 'property':
            import_property_data(data, result)
        elif import_type == 'tax_code':
            import_tax_code_data(data, result)
        elif import_type == 'tax_district':
            import_tax_district_data(data, result)
        else:
            result.add_error(f"Unsupported import type: {import_type}")
            return result
            
        # Create import log
        if result.success:
            log_id = create_import_log(file.filename, import_type, result)
            result.import_log_id = log_id
            
    except Exception as e:
        logger.error(f"Import error: {str(e)}")
        result.add_error(f"Import failed: {str(e)}")
        
    return result