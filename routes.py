import os
import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.utils import secure_filename
from app import app, db
from models import Property, TaxCode, ImportLog, ExportLog, TaxDistrict
from utils.import_utils import validate_and_import_csv
from utils.levy_utils import calculate_levy_rates, apply_statutory_limits
from utils.export_utils import generate_tax_roll
from utils.district_utils import import_district_text_file, import_district_xml_file, import_district_excel_file, get_linked_levy_codes
from sqlalchemy import func

# Configure logger
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """
    Render the main dashboard.
    """
    # Count of properties
    property_count = Property.query.count()
    
    # Count of tax codes
    tax_code_count = TaxCode.query.count()
    
    # Count of tax districts
    district_count = TaxDistrict.query.count()
    
    # Recent imports
    recent_imports = ImportLog.query.order_by(ImportLog.import_date.desc()).limit(5).all()
    
    # Recent exports
    recent_exports = ExportLog.query.order_by(ExportLog.export_date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          property_count=property_count,
                          tax_code_count=tax_code_count,
                          district_count=district_count,
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
                warnings='\n'.join(result['warnings']) if result['warnings'] else None,
                import_type='property'
            )
            db.session.add(import_log)
            db.session.commit()
            
            if result['success']:
                flash(f"Successfully imported {result['imported']} properties. Skipped {result['skipped']} records.", 'success')
            else:
                flash(f"Import completed with warnings. Imported {result['imported']} properties. Skipped {result['skipped']} records.", 'warning')
            
            return redirect(url_for('index'))
    
    return render_template('import.html')

@app.route('/district-import', methods=['GET', 'POST'])
def district_import():
    """
    Handle tax district data import via file upload.
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
            
            # Detect file type and import accordingly
            result = None
            if filename.lower().endswith('.txt'):
                result = import_district_text_file(temp_path)
            elif filename.lower().endswith('.xml'):
                result = import_district_xml_file(temp_path)
            elif filename.lower().endswith('.xlsx') or filename.lower().endswith('.xls'):
                result = import_district_excel_file(temp_path)
            else:
                flash("Unsupported file format. Please upload a .txt, .xml, .xlsx, or .xls file.", 'danger')
                return redirect(request.url)
            
            # Remove temp file
            os.remove(temp_path)
            
            if result:
                # Log the import
                import_log = ImportLog(
                    filename=filename,
                    rows_imported=result['imported'],
                    rows_skipped=result['skipped'],
                    warnings='\n'.join(result['warnings']) if result['warnings'] else None,
                    import_type='district'
                )
                db.session.add(import_log)
                db.session.commit()
                
                if result['success']:
                    flash(f"Successfully imported {result['imported']} district relationships. Skipped {result['skipped']} records.", 'success')
                else:
                    flash(f"Import completed with warnings. Imported {result['imported']} district relationships. Skipped {result['skipped']} records.", 'warning')
                
                return redirect(url_for('districts'))
    
    return render_template('district_import.html')

@app.route('/districts')
def districts():
    """
    View and manage tax districts.
    """
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    selected_year = request.args.get('year', type=int)
    district_id = request.args.get('district_id', type=int)
    levy_code = request.args.get('levy_code')
    
    # Build query with filters
    query = TaxDistrict.query
    
    if selected_year:
        query = query.filter(TaxDistrict.year == selected_year)
    
    if district_id:
        query = query.filter(TaxDistrict.tax_district_id == district_id)
    
    if levy_code:
        query = query.filter(TaxDistrict.levy_code.ilike(f"%{levy_code}%"))
    
    # Get distinct years for dropdown
    years_query = db.session.query(TaxDistrict.year.distinct()).order_by(TaxDistrict.year)
    years = [year[0] for year in years_query.all()]
    
    # Paginate results
    pagination = query.order_by(TaxDistrict.year.desc(), TaxDistrict.tax_district_id).paginate(page=page, per_page=per_page)
    districts = pagination.items
    
    # Get total count of districts for display
    district_count = TaxDistrict.query.count()
    
    return render_template('districts.html',
                          district_count=district_count,
                          districts=districts,
                          pagination=pagination,
                          years=years,
                          selected_year=selected_year,
                          district_id=district_id,
                          levy_code=levy_code)

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
    mcp_insights = None
    
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
                    
                    # Get linked levy codes if available
                    linked_levy_codes = get_linked_levy_codes(property_obj.tax_code)
                    
                    property_data = {
                        'property_id': property_obj.property_id,
                        'assessed_value': property_obj.assessed_value,
                        'tax_code': property_obj.tax_code,
                        'levy_rate': tax_code_obj.levy_rate,
                        'calculated_tax': calculated_tax,
                        'linked_levy_codes': linked_levy_codes
                    }
                    
                    # Add AI-powered insights using MCP if enabled
                    try:
                        from utils.anthropic_utils import get_claude_service
                        
                        claude_service = get_claude_service()
                        if claude_service:
                            # Generate AI insights
                            insights = claude_service.analyze_property_data(property_data)
                            
                            # Check for successful analysis
                            if insights and not insights.get('error'):
                                property_data['mcp_insights'] = insights
                                
                                # Also add to general MCP insights for the template
                                mcp_insights = {
                                    'narrative': f"""
                                        <p>AI analysis for property {property_obj.property_id}:</p>
                                        <ul>
                                            <li>{insights.get('summary', 'No summary available')}</li>
                                            <li>{insights.get('recommendations', 'No recommendations available')}</li>
                                        </ul>
                                    """,
                                    'data': {
                                        'property_id': property_obj.property_id,
                                        'tax_code': property_obj.tax_code,
                                        'analysis_generated': 'Yes'
                                    }
                                }
                        else:
                            logger.info("Claude service not available for property analysis")
                    except Exception as e:
                        logger.error(f"Error generating property insights: {str(e)}")
                else:
                    flash("Tax code information or levy rate not found for this property", 'warning')
            else:
                flash("Property not found", 'danger')
    
    return render_template('property_lookup.html', property_data=property_data, mcp_insights=mcp_insights)

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

@app.route('/api/district-summary')
def api_district_summary():
    """
    API endpoint to get district summary for current year.
    """
    current_year = datetime.now().year
    
    # Get count of districts by year
    year_counts = db.session.query(
        TaxDistrict.year,
        func.count(TaxDistrict.id).label('count')
    ).group_by(TaxDistrict.year).order_by(TaxDistrict.year.desc()).limit(5).all()
    
    # Get most common levy codes
    levy_code_counts = db.session.query(
        TaxDistrict.levy_code,
        func.count(TaxDistrict.id).label('count')
    ).group_by(TaxDistrict.levy_code).order_by(func.count(TaxDistrict.id).desc()).limit(10).all()
    
    data = {
        'year_counts': [{'year': y[0], 'count': y[1]} for y in year_counts],
        'levy_code_counts': [{'code': l[0], 'count': l[1]} for l in levy_code_counts],
    }
    
    return jsonify(data)

@app.route('/mcp-insights')
def mcp_insights():
    """
    Display Model Content Protocol (MCP) insights and AI capabilities.
    """
    # Get statistical insights
    property_count = Property.query.count()
    tax_code_count = TaxCode.query.count()
    district_count = TaxDistrict.query.count()
    
    # Get recent import/export activity
    recent_imports = ImportLog.query.order_by(ImportLog.import_date.desc()).limit(5).all()
    recent_exports = ExportLog.query.order_by(ExportLog.export_date.desc()).limit(5).all()
    
    # Assemble MCP insights data for the template
    # This will be enhanced by the MCP route enhancement in utils/mcp_integration.py
    mcp_insights = {
        'narrative': """
            <p>The Model Content Protocol (MCP) integration provides intelligent insights
            into your property tax data. Here are some key observations:</p>
            <ul>
                <li>Analysis of levy rates and assessed values across districts</li>
                <li>Trend identification in property valuations</li>
                <li>Compliance verification with statutory limits</li>
                <li>Tax burden distribution analysis across property types</li>
            </ul>
        """,
        'data': {
            'property_count': property_count,
            'tax_code_count': tax_code_count,
            'district_count': district_count,
            'import_activity': len(recent_imports),
            'export_activity': len(recent_exports)
        }
    }
    
    return render_template('mcp_insights.html', 
                          mcp_insights=mcp_insights,
                          property_count=property_count,
                          tax_code_count=tax_code_count,
                          district_count=district_count,
                          recent_imports=recent_imports,
                          recent_exports=recent_exports)
