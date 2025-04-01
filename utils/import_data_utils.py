"""
Utility functions for importing data from various file formats.
"""
import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from app2 import db
from models import Property, TaxCode, TaxDistrict, ImportLog

class ImportResult:
    """Class to represent the result of an import operation."""
    
    def __init__(self):
        self.records_imported = 0
        self.records_skipped = 0
        self.errors = []
        self.warnings = []
        self.import_log_id = None
        self.status = 'completed'
    
    def add_error(self, error_msg):
        """Add an error message."""
        self.errors.append(error_msg)
        self.status = 'failed' if not self.records_imported else 'partial'
    
    def add_warning(self, warning_msg):
        """Add a warning message."""
        self.warnings.append(warning_msg)
    
    def log_import(self, filename, import_type):
        """Log the import operation to the database."""
        import_log = ImportLog(
            filename=filename,
            import_date=datetime.utcnow(),
            import_type=import_type,
            records_imported=self.records_imported,
            records_skipped=self.records_skipped,
            status=self.status,
            notes='\n'.join(self.errors + self.warnings)
        )
        db.session.add(import_log)
        db.session.commit()
        self.import_log_id = import_log.id
        return import_log

def allowed_file(filename, allowed_extensions):
    """Check if a file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_extension(filename):
    """Get the extension of a file."""
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()

def handle_property_import(file_storage, year=None):
    """
    Import property data from a file.
    
    Args:
        file_storage: FileStorage object from Flask's request.files
        year: Year for the imported data (defaults to current year)
        
    Returns:
        ImportResult object with import statistics
    """
    result = ImportResult()
    
    if not file_storage:
        result.add_error("No file provided")
        return result
    
    filename = secure_filename(file_storage.filename)
    extension = get_file_extension(filename)
    
    if year is None:
        year = datetime.now().year
    
    # Save the file temporarily
    temp_path = os.path.join('/tmp', filename)
    file_storage.save(temp_path)
    
    try:
        # Process based on file type
        if extension == 'csv':
            _import_properties_from_csv(temp_path, year, result)
        elif extension in ['xls', 'xlsx']:
            _import_properties_from_excel(temp_path, year, result)
        else:
            result.add_error(f"Unsupported file format: {extension}")
    except Exception as e:
        result.add_error(f"Error processing file: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # Log the import operation
    result.log_import(filename, 'property')
    
    return result

def handle_district_import(file_storage, year=None):
    """
    Import tax district data from a file.
    
    Args:
        file_storage: FileStorage object from Flask's request.files
        year: Year for the imported data (defaults to current year)
        
    Returns:
        ImportResult object with import statistics
    """
    result = ImportResult()
    
    if not file_storage:
        result.add_error("No file provided")
        return result
    
    filename = secure_filename(file_storage.filename)
    extension = get_file_extension(filename)
    
    if year is None:
        year = datetime.now().year
    
    # Save the file temporarily
    temp_path = os.path.join('/tmp', filename)
    file_storage.save(temp_path)
    
    try:
        # Process based on file type
        if extension == 'csv':
            _import_districts_from_csv(temp_path, year, result)
        elif extension in ['xls', 'xlsx']:
            _import_districts_from_excel(temp_path, year, result)
        elif extension == 'xml':
            _import_districts_from_xml(temp_path, year, result)
        elif extension == 'txt':
            _import_districts_from_txt(temp_path, year, result)
        else:
            result.add_error(f"Unsupported file format: {extension}")
    except Exception as e:
        result.add_error(f"Error processing file: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # Log the import operation
    result.log_import(filename, 'district')
    
    return result

def _import_properties_from_csv(file_path, year, result):
    """Import property data from a CSV file."""
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                try:
                    # Check required fields
                    if not all(k in row and row[k] for k in ['property_id', 'assessed_value', 'tax_code']):
                        result.add_warning(f"Missing required fields in row: {row}")
                        result.records_skipped += 1
                        continue
                    
                    # Check if property already exists
                    existing_property = Property.query.filter_by(
                        property_id=row['property_id'],
                        year=year
                    ).first()
                    
                    if existing_property:
                        # Update existing property
                        existing_property.assessed_value = float(row['assessed_value'])
                        existing_property.tax_code = row['tax_code']
                        existing_property.address = row.get('address')
                        existing_property.owner_name = row.get('owner_name')
                        existing_property.property_type = row.get('property_type')
                        existing_property.updated_at = datetime.utcnow()
                    else:
                        # Create new property
                        new_property = Property(
                            property_id=row['property_id'],
                            assessed_value=float(row['assessed_value']),
                            tax_code=row['tax_code'],
                            address=row.get('address'),
                            owner_name=row.get('owner_name'),
                            property_type=row.get('property_type'),
                            year=year
                        )
                        db.session.add(new_property)
                    
                    # Check if tax code exists and create if not
                    tax_code = TaxCode.query.filter_by(code=row['tax_code'], year=year).first()
                    if not tax_code:
                        new_tax_code = TaxCode(
                            code=row['tax_code'],
                            description=f"Imported {row['tax_code']}",
                            year=year
                        )
                        db.session.add(new_tax_code)
                    
                    result.records_imported += 1
                    
                    # Commit every 100 records
                    if result.records_imported % 100 == 0:
                        db.session.commit()
                
                except Exception as e:
                    result.add_warning(f"Error processing row: {str(e)}")
                    result.records_skipped += 1
                    db.session.rollback()
            
            # Final commit
            db.session.commit()
    except Exception as e:
        result.add_error(f"Error reading CSV file: {str(e)}")
        db.session.rollback()

def _import_properties_from_excel(file_path, year, result):
    """Import property data from an Excel file."""
    try:
        df = pd.read_excel(file_path)
        
        # Check if required columns exist
        required_cols = ['property_id', 'assessed_value', 'tax_code']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            result.add_error(f"Missing required columns: {', '.join(missing)}")
            return
        
        # Process each row
        for _, row in df.iterrows():
            try:
                # Skip rows with missing values in required columns
                if pd.isna(row['property_id']) or pd.isna(row['assessed_value']) or pd.isna(row['tax_code']):
                    result.add_warning(f"Missing required fields in row: {row.to_dict()}")
                    result.records_skipped += 1
                    continue
                
                # Convert values to appropriate types
                property_id = str(row['property_id'])
                assessed_value = float(row['assessed_value'])
                tax_code = str(row['tax_code'])
                
                # Optional fields
                address = str(row['address']) if 'address' in row and not pd.isna(row['address']) else None
                owner_name = str(row['owner_name']) if 'owner_name' in row and not pd.isna(row['owner_name']) else None
                property_type = str(row['property_type']) if 'property_type' in row and not pd.isna(row['property_type']) else None
                
                # Check if property already exists
                existing_property = Property.query.filter_by(
                    property_id=property_id,
                    year=year
                ).first()
                
                if existing_property:
                    # Update existing property
                    existing_property.assessed_value = assessed_value
                    existing_property.tax_code = tax_code
                    existing_property.address = address
                    existing_property.owner_name = owner_name
                    existing_property.property_type = property_type
                    existing_property.updated_at = datetime.utcnow()
                else:
                    # Create new property
                    new_property = Property(
                        property_id=property_id,
                        assessed_value=assessed_value,
                        tax_code=tax_code,
                        address=address,
                        owner_name=owner_name,
                        property_type=property_type,
                        year=year
                    )
                    db.session.add(new_property)
                
                # Check if tax code exists and create if not
                tax_code_obj = TaxCode.query.filter_by(code=tax_code, year=year).first()
                if not tax_code_obj:
                    new_tax_code = TaxCode(
                        code=tax_code,
                        description=f"Imported {tax_code}",
                        year=year
                    )
                    db.session.add(new_tax_code)
                
                result.records_imported += 1
                
                # Commit every 100 records
                if result.records_imported % 100 == 0:
                    db.session.commit()
            
            except Exception as e:
                result.add_warning(f"Error processing row: {str(e)}")
                result.records_skipped += 1
                db.session.rollback()
        
        # Final commit
        db.session.commit()
    except Exception as e:
        result.add_error(f"Error reading Excel file: {str(e)}")
        db.session.rollback()

def _import_districts_from_csv(file_path, year, result):
    """Import tax district data from a CSV file."""
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                try:
                    # Check required fields
                    if not all(k in row and row[k] for k in ['tax_district_id', 'district_name', 'levy_code']):
                        result.add_warning(f"Missing required fields in row: {row}")
                        result.records_skipped += 1
                        continue
                    
                    # Check if district already exists
                    existing_district = TaxDistrict.query.filter_by(
                        tax_district_id=row['tax_district_id'],
                        year=year
                    ).first()
                    
                    # Convert statutory limit if present
                    statutory_limit = None
                    if 'statutory_limit' in row and row['statutory_limit']:
                        try:
                            statutory_limit = float(row['statutory_limit'])
                        except ValueError:
                            result.add_warning(f"Invalid statutory limit in row: {row}")
                    
                    if existing_district:
                        # Update existing district
                        existing_district.district_name = row['district_name']
                        existing_district.levy_code = row['levy_code']
                        existing_district.statutory_limit = statutory_limit
                        existing_district.updated_at = datetime.utcnow()
                    else:
                        # Create new district
                        new_district = TaxDistrict(
                            tax_district_id=row['tax_district_id'],
                            district_name=row['district_name'],
                            levy_code=row['levy_code'],
                            statutory_limit=statutory_limit,
                            year=year
                        )
                        db.session.add(new_district)
                    
                    # Check if tax code exists and create if not
                    tax_code = TaxCode.query.filter_by(code=row['levy_code'], year=year).first()
                    if not tax_code:
                        new_tax_code = TaxCode(
                            code=row['levy_code'],
                            description=f"Tax code for {row['district_name']}",
                            year=year
                        )
                        db.session.add(new_tax_code)
                    
                    result.records_imported += 1
                    
                    # Commit every 100 records
                    if result.records_imported % 100 == 0:
                        db.session.commit()
                
                except Exception as e:
                    result.add_warning(f"Error processing row: {str(e)}")
                    result.records_skipped += 1
                    db.session.rollback()
            
            # Final commit
            db.session.commit()
    except Exception as e:
        result.add_error(f"Error reading CSV file: {str(e)}")
        db.session.rollback()

def _import_districts_from_excel(file_path, year, result):
    """Import tax district data from an Excel file."""
    try:
        df = pd.read_excel(file_path)
        
        # Check if required columns exist
        required_cols = ['tax_district_id', 'district_name', 'levy_code']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            result.add_error(f"Missing required columns: {', '.join(missing)}")
            return
        
        # Process each row
        for _, row in df.iterrows():
            try:
                # Skip rows with missing values in required columns
                if pd.isna(row['tax_district_id']) or pd.isna(row['district_name']) or pd.isna(row['levy_code']):
                    result.add_warning(f"Missing required fields in row: {row.to_dict()}")
                    result.records_skipped += 1
                    continue
                
                # Convert values to appropriate types
                tax_district_id = str(row['tax_district_id'])
                district_name = str(row['district_name'])
                levy_code = str(row['levy_code'])
                
                # Optional fields
                statutory_limit = float(row['statutory_limit']) if 'statutory_limit' in row and not pd.isna(row['statutory_limit']) else None
                
                # Check if district already exists
                existing_district = TaxDistrict.query.filter_by(
                    tax_district_id=tax_district_id,
                    year=year
                ).first()
                
                if existing_district:
                    # Update existing district
                    existing_district.district_name = district_name
                    existing_district.levy_code = levy_code
                    existing_district.statutory_limit = statutory_limit
                    existing_district.updated_at = datetime.utcnow()
                else:
                    # Create new district
                    new_district = TaxDistrict(
                        tax_district_id=tax_district_id,
                        district_name=district_name,
                        levy_code=levy_code,
                        statutory_limit=statutory_limit,
                        year=year
                    )
                    db.session.add(new_district)
                
                # Check if tax code exists and create if not
                tax_code_obj = TaxCode.query.filter_by(code=levy_code, year=year).first()
                if not tax_code_obj:
                    new_tax_code = TaxCode(
                        code=levy_code,
                        description=f"Tax code for {district_name}",
                        year=year
                    )
                    db.session.add(new_tax_code)
                
                result.records_imported += 1
                
                # Commit every 100 records
                if result.records_imported % 100 == 0:
                    db.session.commit()
            
            except Exception as e:
                result.add_warning(f"Error processing row: {str(e)}")
                result.records_skipped += 1
                db.session.rollback()
        
        # Final commit
        db.session.commit()
    except Exception as e:
        result.add_error(f"Error reading Excel file: {str(e)}")
        db.session.rollback()

def _import_districts_from_xml(file_path, year, result):
    """Import tax district data from an XML file."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Find all district elements
        districts = root.findall('.//district')
        
        for district in districts:
            try:
                # Extract values from XML elements
                tax_district_id = district.findtext('tax_district_id')
                district_name = district.findtext('district_name')
                levy_code = district.findtext('levy_code')
                statutory_limit_text = district.findtext('statutory_limit')
                
                # Check required fields
                if not all([tax_district_id, district_name, levy_code]):
                    result.add_warning(f"Missing required fields in district element: {ET.tostring(district)}")
                    result.records_skipped += 1
                    continue
                
                # Convert statutory limit if present
                statutory_limit = None
                if statutory_limit_text:
                    try:
                        statutory_limit = float(statutory_limit_text)
                    except ValueError:
                        result.add_warning(f"Invalid statutory limit in district element: {statutory_limit_text}")
                
                # Check if district already exists
                existing_district = TaxDistrict.query.filter_by(
                    tax_district_id=tax_district_id,
                    year=year
                ).first()
                
                if existing_district:
                    # Update existing district
                    existing_district.district_name = district_name
                    existing_district.levy_code = levy_code
                    existing_district.statutory_limit = statutory_limit
                    existing_district.updated_at = datetime.utcnow()
                else:
                    # Create new district
                    new_district = TaxDistrict(
                        tax_district_id=tax_district_id,
                        district_name=district_name,
                        levy_code=levy_code,
                        statutory_limit=statutory_limit,
                        year=year
                    )
                    db.session.add(new_district)
                
                # Check if tax code exists and create if not
                tax_code = TaxCode.query.filter_by(code=levy_code, year=year).first()
                if not tax_code:
                    new_tax_code = TaxCode(
                        code=levy_code,
                        description=f"Tax code for {district_name}",
                        year=year
                    )
                    db.session.add(new_tax_code)
                
                result.records_imported += 1
                
                # Commit every 100 records
                if result.records_imported % 100 == 0:
                    db.session.commit()
            
            except Exception as e:
                result.add_warning(f"Error processing district element: {str(e)}")
                result.records_skipped += 1
                db.session.rollback()
        
        # Final commit
        db.session.commit()
    except Exception as e:
        result.add_error(f"Error reading XML file: {str(e)}")
        db.session.rollback()

def _import_districts_from_txt(file_path, year, result):
    """Import tax district data from a TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Determine format based on first non-empty line
        header_line = next((line.strip() for line in lines if line.strip()), '')
        
        # Check if it's a tab-delimited file
        if '\t' in header_line:
            delimiter = '\t'
        # Check if it's a pipe-delimited file
        elif '|' in header_line:
            delimiter = '|'
        # Default to comma-delimited
        else:
            delimiter = ','
        
        # Parse header to find column positions
        headers = [h.strip() for h in header_line.split(delimiter)]
        
        # Check if required columns exist
        required_cols = ['tax_district_id', 'district_name', 'levy_code']
        if not all(col in headers for col in required_cols):
            missing = [col for col in required_cols if col not in headers]
            result.add_error(f"Missing required columns: {', '.join(missing)}")
            return
        
        # Get column indexes
        col_indexes = {col: headers.index(col) for col in headers}
        
        # Process each data line
        for line_num, line in enumerate(lines[1:], 2):  # Skip header line
            try:
                line = line.strip()
                if not line:
                    continue
                
                # Split by delimiter
                values = line.split(delimiter)
                
                # Skip if not enough columns
                if len(values) < len(headers):
                    result.add_warning(f"Line {line_num} has fewer columns than expected: {line}")
                    result.records_skipped += 1
                    continue
                
                # Extract values
                tax_district_id = values[col_indexes['tax_district_id']].strip()
                district_name = values[col_indexes['district_name']].strip()
                levy_code = values[col_indexes['levy_code']].strip()
                
                # Check required fields
                if not all([tax_district_id, district_name, levy_code]):
                    result.add_warning(f"Missing required fields in line {line_num}: {line}")
                    result.records_skipped += 1
                    continue
                
                # Extract statutory limit if present
                statutory_limit = None
                if 'statutory_limit' in col_indexes and len(values) > col_indexes['statutory_limit']:
                    try:
                        statutory_limit_value = values[col_indexes['statutory_limit']].strip()
                        if statutory_limit_value:
                            statutory_limit = float(statutory_limit_value)
                    except ValueError:
                        result.add_warning(f"Invalid statutory limit in line {line_num}: {line}")
                
                # Check if district already exists
                existing_district = TaxDistrict.query.filter_by(
                    tax_district_id=tax_district_id,
                    year=year
                ).first()
                
                if existing_district:
                    # Update existing district
                    existing_district.district_name = district_name
                    existing_district.levy_code = levy_code
                    existing_district.statutory_limit = statutory_limit
                    existing_district.updated_at = datetime.utcnow()
                else:
                    # Create new district
                    new_district = TaxDistrict(
                        tax_district_id=tax_district_id,
                        district_name=district_name,
                        levy_code=levy_code,
                        statutory_limit=statutory_limit,
                        year=year
                    )
                    db.session.add(new_district)
                
                # Check if tax code exists and create if not
                tax_code = TaxCode.query.filter_by(code=levy_code, year=year).first()
                if not tax_code:
                    new_tax_code = TaxCode(
                        code=levy_code,
                        description=f"Tax code for {district_name}",
                        year=year
                    )
                    db.session.add(new_tax_code)
                
                result.records_imported += 1
                
                # Commit every 100 records
                if result.records_imported % 100 == 0:
                    db.session.commit()
            
            except Exception as e:
                result.add_warning(f"Error processing line {line_num}: {str(e)}")
                result.records_skipped += 1
                db.session.rollback()
        
        # Final commit
        db.session.commit()
    except Exception as e:
        result.add_error(f"Error reading TXT file: {str(e)}")
        db.session.rollback()

def update_tax_code_totals(year=None):
    """
    Update the total assessed value for each tax code based on property data.
    
    Args:
        year: Year to update (defaults to current year)
        
    Returns:
        Number of tax codes updated
    """
    if year is None:
        year = datetime.now().year
    
    count = 0
    
    try:
        # Get all tax codes for the given year
        tax_codes = TaxCode.query.filter_by(year=year).all()
        
        for tax_code in tax_codes:
            # Sum the assessed values of all properties with this tax code
            total_value = db.session.query(db.func.sum(Property.assessed_value)) \
                            .filter(Property.tax_code == tax_code.code, 
                                    Property.year == year) \
                            .scalar() or 0
            
            # Update the tax code's total assessed value
            tax_code.total_assessed_value = total_value
            tax_code.updated_at = datetime.utcnow()
            
            count += 1
        
        # Commit the changes
        db.session.commit()
    
    except Exception as e:
        db.session.rollback()
        raise e
    
    return count