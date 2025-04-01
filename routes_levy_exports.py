"""
Routes for managing levy export files in the Levy Calculation System.

This module provides routes for:
- Uploading and parsing levy export files in different formats
- Viewing historical levy export data
- Comparing levy data across years
"""

import os
import json
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, Response, current_app
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from sqlalchemy import func, desc, or_, and_

from app import db
from models import (
    TaxDistrict, TaxCode, Property, ImportLog, ExportLog,
    PropertyType, ImportType, ExportType, User, TaxCodeHistoricalRate
)
from utils.import_utils import detect_file_type, read_data_from_file


# Create blueprint
levy_exports_bp = Blueprint("levy_exports", __name__, url_prefix="/levy-exports")

# Configure logging
logger = logging.getLogger(__name__)


@levy_exports_bp.route("/", methods=["GET"])
def index():
    """Render the levy exports dashboard."""
    # Get recent levy imports related to levy rates
    recent_imports = ImportLog.query.order_by(desc(ImportLog.created_at)).limit(5).all()
    
    # Count available years of data
    years_data = db.session.query(
        TaxCodeHistoricalRate.year, 
        func.count(TaxCodeHistoricalRate.id)
    ).group_by(
        TaxCodeHistoricalRate.year
    ).order_by(
        desc(TaxCodeHistoricalRate.year)
    ).all()
    
    # Calculate some statistics
    stats = {
        'total_years': len(years_data),
        'latest_year': years_data[0][0] if years_data else datetime.now().year,
        'total_records': sum(count for _, count in years_data),
        'total_districts': TaxDistrict.query.count(),
        'total_tax_codes': TaxCode.query.count(),
    }
    
    return render_template(
        "levy_exports/index.html",
        recent_imports=recent_imports,
        years_data=years_data,
        stats=stats
    )


@levy_exports_bp.route("/upload", methods=["GET", "POST"])
def upload():
    """Handle upload of levy export files."""
    if request.method == "GET":
        # Get available years for the form
        current_year = datetime.now().year
        years = list(range(current_year - 10, current_year + 2))
        
        return render_template(
            "levy_exports/upload.html",
            years=years,
            current_year=current_year
        )
    
    # Handle POST request
    if "file" not in request.files:
        flash("No file part", "error")
        return redirect(request.url)
    
    file = request.files["file"]
    if file.filename == "":
        flash("No selected file", "error")
        return redirect(request.url)
    
    if file:
        # Save the uploaded file to a temporary location
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name
            file.save(temp_path)
        
        try:
            # Get import parameters
            year = int(request.form.get("year", datetime.now().year))
            notes = request.form.get("notes", "")
            
            # Detect file type
            file_type = detect_file_type(filename)
            if not file_type:
                file_type = "unknown"
                flash(f"Could not detect file type from filename: {filename}", "warning")
            
            # Read data from file
            try:
                data = read_data_from_file(temp_path, file_type)
                
                # Create preview data - limit to first 50 rows for display
                preview_data = data[:50] if len(data) > 50 else data
                
                # Store the data in session for processing
                # Process in a separate step to allow user to verify
                if data:
                    # Get column names from first record
                    columns = list(data[0].keys()) if data else []
                    
                    # Create a pandas DataFrame for easier analysis
                    df = pd.DataFrame(data)
                    
                    # Try to normalize/standardize column names
                    std_columns = {}
                    for col in df.columns:
                        col_lower = col.lower()
                        if 'district' in col_lower or 'tax_district' in col_lower:
                            std_columns[col] = 'tax_district_id'
                        elif 'year' in col_lower:
                            std_columns[col] = 'year'
                        elif 'levy_cd' in col_lower or 'code' in col_lower:
                            std_columns[col] = 'levy_cd'
                        elif 'linked' in col_lower:
                            std_columns[col] = 'levy_cd_linked'
                        # Add more mappings as needed
                    
                    # Rename columns if standard names were found
                    if std_columns:
                        df = df.rename(columns=std_columns)
                    
                    # Convert to records for the template
                    preview_data = df.to_dict('records')
                    preview_columns = list(df.columns)
                    
                    # Get unique values in key columns for mapping
                    unique_districts = df['tax_district_id'].unique().tolist() if 'tax_district_id' in df else []
                    unique_levy_codes = df['levy_cd'].unique().tolist() if 'levy_cd' in df else []
                    unique_linked_codes = df['levy_cd_linked'].unique().tolist() if 'levy_cd_linked' in df else []
                    
                    # Get existing districts from database for mapping
                    existing_districts = TaxDistrict.query.all()
                    district_mapping = {str(d.id): d.name for d in existing_districts}
                    
                    # Store temporary file path in session
                    temp_data = {
                        'file_path': temp_path,
                        'file_type': file_type,
                        'filename': filename,
                        'year': year,
                        'notes': notes,
                        'columns': preview_columns,
                        'total_rows': len(data)
                    }
                    
                    # Store in session as JSON
                    request.session['temp_levy_data'] = json.dumps(temp_data)
                    
                    return render_template(
                        "levy_exports/preview.html",
                        preview_data=preview_data,
                        columns=preview_columns,
                        filename=filename,
                        file_type=file_type,
                        year=year,
                        notes=notes,
                        total_rows=len(data),
                        unique_districts=unique_districts,
                        unique_levy_codes=unique_levy_codes,
                        unique_linked_codes=unique_linked_codes,
                        district_mapping=district_mapping
                    )
                else:
                    flash("No data found in the file", "error")
                    os.unlink(temp_path)
                    return redirect(request.url)
                
            except Exception as e:
                logger.error(f"Error reading file: {str(e)}")
                flash(f"Error reading file: {str(e)}", "error")
                os.unlink(temp_path)
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error during upload: {str(e)}")
            flash(f"Error during upload: {str(e)}", "error")
            os.unlink(temp_path)
            return redirect(request.url)
    
    return redirect(request.url)


@levy_exports_bp.route("/process", methods=["POST"])
def process():
    """Process the uploaded levy export file after preview."""
    # Get the temporary data from session
    temp_data_json = request.session.get('temp_levy_data')
    if not temp_data_json:
        flash("Session expired or no data found", "error")
        return redirect(url_for('levy_exports.upload'))
    
    try:
        temp_data = json.loads(temp_data_json)
        
        # Get the file information
        file_path = temp_data['file_path']
        file_type = temp_data['file_type']
        filename = temp_data['filename']
        year = temp_data['year']
        notes = temp_data['notes']
        
        # Get mapping parameters from form
        district_column = request.form.get('district_column')
        levy_code_column = request.form.get('levy_code_column')
        linked_code_column = request.form.get('linked_code_column')
        year_column = request.form.get('year_column')
        
        # Read data from file again
        data = read_data_from_file(file_path, file_type)
        
        # Create a pandas DataFrame
        df = pd.DataFrame(data)
        
        # Apply column mappings
        column_mappings = {}
        if district_column:
            column_mappings[district_column] = 'tax_district_id'
        if levy_code_column:
            column_mappings[levy_code_column] = 'levy_cd'
        if linked_code_column:
            column_mappings[linked_code_column] = 'levy_cd_linked'
        if year_column:
            column_mappings[year_column] = 'year'
            
        # Rename columns if mappings were provided
        if column_mappings:
            df = df.rename(columns=column_mappings)
        
        # Ensure required columns exist
        required_columns = ['tax_district_id', 'levy_cd', 'levy_cd_linked']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            flash(f"Missing required columns: {', '.join(missing_columns)}", "error")
            os.unlink(file_path)
            return redirect(url_for('levy_exports.upload'))
        
        # If year column doesn't exist, use the provided year
        if 'year' not in df.columns:
            df['year'] = year
        
        # Process the data - create/update TaxDistrict records if needed
        success_count = 0
        error_count = 0
        
        # Start a database transaction
        try:
            # Process districts first
            for district_id in df['tax_district_id'].unique():
                # Check if district exists
                district = TaxDistrict.query.filter_by(id=district_id).first()
                
                if not district:
                    # Create a new district
                    # Create district object properly
                    district = TaxDistrict()
                    district.id = district_id
                    district.district_code = f"D{district_id}"
                    district.district_name = f"District {district_id}"
                    district.year = year
                    db.session.add(district)
            
            # Process levy records
            for _, row in df.iterrows():
                try:
                    district_id = row['tax_district_id']
                    levy_code = row['levy_cd']
                    linked_code = row['levy_cd_linked']
                    record_year = int(row['year'])
                    
                    # Find the tax district
                    district = TaxDistrict.query.filter_by(id=district_id).first()
                    
                    if district:
                        # Find or create tax code for the levy code
                        tax_code = TaxCode.query.filter_by(
                            tax_code=levy_code, 
                            year=record_year
                        ).first()
                        
                        if not tax_code:
                            # Create TaxCode object properly
                            tax_code = TaxCode()
                            tax_code.tax_code = levy_code
                            tax_code.tax_district_id = district.id
                            tax_code.year = record_year
                            tax_code.description = f"Levy code {levy_code}"
                            db.session.add(tax_code)
                            db.session.flush()  # Get the ID
                        
                        # Find or create linked tax code
                        linked_tax_code = TaxCode.query.filter_by(
                            tax_code=linked_code, 
                            year=record_year
                        ).first()
                        
                        if not linked_tax_code:
                            # Create linked TaxCode object properly
                            linked_tax_code = TaxCode()
                            linked_tax_code.tax_code = linked_code
                            linked_tax_code.tax_district_id = district.id
                            linked_tax_code.year = record_year
                            linked_tax_code.description = f"Linked levy code {linked_code}"
                            db.session.add(linked_tax_code)
                            db.session.flush()  # Get the ID
                        
                        # Create historical rate record if it doesn't exist
                        hist_rate = TaxCodeHistoricalRate.query.filter_by(
                            tax_code_id=tax_code.id,
                            year=record_year
                        ).first()
                        
                        if not hist_rate:
                            # Create historical rate object properly
                            hist_rate = TaxCodeHistoricalRate()
                            hist_rate.tax_code_id = tax_code.id
                            hist_rate.year = record_year
                            hist_rate.levy_rate = 0.0  # Default value, to be updated later
                            db.session.add(hist_rate)
                        
                        success_count += 1
                    else:
                        logger.warning(f"District not found: {district_id}")
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing row: {str(e)}")
                    error_count += 1
            
            # Create the import log
            # Create a simple import log without details
            import_log = ImportLog()
            import_log.user_id = 1  # Default user ID
            import_log.filename = filename
            import_log.record_count = len(df)
            import_log.success_count = success_count
            import_log.error_count = error_count
            import_log.status = 'COMPLETED'
            import_log.processing_time = 0.0  # Should be measured
            import_log.year = year
            import_log.import_metadata = {
                'file_type': file_type,
                'notes': notes,
                'columns': list(df.columns)
            }
            db.session.add(import_log)
            
            # Commit the transaction
            db.session.commit()
            
            flash(f"Successfully processed {success_count} records with {error_count} errors", "success")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error: {str(e)}")
            flash(f"Database error: {str(e)}", "error")
            return redirect(url_for('levy_exports.upload'))
        
        # Clean up the temporary file
        os.unlink(file_path)
        
        # Clear session data
        request.session.pop('temp_levy_data', None)
        
        return redirect(url_for('levy_exports.view_year', year=year))
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        flash(f"Error processing data: {str(e)}", "error")
        return redirect(url_for('levy_exports.upload'))


@levy_exports_bp.route("/view/<int:year>", methods=["GET"])
def view_year(year):
    """View levy export data for a specific year."""
    # Get all districts for this year
    districts = TaxDistrict.query.filter_by(year=year).all()
    
    # Get all tax codes for this year
    tax_codes = TaxCode.query.filter_by(year=year).all()
    
    # Get historical rates for this year
    historical_rates = TaxCodeHistoricalRate.query.filter_by(year=year).all()
    
    # Create a mapping of tax code IDs to historical rates
    rate_mapping = {rate.tax_code_id: rate for rate in historical_rates}
    
    # Add historical rate data to tax codes
    for tax_code in tax_codes:
        tax_code.historical_rate = rate_mapping.get(tax_code.id)
    
    # Group tax codes by district
    district_tax_codes = {}
    for district in districts:
        district_codes = [tc for tc in tax_codes if tc.tax_district_id == district.id]
        district_tax_codes[district.id] = district_codes
    
    return render_template(
        "levy_exports/view.html",
        year=year,
        districts=districts,
        tax_codes=tax_codes,
        district_tax_codes=district_tax_codes,
        rate_mapping=rate_mapping
    )


@levy_exports_bp.route("/compare", methods=["GET"])
def compare():
    """Compare levy data across years."""
    # Get parameters
    start_year = request.args.get('start_year', type=int)
    end_year = request.args.get('end_year', type=int)
    district_id = request.args.get('district_id', type=int)
    
    # Default to last 5 years if not specified
    if not end_year:
        # Get the most recent year
        latest_year = db.session.query(func.max(TaxCodeHistoricalRate.year)).scalar() or datetime.now().year
        end_year = latest_year
        
    if not start_year:
        start_year = end_year - 4  # Last 5 years
    
    # Get all available years
    available_years = db.session.query(
        TaxCodeHistoricalRate.year
    ).distinct().order_by(
        TaxCodeHistoricalRate.year
    ).all()
    available_years = [y[0] for y in available_years]
    
    # Get all districts
    all_districts = TaxDistrict.query.all()
    
    # If no district is selected, get the first one
    if not district_id and all_districts:
        district_id = all_districts[0].id
    
    # Get data for comparison if all parameters are available
    comparison_data = None
    if start_year and end_year and district_id:
        # Get all tax codes for this district across the years
        tax_codes = TaxCode.query.filter_by(
            tax_district_id=district_id
        ).filter(
            TaxCode.year.between(start_year, end_year)
        ).all()
        
        # Get all historical rates for these tax codes
        tax_code_ids = [tc.id for tc in tax_codes]
        historical_rates = TaxCodeHistoricalRate.query.filter(
            TaxCodeHistoricalRate.tax_code_id.in_(tax_code_ids),
            TaxCodeHistoricalRate.year.between(start_year, end_year)
        ).all()
        
        # Organize data by year and tax code
        comparison_data = {}
        for year in range(start_year, end_year + 1):
            year_data = {}
            # Get tax codes for this year
            year_tax_codes = [tc for tc in tax_codes if tc.year == year]
            
            for tc in year_tax_codes:
                # Find historical rate for this tax code
                rate = next((r for r in historical_rates if r.tax_code_id == tc.id and r.year == year), None)
                
                if rate:
                    year_data[tc.tax_code] = {
                        'tax_code': tc.tax_code,
                        'levy_rate': rate.levy_rate,
                        'levy_amount': rate.levy_amount,
                        'total_assessed_value': rate.total_assessed_value
                    }
            
            comparison_data[year] = year_data
    
    return render_template(
        "levy_exports/compare.html",
        available_years=available_years,
        all_districts=all_districts,
        start_year=start_year,
        end_year=end_year,
        district_id=district_id,
        comparison_data=comparison_data
    )


@levy_exports_bp.route("/export", methods=["GET"])
def export_data():
    """Export levy data to various formats."""
    # Get parameters
    year = request.args.get('year', type=int, default=datetime.now().year)
    format = request.args.get('format', default='csv')
    district_id = request.args.get('district_id', type=int)
    
    # Get available years for the form
    available_years = db.session.query(
        TaxCodeHistoricalRate.year
    ).distinct().order_by(
        TaxCodeHistoricalRate.year
    ).all()
    available_years = [y[0] for y in available_years]
    
    # Get all districts
    all_districts = TaxDistrict.query.all()
    
    # If exporting, generate the export file
    if 'export' in request.args:
        try:
            # Query data based on parameters
            query = db.session.query(
                TaxCode, TaxCodeHistoricalRate, TaxDistrict
            ).join(
                TaxCodeHistoricalRate, 
                TaxCode.id == TaxCodeHistoricalRate.tax_code_id
            ).join(
                TaxDistrict,
                TaxCode.tax_district_id == TaxDistrict.id
            ).filter(
                TaxCodeHistoricalRate.year == year
            )
            
            # Filter by district if specified
            if district_id:
                query = query.filter(TaxDistrict.id == district_id)
            
            # Execute query
            results = query.all()
            
            # Format data for export
            export_data = []
            for tax_code, rate, district in results:
                export_data.append({
                    'tax_district_id': district.id,
                    'tax_district_name': district.district_name,
                    'tax_district_code': district.district_code,
                    'year': rate.year,
                    'tax_code': tax_code.tax_code,
                    'levy_rate': rate.levy_rate,
                    'levy_amount': rate.levy_amount,
                    'total_assessed_value': rate.total_assessed_value
                })
            
            # Generate the response based on format
            if format == 'csv':
                df = pd.DataFrame(export_data)
                csv_data = df.to_csv(index=False)
                
                response = Response(
                    csv_data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment;filename=levy_data_{year}.csv'
                    }
                )
                return response
                
            elif format == 'json':
                json_data = json.dumps(export_data, indent=2)
                
                response = Response(
                    json_data,
                    mimetype='application/json',
                    headers={
                        'Content-Disposition': f'attachment;filename=levy_data_{year}.json'
                    }
                )
                return response
                
            elif format == 'excel':
                df = pd.DataFrame(export_data)
                
                # Create Excel in memory
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp:
                    temp_path = temp.name
                    df.to_excel(temp_path, index=False)
                
                with open(temp_path, 'rb') as f:
                    excel_data = f.read()
                
                # Clean up temp file
                os.unlink(temp_path)
                
                response = Response(
                    excel_data,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={
                        'Content-Disposition': f'attachment;filename=levy_data_{year}.xlsx'
                    }
                )
                return response
                
            else:
                flash(f"Unsupported export format: {format}", "error")
        
        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            flash(f"Export error: {str(e)}", "error")
    
    # Render the export form
    return render_template(
        "levy_exports/export.html",
        available_years=available_years,
        all_districts=all_districts,
        year=year,
        district_id=district_id,
        format=format
    )