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
        
        # Map column names to expected names based on the sample file
        column_mapping = {
            # Standard format
            'tax_district_id': 'tax_district_id',
            'year': 'year',
            'levy_code': 'levy_code',
            'linked_levy_code': 'linked_levy_code',
            
            # Format from the provided sample file
            'levy_cd': 'levy_code',
            'levy_cd_linked': 'linked_levy_code'
        }
        
        # Rename columns to match expected format
        df = df.rename(columns=column_mapping)
        
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
        
        # First check if this is an Excel XML format
        workbook_namespace = '{urn:schemas-microsoft-com:office:spreadsheet}'
        if 'Workbook' in root.tag or root.find(f'.//{workbook_namespace}Worksheet') is not None:
            # This looks like an Excel XML file, so handle it appropriately
            return import_excel_xml_file(root, namespace)
            
        # Try to find tax district elements in a standard XML format
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
            'warnings': [f"Error importing XML file: {str(e)}"]
        }

def import_excel_xml_file(root, namespace=''):
    """
    Import data from an Excel XML file format.
    
    Args:
        root: The XML root element
        namespace: XML namespace prefix
        
    Returns:
        Dict containing import results
    """
    imported_count = 0
    skipped_count = 0
    warnings = []
    
    try:
        # Excel XML namespace
        ss_namespace = '{urn:schemas-microsoft-com:office:spreadsheet}'
        
        # Look for worksheets
        worksheet_found = False
        for worksheet in root.findall(f'.//{ss_namespace}Worksheet') or root.findall('.//Worksheet'):
            worksheet_found = True
            worksheet_name = worksheet.get(f'{ss_namespace}Name', '') or worksheet.get('Name', '')
            
            # Skip if this doesn't look like the right worksheet (we're looking for levy data)
            if not ('levy' in worksheet_name.lower() or 'district' in worksheet_name.lower()):
                continue
            
            # Get table element
            table = worksheet.find(f'.//{ss_namespace}Table') or worksheet.find('.//Table')
            if table is None:
                warnings.append(f"No table found in worksheet {worksheet_name}")
                continue
            
            # Get all rows
            rows = table.findall(f'.//{ss_namespace}Row') or table.findall('.//Row')
            if not rows:
                warnings.append(f"No rows found in worksheet {worksheet_name}")
                continue
            
            # Extract header row to get column indices
            header_row = rows[0]
            header_cells = header_row.findall(f'.//{ss_namespace}Cell') or header_row.findall('.//Cell')
            
            # Extract column headers
            headers = []
            for cell in header_cells:
                data_elem = cell.find(f'.//{ss_namespace}Data') or cell.find('.//Data')
                if data_elem is not None and data_elem.text:
                    headers.append(data_elem.text.strip())
                else:
                    headers.append(None)
            
            # Map column names to indices
            column_indices = {}
            column_mapping = {
                'tax_district_id': ['tax_district_id', 'district_id'],
                'year': ['year'],
                'levy_code': ['levy_code', 'levy_cd'],
                'linked_levy_code': ['linked_levy_code', 'levy_cd_linked']
            }
            
            for actual_name, possible_names in column_mapping.items():
                for possible_name in possible_names:
                    if possible_name in headers:
                        column_indices[actual_name] = headers.index(possible_name)
                        break
            
            # Check if we have all required columns
            required_columns = ['tax_district_id', 'year', 'levy_code', 'linked_levy_code']
            missing_columns = [col for col in required_columns if col not in column_indices]
            
            if missing_columns:
                warnings.append(f"Missing required columns in worksheet {worksheet_name}: {', '.join(missing_columns)}")
                continue
            
            # Process data rows (skip header)
            for row_idx, row in enumerate(rows[1:], 1):
                try:
                    cells = row.findall(f'.//{ss_namespace}Cell') or row.findall('.//Cell')
                    
                    # Initialize row data
                    row_data = {
                        'tax_district_id': None,
                        'year': None,
                        'levy_code': None,
                        'linked_levy_code': None
                    }
                    
                    # Extract cell data
                    for col_name, col_idx in column_indices.items():
                        if col_idx < len(cells):
                            cell = cells[col_idx]
                            data_elem = cell.find(f'.//{ss_namespace}Data') or cell.find('.//Data')
                            if data_elem is not None and data_elem.text:
                                row_data[col_name] = data_elem.text.strip()
                    
                    # Validate and convert data types
                    try:
                        district_id = int(row_data['tax_district_id'])
                        year = int(row_data['year'])
                        levy_code = str(row_data['levy_code']).strip() if row_data['levy_code'] else None
                        linked_levy_code = str(row_data['linked_levy_code']).strip() if row_data['linked_levy_code'] else None
                    except (ValueError, TypeError) as e:
                        skipped_count += 1
                        warnings.append(f"Error in row {row_idx+1}: Invalid data type - {str(e)}")
                        continue
                    
                    # Skip rows with missing required data
                    if not all([district_id, year, levy_code, linked_levy_code]):
                        skipped_count += 1
                        warnings.append(f"Skipped row {row_idx+1} due to missing required values")
                        continue
                    
                    # Check if record already exists
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
                    warnings.append(f"Error processing row {row_idx+1}: {str(e)}")
            
        if not worksheet_found:
            warnings.append("No worksheets found in Excel XML file")
        
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
            'warnings': [f"Error processing Excel XML file: {str(e)}"]
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