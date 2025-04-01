import os
import pandas as pd
import xml.etree.ElementTree as ET
import openpyxl
import xlrd
from datetime import datetime
from app import db
from models import TaxDistrict
from sqlalchemy import and_

def import_district_text_file(file_path):
    """
    Import tax district data from a tab-delimited text file.
    
    Args:
        file_path: Path to the tab-delimited text file
        
    Returns:
        Dict containing import results
    """
    try:
        # Determine the file format (TXT files are often tab-delimited)
        df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        
        # Basic validation of required columns
        required_columns = ['tax_district_id', 'year', 'levy_code', 'linked_levy_code']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'warnings': [f"Missing required columns: {', '.join(missing_columns)}"]
            }
        
        # Store results
        imported_count = 0
        skipped_count = 0
        warnings = []
        
        # Process each row
        for _, row in df.iterrows():
            try:
                # Check if a record with the same key already exists
                existing_record = TaxDistrict.query.filter(
                    and_(
                        TaxDistrict.tax_district_id == row['tax_district_id'],
                        TaxDistrict.year == row['year'],
                        TaxDistrict.levy_code == row['levy_code'],
                        TaxDistrict.linked_levy_code == row['linked_levy_code']
                    )
                ).first()
                
                if existing_record:
                    skipped_count += 1
                    continue
                
                # Create a new district record
                district = TaxDistrict(
                    tax_district_id=row['tax_district_id'],
                    year=row['year'],
                    levy_code=row['levy_code'],
                    linked_levy_code=row['linked_levy_code']
                )
                
                db.session.add(district)
                imported_count += 1
                
            except Exception as e:
                skipped_count += 1
                warnings.append(f"Error processing row {_}: {str(e)}")
        
        # Commit changes
        db.session.commit()
        
        return {
            'success': len(warnings) == 0,
            'imported': imported_count,
            'skipped': skipped_count,
            'warnings': warnings
        }
        
    except Exception as e:
        return {
            'success': False,
            'imported': 0,
            'skipped': 0,
            'warnings': [f"Error importing file: {str(e)}"]
        }

def import_district_xml_file(file_path):
    """
    Import tax district data from an XML file.
    
    Args:
        file_path: Path to the XML file
        
    Returns:
        Dict containing import results
    """
    try:
        # Parse the XML file
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract the namespace if it exists
        namespace = ''
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0] + '}'
        
        # Store results
        imported_count = 0
        skipped_count = 0
        warnings = []
        
        # Look for district elements
        district_elements = root.findall(f'.//{namespace}TaxDistrict') or root.findall('.//*[contains(local-name(), "District")]')
        
        if not district_elements:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'warnings': ["No district elements found in XML file"]
            }
        
        # Process each district
        for district_elem in district_elements:
            try:
                # Extract district attributes
                district_id = None
                year = datetime.now().year  # Default to current year if not specified
                levy_code = None
                linked_levy_code = None
                
                # Extract ID
                id_elem = district_elem.find(f'./{namespace}DistrictID') or district_elem.find('.//*[contains(local-name(), "ID")]')
                if id_elem is not None and id_elem.text:
                    district_id = int(id_elem.text.strip())
                
                # Extract year
                year_elem = district_elem.find(f'./{namespace}Year') or district_elem.find('.//*[contains(local-name(), "Year")]')
                if year_elem is not None and year_elem.text:
                    year = int(year_elem.text.strip())
                
                # Extract levy code
                levy_code_elem = district_elem.find(f'./{namespace}LevyCode') or district_elem.find('.//*[contains(local-name(), "LevyCode")]')
                if levy_code_elem is not None and levy_code_elem.text:
                    levy_code = levy_code_elem.text.strip()
                
                # Extract linked levy code
                linked_levy_code_elem = district_elem.find(f'./{namespace}LinkedLevyCode') or district_elem.find('.//*[contains(local-name(), "LinkedCode")]')
                if linked_levy_code_elem is not None and linked_levy_code_elem.text:
                    linked_levy_code = linked_levy_code_elem.text.strip()
                
                # Validate required fields
                if not all([district_id, year, levy_code, linked_levy_code]):
                    skipped_count += 1
                    missing_fields = []
                    if not district_id: missing_fields.append('DistrictID')
                    if not levy_code: missing_fields.append('LevyCode')
                    if not linked_levy_code: missing_fields.append('LinkedLevyCode')
                    warnings.append(f"Skipped district with missing fields: {', '.join(missing_fields)}")
                    continue
                
                # Check for existing record
                existing_record = TaxDistrict.query.filter(
                    and_(
                        TaxDistrict.tax_district_id == district_id,
                        TaxDistrict.year == year,
                        TaxDistrict.levy_code == levy_code,
                        TaxDistrict.linked_levy_code == linked_levy_code
                    )
                ).first()
                
                if existing_record:
                    skipped_count += 1
                    continue
                
                # Create a new district record
                district = TaxDistrict(
                    tax_district_id=district_id,
                    year=year,
                    levy_code=levy_code,
                    linked_levy_code=linked_levy_code
                )
                
                db.session.add(district)
                imported_count += 1
                
            except Exception as e:
                skipped_count += 1
                warnings.append(f"Error processing district: {str(e)}")
        
        # Commit changes
        db.session.commit()
        
        return {
            'success': len(warnings) == 0,
            'imported': imported_count,
            'skipped': skipped_count,
            'warnings': warnings
        }
        
    except Exception as e:
        return {
            'success': False,
            'imported': 0,
            'skipped': 0,
            'warnings': [f"Error importing XML file: {str(e)}"]
        }

def import_district_excel_file(file_path):
    """
    Import tax district data from an Excel file (.xls or .xlsx).
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        Dict containing import results
    """
    try:
        # Determine file extension and read accordingly
        if file_path.lower().endswith('.xlsx'):
            # Use pandas with openpyxl engine for .xlsx files
            df = pd.read_excel(file_path, engine='openpyxl')
        elif file_path.lower().endswith('.xls'):
            # Use pandas with xlrd engine for .xls files
            df = pd.read_excel(file_path, engine='xlrd')
        else:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'warnings': ["Unsupported Excel file format. Only .xls and .xlsx are supported."]
            }
        
        # Check if the DataFrame is empty
        if df.empty:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'warnings': ["No district data found in Excel file."]
            }
        
        # Map column names to expected names
        column_mapping = {
            # Standard format
            'tax_district_id': 'tax_district_id',
            'year': 'year',
            'levy_code': 'levy_code',
            'linked_levy_code': 'linked_levy_code',
            
            # Alternative format from provided Excel files
            'levy_cd': 'levy_code',
            'levy_cd_linked': 'linked_levy_code'
        }
        
        # Rename columns to match expected format
        df = df.rename(columns=column_mapping)
        
        # Check for required columns after mapping
        required_columns = ['tax_district_id', 'year', 'levy_code', 'linked_levy_code']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'warnings': [f"Missing required columns after mapping: {', '.join(missing_columns)}"]
            }
        
        # Store results
        imported_count = 0
        skipped_count = 0
        warnings = []
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Validate data types and convert if needed
                try:
                    district_id = int(row['tax_district_id'])
                    year = int(row['year'])
                    levy_code = str(row['levy_code']).strip()
                    linked_levy_code = str(row['linked_levy_code']).strip()
                except (ValueError, TypeError) as e:
                    skipped_count += 1
                    warnings.append(f"Error in row {index+2}: Invalid data type - {str(e)}")
                    continue
                
                # Skip rows with empty values in any required field
                if pd.isna(district_id) or pd.isna(year) or not levy_code or not linked_levy_code:
                    skipped_count += 1
                    warnings.append(f"Skipped row {index+2} due to missing required values")
                    continue
                
                # Check if a record with the same key already exists
                existing_record = TaxDistrict.query.filter(
                    and_(
                        TaxDistrict.tax_district_id == district_id,
                        TaxDistrict.year == year,
                        TaxDistrict.levy_code == levy_code,
                        TaxDistrict.linked_levy_code == linked_levy_code
                    )
                ).first()
                
                if existing_record:
                    skipped_count += 1
                    continue
                
                # Create a new district record
                district = TaxDistrict(
                    tax_district_id=district_id,
                    year=year,
                    levy_code=levy_code,
                    linked_levy_code=linked_levy_code
                )
                
                db.session.add(district)
                imported_count += 1
                
            except Exception as e:
                skipped_count += 1
                warnings.append(f"Error processing row {index+2}: {str(e)}")
        
        # Commit changes
        db.session.commit()
        
        return {
            'success': imported_count > 0,
            'imported': imported_count,
            'skipped': skipped_count,
            'warnings': warnings
        }
        
    except Exception as e:
        return {
            'success': False,
            'imported': 0,
            'skipped': 0,
            'warnings': [f"Error importing Excel file: {str(e)}"]
        }

def get_linked_levy_codes(levy_code, year=None):
    """
    Get all levy codes linked to the specified levy code for a given year.
    If year is not specified, use the most recent year.
    
    Args:
        levy_code: The levy code to find links for
        year: The year to search in (optional)
        
    Returns:
        List of linked levy codes
    """
    if not year:
        # Get the most recent year
        max_year = db.session.query(db.func.max(TaxDistrict.year)).scalar()
        year = max_year if max_year else datetime.now().year
    
    # Find all districts that contain this levy code
    districts = TaxDistrict.query.filter(
        and_(
            TaxDistrict.levy_code == levy_code,
            TaxDistrict.year == year
        )
    ).all()
    
    # Extract unique linked levy codes
    linked_codes = set()
    for district in districts:
        linked_codes.add(district.linked_levy_code)
    
    # If there are no direct links, check if this code is a linked code itself
    if not linked_codes:
        reverse_districts = TaxDistrict.query.filter(
            and_(
                TaxDistrict.linked_levy_code == levy_code,
                TaxDistrict.year == year
            )
        ).all()
        
        for district in reverse_districts:
            linked_codes.add(district.levy_code)
    
    return sorted(list(linked_codes))