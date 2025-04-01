"""
Utility functions for importing data from various file formats.
"""

import os
import csv
import io
import json
import logging
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
from werkzeug.datastructures import FileStorage
from sqlalchemy.exc import SQLAlchemyError

from app2 import db
from models import Property, TaxCode, TaxDistrict, ImportLog

# Configure logger
logger = logging.getLogger(__name__)

@dataclass
class ImportResult:
    """Data class to track results of an import operation."""
    success: bool = True
    message: str = ''
    records_imported: int = 0
    records_skipped: int = 0
    error_messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error_message: str) -> None:
        """Add an error message to the result."""
        self.error_messages.append(error_message)
        
    def add_warning(self, warning_message: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning_message)
        
    def as_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'success': self.success,
            'message': self.message,
            'records_imported': self.records_imported,
            'records_skipped': self.records_skipped,
            'error_messages': self.error_messages,
            'warnings': self.warnings
        }

def process_file_import(file: FileStorage, import_type: str) -> ImportResult:
    """
    Process file import for different data types.
    
    Args:
        file: Uploaded file object
        import_type: Type of import ('property', 'district', etc.)
        
    Returns:
        ImportResult object with import statistics and messages
    """
    if not file or not file.filename:
        return ImportResult(
            success=False,
            message="No file provided"
        )
    
    # Get file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    try:
        # Process different file formats
        if file_ext == '.csv':
            df = pd.read_csv(file.stream)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file.stream)
        elif file_ext == '.json':
            df = pd.read_json(file.stream)
        elif file_ext == '.xml':
            df = pd.read_xml(file.stream)
        elif file_ext == '.txt':
            # Try to determine delimiter
            file.stream.seek(0)
            sample = file.stream.read(4096).decode('utf-8')
            file.stream.seek(0)
            
            if '\t' in sample:
                df = pd.read_csv(file.stream, delimiter='\t')
            elif ',' in sample:
                df = pd.read_csv(file.stream, delimiter=',')
            elif ';' in sample:
                df = pd.read_csv(file.stream, delimiter=';')
            else:
                df = pd.read_csv(file.stream, delimiter=None, engine='python')
        else:
            return ImportResult(
                success=False,
                message=f"Unsupported file format: {file_ext}"
            )
            
        # Clean up column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Process based on import type
        if import_type == 'property':
            return import_property_data(df)
        elif import_type == 'district':
            return import_district_data(df)
        else:
            return ImportResult(
                success=False,
                message=f"Unknown import type: {import_type}"
            )
    
    except Exception as e:
        logger.error(f"Error processing {import_type} import: {str(e)}")
        return ImportResult(
            success=False,
            message=f"Error processing file: {str(e)}"
        )

def import_property_data(df: pd.DataFrame) -> ImportResult:
    """
    Import property data from DataFrame.
    
    Args:
        df: DataFrame containing property data
        
    Returns:
        ImportResult object with import statistics and messages
    """
    result = ImportResult()
    
    # Validate required columns
    required_columns = ['property_id', 'assessed_value', 'tax_code']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        result.success = False
        result.message = f"Missing required columns: {', '.join(missing_columns)}"
        return result
    
    # Additional validation for data types
    try:
        df['assessed_value'] = pd.to_numeric(df['assessed_value'], errors='coerce')
        if df['assessed_value'].isna().any():
            result.add_warning("Some assessed_value entries were not valid numbers and were set to null")
            
        # Get valid tax codes
        valid_tax_codes = set(tc.code for tc in TaxCode.query.all())
        invalid_tax_codes = set(df['tax_code'].unique()) - valid_tax_codes
        
        if invalid_tax_codes:
            # Create new tax codes for missing ones
            for code in invalid_tax_codes:
                if pd.isna(code) or code == '':
                    continue
                    
                new_tax_code = TaxCode(
                    code=str(code),
                    description=f"Auto-created from property import",
                    year=pd.to_datetime('now').year
                )
                db.session.add(new_tax_code)
            
            db.session.commit()
            result.add_warning(f"Created {len(invalid_tax_codes)} new tax codes: {', '.join(str(c) for c in invalid_tax_codes if not pd.isna(c) and c != '')}")
        
        # Add current year if not present
        if 'year' not in df.columns:
            df['year'] = pd.to_datetime('now').year
            result.add_warning("Year column not found, using current year")
            
        # Start import
        imported_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                # Check if property already exists
                property_id = str(row['property_id']).strip()
                year = int(row['year']) if 'year' in row else pd.to_datetime('now').year
                existing_property = Property.query.filter_by(property_id=property_id, year=year).first()
                
                if existing_property:
                    # Update existing property
                    existing_property.assessed_value = float(row['assessed_value']) if not pd.isna(row['assessed_value']) else None
                    existing_property.tax_code = str(row['tax_code']).strip()
                    
                    if 'address' in row and not pd.isna(row['address']):
                        existing_property.address = str(row['address']).strip()
                        
                    if 'owner_name' in row and not pd.isna(row['owner_name']):
                        existing_property.owner_name = str(row['owner_name']).strip()
                        
                    if 'property_type' in row and not pd.isna(row['property_type']):
                        existing_property.property_type = str(row['property_type']).strip()
                    
                    db.session.add(existing_property)
                    
                else:
                    # Create new property
                    new_property = Property(
                        property_id=property_id,
                        assessed_value=float(row['assessed_value']) if not pd.isna(row['assessed_value']) else 0,
                        tax_code=str(row['tax_code']).strip(),
                        year=year
                    )
                    
                    if 'address' in row and not pd.isna(row['address']):
                        new_property.address = str(row['address']).strip()
                        
                    if 'owner_name' in row and not pd.isna(row['owner_name']):
                        new_property.owner_name = str(row['owner_name']).strip()
                        
                    if 'property_type' in row and not pd.isna(row['property_type']):
                        new_property.property_type = str(row['property_type']).strip()
                        
                    db.session.add(new_property)
                
                imported_count += 1
                
                # Commit in batches to avoid memory issues
                if imported_count % 100 == 0:
                    db.session.commit()
                
            except Exception as e:
                logger.error(f"Error importing property {row.get('property_id', 'unknown')}: {str(e)}")
                result.add_error(f"Error importing property {row.get('property_id', 'unknown')}: {str(e)}")
                skipped_count += 1
        
        # Final commit
        db.session.commit()
        
        # Create import log entry
        import_log = ImportLog(
            filename=f"property_import_{pd.to_datetime('now').strftime('%Y%m%d_%H%M%S')}",
            import_type='property',
            records_imported=imported_count,
            records_skipped=skipped_count,
            status='completed' if imported_count > 0 else 'failed'
        )
        db.session.add(import_log)
        db.session.commit()
        
        result.records_imported = imported_count
        result.records_skipped = skipped_count
        
        if imported_count == 0 and skipped_count > 0:
            result.success = False
            result.message = "Import failed: No records were imported"
        elif imported_count > 0 and skipped_count > 0:
            result.message = f"Import completed with warnings: {imported_count} records imported, {skipped_count} records skipped"
        else:
            result.message = f"Import successful: {imported_count} records imported"
            
        return result
        
    except Exception as e:
        logger.error(f"Error in property import: {str(e)}")
        result.success = False
        result.message = f"Error during import: {str(e)}"
        return result

def import_district_data(df: pd.DataFrame) -> ImportResult:
    """
    Import tax district data from DataFrame.
    
    Args:
        df: DataFrame containing district data
        
    Returns:
        ImportResult object with import statistics and messages
    """
    result = ImportResult()
    
    # Validate required columns
    required_columns = ['tax_district_id', 'district_name', 'levy_code']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        result.success = False
        result.message = f"Missing required columns: {', '.join(missing_columns)}"
        return result
    
    # Additional validation and data preparation
    try:
        # Get valid tax codes
        valid_tax_codes = set(tc.code for tc in TaxCode.query.all())
        invalid_tax_codes = set(df['levy_code'].unique()) - valid_tax_codes
        
        if invalid_tax_codes:
            # Create new tax codes for missing ones
            for code in invalid_tax_codes:
                if pd.isna(code) or code == '':
                    continue
                    
                new_tax_code = TaxCode(
                    code=str(code),
                    description=f"Auto-created from district import",
                    year=pd.to_datetime('now').year
                )
                db.session.add(new_tax_code)
            
            db.session.commit()
            result.add_warning(f"Created {len(invalid_tax_codes)} new tax codes: {', '.join(str(c) for c in invalid_tax_codes if not pd.isna(c) and c != '')}")
        
        # Add current year if not present
        if 'year' not in df.columns:
            df['year'] = pd.to_datetime('now').year
            result.add_warning("Year column not found, using current year")
            
        # Start import
        imported_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                # Check if district already exists
                district_id = str(row['tax_district_id']).strip()
                year = int(row['year']) if 'year' in row else pd.to_datetime('now').year
                existing_district = TaxDistrict.query.filter_by(tax_district_id=district_id, year=year).first()
                
                if existing_district:
                    # Update existing district
                    existing_district.district_name = str(row['district_name']).strip()
                    existing_district.levy_code = str(row['levy_code']).strip()
                    
                    if 'statutory_limit' in row and not pd.isna(row['statutory_limit']):
                        existing_district.statutory_limit = float(row['statutory_limit'])
                    
                    db.session.add(existing_district)
                    
                else:
                    # Create new district
                    new_district = TaxDistrict(
                        tax_district_id=district_id,
                        district_name=str(row['district_name']).strip(),
                        levy_code=str(row['levy_code']).strip(),
                        year=year
                    )
                    
                    if 'statutory_limit' in row and not pd.isna(row['statutory_limit']):
                        new_district.statutory_limit = float(row['statutory_limit'])
                        
                    db.session.add(new_district)
                
                imported_count += 1
                
                # Commit in batches to avoid memory issues
                if imported_count % 100 == 0:
                    db.session.commit()
                
            except Exception as e:
                logger.error(f"Error importing district {row.get('tax_district_id', 'unknown')}: {str(e)}")
                result.add_error(f"Error importing district {row.get('tax_district_id', 'unknown')}: {str(e)}")
                skipped_count += 1
        
        # Final commit
        db.session.commit()
        
        # Create import log entry
        import_log = ImportLog(
            filename=f"district_import_{pd.to_datetime('now').strftime('%Y%m%d_%H%M%S')}",
            import_type='district',
            records_imported=imported_count,
            records_skipped=skipped_count,
            status='completed' if imported_count > 0 else 'failed'
        )
        db.session.add(import_log)
        db.session.commit()
        
        result.records_imported = imported_count
        result.records_skipped = skipped_count
        
        if imported_count == 0 and skipped_count > 0:
            result.success = False
            result.message = "Import failed: No records were imported"
        elif imported_count > 0 and skipped_count > 0:
            result.message = f"Import completed with warnings: {imported_count} records imported, {skipped_count} records skipped"
        else:
            result.message = f"Import successful: {imported_count} records imported"
            
        return result
        
    except Exception as e:
        logger.error(f"Error in district import: {str(e)}")
        result.success = False
        result.message = f"Error during import: {str(e)}"
        return result