import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from app import app, db
from models import Property, TaxCode, ImportLog, ExportLog
from utils.import_utils import validate_and_import_csv
from utils.levy_utils import calculate_levy_rates, apply_statutory_limits
from utils.export_utils import generate_tax_roll

@app.route('/')
def index():
    """
    Render the main dashboard.
    """
    # Count of properties
    property_count = Property.query.count()
    
    # Count of tax codes
    tax_code_count = TaxCode.query.count()
    
    # Recent imports
    recent_imports = ImportLog.query.order_by(ImportLog.import_date.desc()).limit(5).all()
    
    # Recent exports
    recent_exports = ExportLog.query.order_by(ExportLog.export_date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          property_count=property_count,
                          tax_code_count=tax_code_count,
                          recent_imports=recent_imports,
                          recent_exports=recent_exports)

@app.route('/import', methods=['GET', 'POST'])
def import_data():
    """
    Handle property data import via CSV upload.
    """
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            # Save file temporarily
            temp_path = os.path.join('/tmp', filename)
            file.save(temp_path)
            
            # Validate and import the CSV data
            result = validate_and_import_csv(temp_path)
            
            # Remove temp file
            os.remove(temp_path)
            
            # Log the import
            import_log = ImportLog(
                filename=filename,
                rows_imported=result['imported'],
                rows_skipped=result['skipped'],
                warnings='\n'.join(result['warnings']) if result['warnings'] else None
            )
            db.session.add(import_log)
            db.session.commit()
            
            if result['success']:
                flash(f"Successfully imported {result['imported']} properties. Skipped {result['skipped']} records.", 'success')
            else:
                flash(f"Import completed with warnings. Imported {result['imported']} properties. Skipped {result['skipped']} records.", 'warning')
            
            return redirect(url_for('index'))
    
    return render_template('import.html')

@app.route('/levy-calculator', methods=['GET', 'POST'])
def levy_calculator():
    """
    Calculate levy rates based on the imported property data.
    """
    if request.method == 'POST':
        # Get all tax codes
        tax_codes = db.session.query(TaxCode.code).all()
        tax_codes = [tc[0] for tc in tax_codes]
        
        levy_amounts = {}
        for tax_code in tax_codes:
            levy_amount = request.form.get(f'levy_amount_{tax_code}')
            if levy_amount:
                try:
                    levy_amounts[tax_code] = float(levy_amount)
                except ValueError:
                    flash(f"Invalid levy amount for tax code {tax_code}", 'danger')
                    return redirect(url_for('levy_calculator'))
        
        # Calculate levy rates
        levy_rates = calculate_levy_rates(levy_amounts)
        
        # Apply statutory limits
        limited_rates = apply_statutory_limits(levy_rates)
        
        # Update TaxCode database with new levy amounts and rates
        for tax_code, amount in levy_amounts.items():
            tc = TaxCode.query.filter_by(code=tax_code).first()
            if tc:
                tc.levy_amount = amount
                tc.levy_rate = limited_rates.get(tax_code, 0)
                db.session.add(tc)
        
        db.session.commit()
        
        flash("Levy rates calculated and updated successfully", 'success')
        return redirect(url_for('index'))
    
    # Get all tax codes with their total assessed values
    tax_codes = TaxCode.query.all()
    
    return render_template('levy_calculator.html', tax_codes=tax_codes)

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    """
    Generate and download tax roll reports.
    """
    if request.method == 'POST':
        # Generate tax roll data as CSV
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"tax_roll_{timestamp}.csv"
        file_path = os.path.join('/tmp', filename)
        
        # Generate the tax roll CSV
        rows_exported = generate_tax_roll(file_path)
        
        # Log the export
        export_log = ExportLog(
            filename=filename,
            rows_exported=rows_exported
        )
        db.session.add(export_log)
        db.session.commit()
        
        # Return the file for download
        return send_file(file_path, as_attachment=True, download_name=filename)
    
    return render_template('reports.html')

@app.route('/property-lookup', methods=['GET', 'POST'])
def property_lookup():
    """
    Look up property tax details by property ID.
    """
    property_data = None
    
    if request.method == 'POST':
        property_id = request.form.get('property_id')
        if property_id:
            # Find the property in the database
            property_obj = Property.query.filter_by(property_id=property_id).first()
            
            if property_obj:
                # Get the tax code information
                tax_code_obj = TaxCode.query.filter_by(code=property_obj.tax_code).first()
                
                if tax_code_obj and tax_code_obj.levy_rate:
                    # Calculate property tax
                    calculated_tax = (property_obj.assessed_value / 1000) * tax_code_obj.levy_rate
                    
                    property_data = {
                        'property_id': property_obj.property_id,
                        'assessed_value': property_obj.assessed_value,
                        'tax_code': property_obj.tax_code,
                        'levy_rate': tax_code_obj.levy_rate,
                        'calculated_tax': calculated_tax
                    }
                else:
                    flash("Tax code information or levy rate not found for this property", 'warning')
            else:
                flash("Property not found", 'danger')
    
    return render_template('property_lookup.html', property_data=property_data)

@app.route('/api/tax-codes')
def api_tax_codes():
    """
    API endpoint to get tax code information for charts.
    """
    tax_codes = TaxCode.query.all()
    data = [{
        'code': tc.code,
        'levy_amount': tc.levy_amount,
        'levy_rate': tc.levy_rate,
        'total_assessed_value': tc.total_assessed_value
    } for tc in tax_codes]
    
    return {'data': data}
