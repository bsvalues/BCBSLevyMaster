"""
Data management routes for the Levy Calculation System.

This module provides routes for importing and exporting data.
"""

import os
import json
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional
from json import JSONEncoder

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, current_app, session
from werkzeug.utils import secure_filename
import sqlalchemy as sa

from app2 import db
from models import ImportLog, ExportLog, Property, TaxCode, TaxDistrict
from utils.import_utils import process_file_import

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
data_management_bp = Blueprint(
    'data_management', 
    __name__, 
    url_prefix='/data-management',
    template_folder='templates/data_management'
)

# Define routes
@data_management_bp.route('/import', methods=['GET'])
def import_page():
    """Render the import page."""
    # Get recent imports
    recent_imports = ImportLog.query.order_by(ImportLog.import_date.desc()).limit(5).all()
    
    return render_template(
        'import.html',
        recent_imports=recent_imports,
        current_year=datetime.now().year
    )

@data_management_bp.route('/import/property', methods=['POST'])
def import_property():
    """Handle property data import."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('data_management.import_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('data_management.import_page'))
    
    try:
        result = process_file_import(file, 'property')
        
        if result.success:
            flash(f'Successfully imported {result.records_imported} properties', 'success')
        else:
            flash(f'Import failed: {result.message}', 'error')
            
        # Add warnings to flash messages
        for warning in result.warnings:
            flash(warning, 'warning')
            
        return redirect(url_for('data_management.import_page'))
    
    except Exception as e:
        logger.error(f"Error importing property data: {str(e)}")
        flash(f'Error importing property data: {str(e)}', 'error')
        return redirect(url_for('data_management.import_page'))

@data_management_bp.route('/import/district', methods=['POST'])
def import_district():
    """Handle tax district data import."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('data_management.import_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('data_management.import_page'))
    
    try:
        result = process_file_import(file, 'district')
        
        if result.success:
            flash(f'Successfully imported {result.records_imported} districts', 'success')
        else:
            flash(f'Import failed: {result.message}', 'error')
            
        # Add warnings to flash messages
        for warning in result.warnings:
            flash(warning, 'warning')
            
        return redirect(url_for('data_management.import_page'))
    
    except Exception as e:
        logger.error(f"Error importing district data: {str(e)}")
        flash(f'Error importing district data: {str(e)}', 'error')
        return redirect(url_for('data_management.import_page'))

@data_management_bp.route('/export', methods=['GET'])
def export_page():
    """Render the export page."""
    # Get available years
    years = db.session.query(Property.year).distinct().all()
    years = [year[0] for year in years]
    
    # Get recent exports
    recent_exports = ExportLog.query.order_by(ExportLog.export_date.desc()).limit(5).all()
    
    return render_template(
        'export.html',
        years=years,
        recent_exports=recent_exports,
        current_year=datetime.now().year
    )

@data_management_bp.route('/export/properties', methods=['POST'])
def export_properties():
    """Handle property data export."""
    try:
        # Get export parameters
        export_format = request.form.get('format', 'csv')
        year = request.form.get('year', datetime.now().year)
        tax_code = request.form.get('tax_code')
        
        # Build query
        query = db.session.query(Property)
        if year:
            query = query.filter(Property.year == year)
        if tax_code:
            query = query.filter(Property.tax_code == tax_code)
            
        # Execute query
        properties = query.all()
        
        if not properties:
            flash('No properties found matching the criteria', 'warning')
            return redirect(url_for('data_management.export_page'))
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{export_format}') as temp:
            temp_path = temp.name
            
            if export_format == 'csv':
                # Create CSV file
                import csv
                with open(temp_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write header
                    writer.writerow(['property_id', 'address', 'owner_name', 'assessed_value', 'tax_code', 'property_type', 'year'])
                    # Write data
                    for prop in properties:
                        writer.writerow([
                            prop.property_id,
                            prop.address,
                            prop.owner_name,
                            prop.assessed_value,
                            prop.tax_code,
                            prop.property_type,
                            prop.year
                        ])
                        
            elif export_format == 'json':
                # Create JSON file
                class PropertyEncoder(JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, Property):
                            return {
                                'property_id': obj.property_id,
                                'address': obj.address,
                                'owner_name': obj.owner_name,
                                'assessed_value': obj.assessed_value,
                                'tax_code': obj.tax_code,
                                'property_type': obj.property_type,
                                'year': obj.year
                            }
                        return super().default(obj)
                
                with open(temp_path, 'w') as jsonfile:
                    json.dump(properties, jsonfile, cls=PropertyEncoder, indent=2)
                    
            elif export_format == 'excel':
                try:
                    import pandas as pd
                    
                    # Convert to pandas DataFrame
                    data = []
                    for prop in properties:
                        data.append({
                            'property_id': prop.property_id,
                            'address': prop.address,
                            'owner_name': prop.owner_name,
                            'assessed_value': prop.assessed_value,
                            'tax_code': prop.tax_code,
                            'property_type': prop.property_type,
                            'year': prop.year
                        })
                    
                    df = pd.DataFrame(data)
                    df.to_excel(temp_path, index=False)
                    
                except ImportError:
                    flash('Excel export requires pandas to be installed', 'error')
                    return redirect(url_for('data_management.export_page'))
                
            else:
                flash(f'Unsupported export format: {export_format}', 'error')
                return redirect(url_for('data_management.export_page'))
                
        # Log the export
        export_log = ExportLog(
            filename=f'properties_{year}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}',
            export_date=datetime.utcnow(),
            export_type='property',
            rows_exported=len(properties),
            status='completed'
        )
        db.session.add(export_log)
        db.session.commit()
        
        # Create exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Copy the temporary file to the exports directory
        export_filename = f'properties_{year}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}'
        export_path = os.path.join('exports', export_filename)
        with open(temp_path, 'rb') as src, open(export_path, 'wb') as dst:
            dst.write(src.read())
            
        # Send the file
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error exporting properties: {str(e)}")
        flash(f'Error exporting properties: {str(e)}', 'error')
        return redirect(url_for('data_management.export_page'))
        
    finally:
        # Clean up temporary file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)

@data_management_bp.route('/export/districts', methods=['POST'])
def export_districts():
    """Handle tax district data export."""
    try:
        # Get export parameters
        export_format = request.form.get('format', 'csv')
        year = request.form.get('year', datetime.now().year)
        
        # Build query
        query = db.session.query(TaxDistrict)
        if year:
            query = query.filter(TaxDistrict.year == year)
            
        # Execute query
        districts = query.all()
        
        if not districts:
            flash('No districts found matching the criteria', 'warning')
            return redirect(url_for('data_management.export_page'))
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{export_format}') as temp:
            temp_path = temp.name
            
            if export_format == 'csv':
                # Create CSV file
                import csv
                with open(temp_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write header
                    writer.writerow(['tax_district_id', 'district_name', 'levy_code', 'statutory_limit', 'year'])
                    # Write data
                    for district in districts:
                        writer.writerow([
                            district.tax_district_id,
                            district.district_name,
                            district.levy_code,
                            district.statutory_limit,
                            district.year
                        ])
                        
            elif export_format == 'json':
                # Create JSON file
                class DistrictEncoder(JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, TaxDistrict):
                            return {
                                'tax_district_id': obj.tax_district_id,
                                'district_name': obj.district_name,
                                'levy_code': obj.levy_code,
                                'statutory_limit': obj.statutory_limit,
                                'year': obj.year
                            }
                        return super().default(obj)
                
                with open(temp_path, 'w') as jsonfile:
                    json.dump(districts, jsonfile, cls=DistrictEncoder, indent=2)
                    
            elif export_format == 'excel':
                try:
                    import pandas as pd
                    
                    # Convert to pandas DataFrame
                    data = []
                    for district in districts:
                        data.append({
                            'tax_district_id': district.tax_district_id,
                            'district_name': district.district_name,
                            'levy_code': district.levy_code,
                            'statutory_limit': district.statutory_limit,
                            'year': district.year
                        })
                    
                    df = pd.DataFrame(data)
                    df.to_excel(temp_path, index=False)
                    
                except ImportError:
                    flash('Excel export requires pandas to be installed', 'error')
                    return redirect(url_for('data_management.export_page'))
                
            else:
                flash(f'Unsupported export format: {export_format}', 'error')
                return redirect(url_for('data_management.export_page'))
                
        # Log the export
        export_log = ExportLog(
            filename=f'districts_{year}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}',
            export_date=datetime.utcnow(),
            export_type='district',
            rows_exported=len(districts),
            status='completed'
        )
        db.session.add(export_log)
        db.session.commit()
        
        # Create exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Copy the temporary file to the exports directory
        export_filename = f'districts_{year}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}'
        export_path = os.path.join('exports', export_filename)
        with open(temp_path, 'rb') as src, open(export_path, 'wb') as dst:
            dst.write(src.read())
            
        # Send the file
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error exporting districts: {str(e)}")
        flash(f'Error exporting districts: {str(e)}', 'error')
        return redirect(url_for('data_management.export_page'))
        
    finally:
        # Clean up temporary file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)

@data_management_bp.route('/export/tax-codes', methods=['POST'])
def export_tax_codes():
    """Handle tax code data export."""
    try:
        # Get export parameters
        export_format = request.form.get('format', 'csv')
        year = request.form.get('year', datetime.now().year)
        
        # Build query
        query = db.session.query(TaxCode)
        if year:
            query = query.filter(TaxCode.year == year)
            
        # Execute query
        tax_codes = query.all()
        
        if not tax_codes:
            flash('No tax codes found matching the criteria', 'warning')
            return redirect(url_for('data_management.export_page'))
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{export_format}') as temp:
            temp_path = temp.name
            
            if export_format == 'csv':
                # Create CSV file
                import csv
                with open(temp_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write header
                    writer.writerow(['code', 'description', 'total_assessed_value', 'levy_rate', 'levy_amount', 'year'])
                    # Write data
                    for tax_code in tax_codes:
                        writer.writerow([
                            tax_code.code,
                            tax_code.description,
                            tax_code.total_assessed_value,
                            tax_code.levy_rate,
                            tax_code.levy_amount,
                            tax_code.year
                        ])
                        
            elif export_format == 'json':
                # Create JSON file
                class TaxCodeEncoder(JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, TaxCode):
                            return {
                                'code': obj.code,
                                'description': obj.description,
                                'total_assessed_value': obj.total_assessed_value,
                                'levy_rate': obj.levy_rate,
                                'levy_amount': obj.levy_amount,
                                'year': obj.year
                            }
                        return super().default(obj)
                
                with open(temp_path, 'w') as jsonfile:
                    json.dump(tax_codes, jsonfile, cls=TaxCodeEncoder, indent=2)
                    
            elif export_format == 'excel':
                try:
                    import pandas as pd
                    
                    # Convert to pandas DataFrame
                    data = []
                    for tax_code in tax_codes:
                        data.append({
                            'code': tax_code.code,
                            'description': tax_code.description,
                            'total_assessed_value': tax_code.total_assessed_value,
                            'levy_rate': tax_code.levy_rate,
                            'levy_amount': tax_code.levy_amount,
                            'year': tax_code.year
                        })
                    
                    df = pd.DataFrame(data)
                    df.to_excel(temp_path, index=False)
                    
                except ImportError:
                    flash('Excel export requires pandas to be installed', 'error')
                    return redirect(url_for('data_management.export_page'))
                
            else:
                flash(f'Unsupported export format: {export_format}', 'error')
                return redirect(url_for('data_management.export_page'))
                
        # Log the export
        export_log = ExportLog(
            filename=f'tax_codes_{year}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}',
            export_date=datetime.utcnow(),
            export_type='tax_code',
            rows_exported=len(tax_codes),
            status='completed'
        )
        db.session.add(export_log)
        db.session.commit()
        
        # Create exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Copy the temporary file to the exports directory
        export_filename = f'tax_codes_{year}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}'
        export_path = os.path.join('exports', export_filename)
        with open(temp_path, 'rb') as src, open(export_path, 'wb') as dst:
            dst.write(src.read())
            
        # Send the file
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error exporting tax codes: {str(e)}")
        flash(f'Error exporting tax codes: {str(e)}', 'error')
        return redirect(url_for('data_management.export_page'))
        
    finally:
        # Clean up temporary file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)