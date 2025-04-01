import os
import logging
import json
import csv
import io
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.utils import secure_filename
from app import app, db
from models import Property, TaxCode, ImportLog, ExportLog, TaxDistrict, TaxCodeHistoricalRate
from utils.import_utils import process_import
from utils.levy_utils import calculate_levy_rates, apply_statutory_limits
from utils.export_utils import generate_tax_roll
from utils.district_utils import import_district_text_file, import_district_xml_file, import_district_excel_file, get_linked_levy_codes
from utils.bill_impact_utils import calculate_bill_impact
from utils.historical_utils import (
    store_current_rates_as_historical, get_available_years, 
    get_historical_rates_by_code, calculate_multi_year_changes,
    seed_historical_rates, export_historical_rates_to_csv,
    import_historical_rates_from_csv
)
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
            
            # Create a FileStorage object from the saved file
            with open(temp_path, 'rb') as f:
                file_content = f.read()
            
            from werkzeug.datastructures import FileStorage
            file_obj = FileStorage(
                stream=io.BytesIO(file_content),
                filename=filename,
                name='file'
            )
            
            # Process the import with our new utility
            result = process_import(file_obj, 'property')
            
            # Remove temp file
            os.remove(temp_path)
            
            # No need to manually create import log as process_import handles that
            
            if result.success:
                flash(f"Successfully imported {result.imported_count} properties. Skipped {result.skipped_count} records.", 'success')
            else:
                error_msg = "; ".join(result.error_messages) if result.error_messages else "Unknown error"
                warnings_msg = f" ({len(result.warning_messages)} warnings)" if result.warning_messages else ""
                flash(f"Import completed with errors: {error_msg}{warnings_msg}. Imported {result.imported_count} properties. Skipped {result.skipped_count} records.", 'warning')
            
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
            
            # Create a FileStorage object from the saved file
            with open(temp_path, 'rb') as f:
                file_content = f.read()
            
            from werkzeug.datastructures import FileStorage
            file_obj = FileStorage(
                stream=io.BytesIO(file_content),
                filename=filename,
                name='file'
            )
            
            # Use our new process_import function for tax district data
            result = process_import(file_obj, 'tax_district')
            
            # Remove temp file
            os.remove(temp_path)
            
            if result.success:
                flash(f"Successfully imported {result.imported_count} district relationships. Skipped {result.skipped_count} records.", 'success')
            else:
                error_msg = "; ".join(result.error_messages) if result.error_messages else "Unknown error"
                warnings_msg = f" ({len(result.warning_messages)} warnings)" if result.warning_messages else ""
                flash(f"Import completed with errors: {error_msg}{warnings_msg}. Imported {result.imported_count} district relationships. Skipped {result.skipped_count} records.", 'warning')
                
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
    
    Enhanced version with:
    - Statutory limit application
    - Historical rate comparison
    - Levy scenario simulation
    - AI-powered insights
    """
    mcp_insights = None
    limited_rates = None
    levy_rates = None
    historical_comparison = None
    scenario_results = None
    
    # Always get the historical comparison data for display
    try:
        from utils.levy_utils import calculate_historical_comparison
        historical_comparison = calculate_historical_comparison()
    except Exception as e:
        logger.error(f"Error calculating historical comparison: {str(e)}")
    
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
        from utils.levy_utils import calculate_levy_rates, apply_statutory_limits, update_tax_codes_with_levy_rates
        levy_rates = calculate_levy_rates(levy_amounts)
        
        # Apply statutory limits
        limited_rates = apply_statutory_limits(levy_rates)
        
        # Update TaxCode database with new levy amounts and rates
        update_tax_codes_with_levy_rates(limited_rates, levy_amounts)
        
        # Generate scenarios for what-if analysis
        from utils.levy_utils import simulate_levy_scenarios
        default_scenarios = [
            {'name': 'Current', 'adjustments': {}},
            {'name': '1% Increase', 'adjustments': {code: 1.01 for code in levy_amounts.keys()}},
            {'name': '5% Increase', 'adjustments': {code: 1.05 for code in levy_amounts.keys()}},
            {'name': '1% Decrease', 'adjustments': {code: 0.99 for code in levy_amounts.keys()}},
            {'name': '5% Decrease', 'adjustments': {code: 0.95 for code in levy_amounts.keys()}}
        ]
        
        try:
            scenario_results = simulate_levy_scenarios(default_scenarios)
        except Exception as e:
            logger.error(f"Error simulating levy scenarios: {str(e)}")
            
        # Generate AI-powered insights for levy rates if Claude is available
        try:
            from utils.anthropic_utils import get_claude_service
            from utils.levy_utils import get_levy_insights
            
            # Prepare data for analysis
            levy_data = {
                'levy_amounts': levy_amounts,
                'original_rates': levy_rates,
                'limited_rates': limited_rates,
                'statutory_limits': {
                    'max_rate': float(5.90),  # Maximum levy rate per $1,000
                    'max_increase': float(1.01)  # Maximum 1% annual increase
                },
                'historical_comparison': historical_comparison,
                'scenarios': scenario_results
            }
            
            # Get AI insights
            insights_result = get_levy_insights(levy_data)
            
            if insights_result.get('status') == 'success':
                insights = insights_result.get('insights', {})
                
                # Create MCP insights for the template
                mcp_insights = {
                    'narrative': f"""
                        <div class="card mb-4">
                            <div class="card-header">
                                <h5 class="mb-0"><i class="bi bi-robot"></i> AI Analysis</h5>
                            </div>
                            <div class="card-body">
                                <h6>Statutory Compliance:</h6>
                                <p>{insights.get('compliance', 'The calculated levy rates have been analyzed for statutory compliance.')}</p>
                                
                                <h6>Tax Impact Analysis:</h6>
                                <p>{insights.get('impact', 'Impact analysis on property owners and districts available.')}</p>
                                
                                <h6>Recommendations:</h6>
                                <ul>
                                    {' '.join([f'<li>{rec}</li>' for rec in insights.get('recommendations', ['No specific recommendations available'])])}
                                </ul>
                            </div>
                        </div>
                    """,
                    'data': {
                        'levy_codes_count': len(levy_amounts),
                        'compliance_status': insights.get('compliance_status', 'Within limits'),
                        'key_insights': insights.get('key_insights', []),
                        'recommendations': insights.get('recommendations', [])
                    }
                }
            else:
                logger.info(f"Claude analysis not available: {insights_result.get('message')}")
        except Exception as e:
            logger.error(f"Error generating levy insights: {str(e)}")
        
        flash("Levy rates calculated and updated successfully", 'success')
        
        # Get all tax codes with updated values for display
        tax_codes = TaxCode.query.all()
        return render_template('levy_calculator.html', 
                              tax_codes=tax_codes, 
                              mcp_insights=mcp_insights,
                              levy_rates=levy_rates,
                              limited_rates=limited_rates,
                              historical_comparison=historical_comparison,
                              scenario_results=scenario_results,
                              calculated=True)
    
    # Get all tax codes with their total assessed values
    tax_codes = TaxCode.query.all()
    
    return render_template('levy_calculator.html', 
                          tax_codes=tax_codes,
                          historical_comparison=historical_comparison)

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    """
    Generate and download tax roll reports with enhanced statutory compliance checks.
    """
    compliance_report = None
    report_type = request.args.get('report_type', 'tax_roll')

    if request.method == 'POST':
        if 'generate_tax_roll' in request.form:
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
        
        elif 'generate_compliance_report' in request.form:
            # Generate compliance report as CSV
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"statutory_compliance_{timestamp}.csv"
            file_path = os.path.join('/tmp', filename)
            
            try:
                from utils.compliance_utils import generate_compliance_report
                compliance_data = generate_compliance_report()
                
                # Convert compliance report to CSV
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow(['Statutory Compliance Report', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                    writer.writerow(['Overall Compliance', 'Yes' if compliance_data['overall_compliant'] else 'No'])
                    writer.writerow(['Compliance Percentage', f"{compliance_data['compliance_percentage']:.2f}%"])
                    writer.writerow([])
                    
                    # Write critical issues
                    writer.writerow(['Critical Issues'])
                    if compliance_data['critical_issues']:
                        for issue in compliance_data['critical_issues']:
                            writer.writerow([issue])
                    else:
                        writer.writerow(['No critical issues found'])
                    writer.writerow([])
                    
                    # Write levy rate compliance details
                    writer.writerow(['Levy Rate Compliance'])
                    writer.writerow(['Tax Code', 'Levy Rate', 'Previous Rate', 'Regular Levy Compliant', 'Annual Increase Compliant', 'Issues'])
                    
                    for code_data in compliance_data['levy_rate_compliance']['regular_levy_compliance']:
                        writer.writerow([
                            code_data['code'],
                            code_data['levy_rate'],
                            code_data['previous_rate'],
                            'Yes' if code_data['regular_levy_compliant'] else 'No',
                            'Yes' if code_data['annual_increase_compliant'] else 'No',
                            '; '.join(code_data['issues']) if code_data['issues'] else 'None'
                        ])
                    writer.writerow([])
                    
                    # Write filing deadline compliance
                    writer.writerow(['Filing Deadline Compliance'])
                    writer.writerow(['Deadline Date', compliance_data['filing_deadline_compliance']['deadline_date']])
                    writer.writerow(['Days Remaining', compliance_data['filing_deadline_compliance']['days_remaining']])
                    writer.writerow(['Status', compliance_data['filing_deadline_compliance']['status']])
                    writer.writerow(['Warnings', '; '.join(compliance_data['filing_deadline_compliance']['warnings']) if compliance_data['filing_deadline_compliance']['warnings'] else 'None'])
                    writer.writerow([])
                    
                    # Write banked capacity information
                    writer.writerow(['Banked Capacity Information'])
                    writer.writerow(['Total Banked Capacity', f"${compliance_data['banked_capacity_compliance']['total_banked_capacity']:,.2f}"])
                    writer.writerow(['Tax Codes with Banked Capacity', len(compliance_data['banked_capacity_compliance']['tax_codes_with_banked_capacity'])])
                    writer.writerow([])
                    
                    # Write recommendations
                    writer.writerow(['Recommendations'])
                    for recommendation in compliance_data['recommendations']:
                        writer.writerow([recommendation])
                
                # Log the export
                export_log = ExportLog(
                    filename=filename,
                    rows_exported=len(compliance_data['levy_rate_compliance']['regular_levy_compliance'])
                )
                db.session.add(export_log)
                db.session.commit()
                
                # Return the file for download
                return send_file(file_path, as_attachment=True, download_name=filename)
            
            except Exception as e:
                logger.error(f"Error generating compliance report: {str(e)}")
                flash(f"Error generating compliance report: {str(e)}", 'danger')
    
    # Generate compliance report for display
    if report_type == 'compliance':
        try:
            from utils.compliance_utils import generate_compliance_report
            compliance_report = generate_compliance_report()
        except Exception as e:
            logger.error(f"Error generating compliance report for display: {str(e)}")
            flash(f"Error generating compliance report: {str(e)}", 'danger')
    
    # Get recent export history
    recent_exports = ExportLog.query.order_by(ExportLog.export_date.desc()).limit(10).all()
    
    return render_template('reports.html', 
                          compliance_report=compliance_report,
                          report_type=report_type,
                          recent_exports=recent_exports)

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

@app.route('/api/levy-historical')
def api_levy_historical():
    """
    API endpoint for historical levy rate comparison.
    """
    from utils.levy_utils import calculate_historical_comparison
    
    try:
        comparison = calculate_historical_comparison()
        
        # Format data for chart display
        tax_codes = [item['code'] for item in comparison]
        current_rates = [item['current_rate'] for item in comparison]
        previous_rates = [item['previous_rate'] for item in comparison]
        
        return jsonify({
            'tax_codes': tax_codes,
            'current_rates': current_rates,
            'previous_rates': previous_rates,
            'comparison': comparison
        })
    except Exception as e:
        logger.error(f"Error generating historical comparison: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/levy-scenarios', methods=['POST'])
def api_levy_scenarios():
    """
    API endpoint for levy scenario analysis.
    """
    from utils.levy_utils import simulate_levy_scenarios
    
    try:
        data = request.get_json()
        scenarios = data.get('scenarios', [])
        
        if not scenarios:
            # Use default scenarios if none provided
            scenarios = [
                {'name': 'Current', 'adjustments': {}},
                {'name': '1% Increase', 'adjustments': {'adjustment_factor': 1.01}},
                {'name': '5% Increase', 'adjustments': {'adjustment_factor': 1.05}},
                {'name': '10% Increase', 'adjustments': {'adjustment_factor': 1.10}}
            ]
        
        # Run the simulation
        results = simulate_levy_scenarios(scenarios)
        
        # Format for visualization
        formatted_results = {
            'scenarios': []
        }
        
        for scenario in results:
            scenario_data = {
                'name': scenario['name'],
                'rates': [],
                'limited_rates': [],
                'impact': []
            }
            
            for code, data in scenario['scenarios'].items():
                scenario_data['rates'].append({
                    'code': code,
                    'rate': data['rate']
                })
                
                scenario_data['limited_rates'].append({
                    'code': code,
                    'rate': data['limited_rate'] if data.get('limited') else data['rate']
                })
                
                scenario_data['impact'].append({
                    'code': code,
                    'change_pct': data['change_pct']
                })
                
            formatted_results['scenarios'].append(scenario_data)
            
        return jsonify(formatted_results)
    except Exception as e:
        logger.error(f"Error simulating scenarios: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/levy-distribution')
def api_levy_distribution():
    """
    API endpoint for levy distribution visualization.
    """
    try:
        # Get tax codes with levy amounts
        tax_codes = TaxCode.query.filter(TaxCode.levy_amount.isnot(None)).all()
        
        if not tax_codes:
            return jsonify({'error': 'No levy data available'}), 404
            
        # Format data for visualization
        districts = []
        amounts = []
        
        for tc in tax_codes:
            if tc.levy_amount:
                districts.append(tc.code)
                amounts.append(float(tc.levy_amount))
                
        return jsonify({
            'districts': districts,
            'amounts': amounts
        })
    except Exception as e:
        logger.error(f"Error generating levy distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/property-impact', methods=['POST'])
def api_property_impact():
    """
    API endpoint to calculate impact of different levy scenarios on a specific property.
    """
    try:
        data = request.get_json()
        property_id = data.get('property_id')
        scenarios = data.get('scenarios', [])
        
        if not property_id:
            return jsonify({'error': 'Property ID is required'}), 400
            
        # Find the property
        property_obj = Property.query.filter_by(property_id=property_id).first()
        if not property_obj:
            return jsonify({'error': 'Property not found'}), 404
            
        # Get the tax code
        tax_code_obj = TaxCode.query.filter_by(code=property_obj.tax_code).first()
        if not tax_code_obj or not tax_code_obj.levy_rate:
            return jsonify({'error': 'Tax code or levy rate not found'}), 404
            
        # Calculate baseline tax
        base_tax = (property_obj.assessed_value / 1000) * tax_code_obj.levy_rate
        
        # Create default scenarios if none provided
        if not scenarios:
            scenarios = [
                {'name': 'Current', 'adjustments': {}},
                {'name': '1% Increase', 'adjustments': {property_obj.tax_code: 1.01}},
                {'name': '5% Increase', 'adjustments': {property_obj.tax_code: 1.05}},
                {'name': '1% Decrease', 'adjustments': {property_obj.tax_code: 0.99}},
                {'name': '5% Decrease', 'adjustments': {property_obj.tax_code: 0.95}}
            ]
            
        # Calculate impact for each scenario
        impact_results = {
            'property_id': property_id,
            'assessed_value': property_obj.assessed_value,
            'tax_code': property_obj.tax_code,
            'base_tax': base_tax,
            'scenarios': []
        }
        
        for scenario in scenarios:
            name = scenario.get('name', 'Scenario')
            adjustments = scenario.get('adjustments', {})
            
            # Get adjustment factor for this property's tax code
            adjustment = adjustments.get(property_obj.tax_code, 1.0)
            
            # Calculate adjusted rate and tax
            adjusted_rate = tax_code_obj.levy_rate * adjustment
            tax_amount = (property_obj.assessed_value / 1000) * adjusted_rate
            
            # Add to results
            impact_results['scenarios'].append({
                'name': name,
                'adjusted_rate': adjusted_rate,
                'tax_amount': tax_amount,
                'difference': tax_amount - base_tax,
                'percent_change': ((tax_amount - base_tax) / base_tax) * 100 if base_tax else 0
            })
            
        return jsonify(impact_results)
    except Exception as e:
        logger.error(f"Error calculating property impact: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/levy-insights')
def api_levy_insights():
    """
    API endpoint to get AI-powered insights about levy calculations.
    """
    from utils.levy_utils import get_levy_insights, calculate_historical_comparison
    from utils.levy_utils import simulate_levy_scenarios
    
    try:
        # Get current tax codes with levy data
        tax_codes = TaxCode.query.filter(
            TaxCode.levy_amount.isnot(None),
            TaxCode.levy_rate.isnot(None)
        ).all()
        
        if not tax_codes:
            return jsonify({'error': 'No levy data available'}), 404
        
        # Prepare data for analysis
        levy_amounts = {tc.code: tc.levy_amount for tc in tax_codes if tc.levy_amount}
        levy_rates = {tc.code: tc.levy_rate for tc in tax_codes if tc.levy_rate}
        
        # Get historical comparison
        historical_comparison = calculate_historical_comparison()
        
        # Create default scenarios
        default_scenarios = [
            {'name': 'Current', 'adjustments': {}},
            {'name': '1% Increase', 'adjustments': {code: 1.01 for code in levy_amounts.keys()}},
            {'name': '5% Decrease', 'adjustments': {code: 0.95 for code in levy_amounts.keys()}}
        ]
        
        # Run scenario simulation
        scenario_results = simulate_levy_scenarios(default_scenarios)
        
        # Prepare data for AI analysis
        levy_data = {
            'levy_amounts': levy_amounts,
            'levy_rates': levy_rates,
            'statutory_limits': {
                'max_rate': float(5.90),
                'max_increase': float(1.01)
            },
            'historical_comparison': historical_comparison,
            'scenarios': scenario_results
        }
        
        # Get AI insights
        insights_result = get_levy_insights(levy_data)
        
        return jsonify(insights_result)
    except Exception as e:
        logger.error(f"Error generating levy insights: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error generating AI analysis: {str(e)}'
        }), 500

@app.route('/bill-impact-calculator', methods=['GET', 'POST'])
def bill_impact_calculator():
    """
    Calculate the impact of pending property tax bills on levy rates and property taxes.
    """
    bill_impact_results = None
    available_tax_codes = TaxCode.query.all()
    
    if request.method == 'POST':
        bill_name = request.form.get('bill_name', 'Unnamed Bill')
        bill_description = request.form.get('bill_description', '')
        
        # Get rate changes for each tax code
        rate_changes = {}
        for tax_code in available_tax_codes:
            change_type = request.form.get(f'change_type_{tax_code.code}')
            
            if change_type == 'absolute':
                # Absolute new rate
                new_rate = request.form.get(f'new_rate_{tax_code.code}')
                if new_rate:
                    try:
                        rate_changes[tax_code.code] = float(new_rate)
                    except ValueError:
                        pass
            elif change_type == 'percentage':
                # Percentage adjustment
                adjustment = request.form.get(f'adjustment_{tax_code.code}')
                if adjustment:
                    try:
                        adj_value = float(adjustment) / 100 + 1  # Convert percentage to multiplier
                        rate_changes[tax_code.code] = {'adjustment': adj_value}
                    except ValueError:
                        pass
        
        # Get exemption changes
        exemption_changes = {}
        current_exemption = request.form.get('current_exemption')
        new_exemption = request.form.get('new_exemption')
        
        if current_exemption and new_exemption:
            try:
                exemption_changes = {
                    'current_exemption': float(current_exemption),
                    'new_exemption': float(new_exemption)
                }
            except ValueError:
                pass
        
        # Get limit changes
        limit_changes = {}
        max_rate = request.form.get('max_rate')
        max_increase = request.form.get('max_increase')
        
        if max_rate:
            try:
                limit_changes['max_rate'] = float(max_rate)
            except ValueError:
                pass
        
        if max_increase:
            try:
                limit_changes['max_increase'] = float(max_increase) / 100 + 1  # Convert percentage to multiplier
            except ValueError:
                pass
        
        # Assemble bill data
        bill_data = {
            'bill_name': bill_name,
            'bill_description': bill_description,
            'rate_changes': rate_changes,
            'exemption_changes': exemption_changes,
            'limit_changes': limit_changes
        }
        
        # Calculate impact if we have at least one change
        if rate_changes or exemption_changes or limit_changes:
            from utils.bill_impact_utils import calculate_bill_impact
            bill_impact_results = calculate_bill_impact(bill_data)
            
            if bill_impact_results.get('status') == 'success':
                flash('Bill impact analysis completed successfully.', 'success')
            else:
                flash('Error calculating bill impact. Please check your inputs.', 'danger')
        else:
            flash('Please specify at least one change to analyze.', 'warning')
    
    # Pass the current statutory limits to the template
    statutory_limits = {
        'max_rate': 5.90,
        'max_increase': 1.01
    }
    
    return render_template('bill_impact_calculator.html', 
                          tax_codes=available_tax_codes,
                          statutory_limits=statutory_limits,
                          results=bill_impact_results)


@app.route('/api/bill-impacts', methods=['POST'])
def api_bill_impacts():
    """
    API endpoint for calculating bill impacts.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        from utils.bill_impact_utils import calculate_bill_impact
        results = calculate_bill_impact(data)
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error calculating bill impact: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
    
    # Get average assessed value and levy rate
    try:
        avg_assessed_value = db.session.query(func.avg(Property.assessed_value)).scalar() or 0
        avg_levy_rate = db.session.query(func.avg(TaxCode.levy_rate)).scalar() or 0
    except:
        avg_assessed_value = 0
        avg_levy_rate = 0
    
    # Get tax distribution data
    tax_summary = []
    try:
        # Calculate the total assessed value by tax code
        tax_codes = db.session.query(TaxCode).all()
        for tc in tax_codes:
            if tc.levy_rate and tc.total_assessed_value:
                tax_summary.append({
                    'code': tc.code,
                    'assessed_value': tc.total_assessed_value,
                    'levy_rate': tc.levy_rate,
                    'percent_of_total': 0  # Will be calculated below
                })
        
        # Calculate percentages
        total_av = sum(item['assessed_value'] for item in tax_summary)
        if total_av > 0:
            for item in tax_summary:
                item['percent_of_total'] = (item['assessed_value'] / total_av) * 100
    except Exception as e:
        logger.error(f"Error calculating tax summary: {str(e)}")
    
    # Generate AI insights using Claude if available
    ai_narrative = ""
    ai_data = {}
    try:
        from utils.anthropic_utils import get_claude_service
        
        claude_service = get_claude_service()
        if claude_service:
            # Prepare data for Claude analysis
            data_for_analysis = {
                'property_count': property_count,
                'tax_code_count': tax_code_count,
                'district_count': district_count,
                'avg_assessed_value': avg_assessed_value,
                'avg_levy_rate': avg_levy_rate,
                'tax_summary': tax_summary[:5],  # Send only first 5 for brevity
                'recent_import_count': len(recent_imports),
                'recent_export_count': len(recent_exports)
            }
            
            system_prompt = """
            You are an expert property tax analyst for the Benton County Assessor's Office in Washington state.
            Analyze the provided tax system data and generate concise, professional insights on:
            1. The overall tax system efficiency and distribution
            2. Patterns in property assessments and levy rates
            3. Recommendations for further analysis or system improvements
            
            Format your response in HTML with appropriate paragraphs, bullet points, and minimal styling.
            Be factual, clear, and focused on the most relevant insights for tax administrators.
            Limit your response to 2-3 paragraphs of 2-3 sentences each.
            """
            
            prompt = f"Please analyze this property tax system data and provide insights:\n{json.dumps(data_for_analysis, indent=2)}"
            
            response = claude_service.generate_text(prompt, system_prompt, temperature=0.3)
            
            if response and not response.startswith("Error:"):
                ai_narrative = response
                
                # Also get some structured data recommendations
                data_prompt = "Based on the same data, provide exactly 3 specific action recommendations in JSON format with keys 'action1', 'action2', and 'action3'."
                data_response = claude_service.generate_text(data_prompt, system_prompt, temperature=0.3)
                
                try:
                    # Try to extract JSON from the response
                    import re
                    json_match = re.search(r'```json\n(.*?)\n```', data_response, re.DOTALL)
                    if json_match:
                        ai_data = json.loads(json_match.group(1))
                    else:
                        # Try to parse the entire response as JSON
                        ai_data = json.loads(data_response)
                except:
                    ai_data = {
                        'action1': 'Analyze tax code efficiency',
                        'action2': 'Review distribution of tax burden',
                        'action3': 'Verify statutory compliance'
                    }
    except Exception as e:
        logger.error(f"Error generating MCP insights with Claude: {str(e)}")
    
    # Assemble MCP insights data for the template
    mcp_insights = {
        'narrative': ai_narrative or """
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
            'avg_assessed_value': f"${avg_assessed_value:,.2f}",
            'avg_levy_rate': f"{avg_levy_rate:.4f}",
            'import_activity': len(recent_imports),
            'export_activity': len(recent_exports),
            'recommendations': ai_data if ai_data else {
                'action1': 'Analyze tax code efficiency',
                'action2': 'Review distribution of tax burden',
                'action3': 'Verify statutory compliance'
            }
        }
    }
    
    return render_template('mcp_insights.html', 
                          mcp_insights=mcp_insights,
                          property_count=property_count,
                          tax_code_count=tax_code_count,
                          district_count=district_count,
                          recent_imports=recent_imports,
                          recent_exports=recent_exports,
                          tax_summary=tax_summary)


@app.route('/historical-rates', methods=['GET', 'POST'])
def historical_rates():
    """
    View and manage multi-year historical levy rate data.
    """
    # Variables for template rendering
    tax_codes = TaxCode.query.all()
    available_years = get_available_years()
    chart_data = None
    selected_tax_code = None
    multi_year_analysis = None
    seeded = False
    stored = False
    
    # Get the current year (default to 2024 if not available)
    current_year = datetime.now().year
    
    if request.method == 'POST':
        if 'seed_historical_data' in request.form:
            # Seed historical rates for development and testing
            base_year = int(request.form.get('base_year', current_year))
            num_years = int(request.form.get('num_years', 5))
            
            success, message = seed_historical_rates(base_year, num_years)
            
            if success:
                flash(message, 'success')
                seeded = True
            else:
                flash(f"Error seeding historical data: {message}", 'danger')
                
            # Refresh available years
            available_years = get_available_years()
                
        elif 'store_current_rates' in request.form:
            # Store current tax code rates as historical data
            year = int(request.form.get('year', current_year))
            
            success, message = store_current_rates_as_historical(year)
            
            if success:
                flash(message, 'success')
                stored = True
            else:
                flash(f"Error storing current rates: {message}", 'danger')
                
            # Refresh available years
            available_years = get_available_years()
            
        elif 'view_historical_data' in request.form:
            # Get selected tax code for historical data viewing
            tax_code = request.form.get('tax_code')
            selected_tax_code = tax_code
            
            if tax_code:
                # Retrieve historical data for this tax code
                historical_data = get_historical_rates_by_code(tax_code)
                
                if historical_data:
                    # Prepare data for chart display
                    years = [data['year'] for data in historical_data]
                    rates = [data['levy_rate'] for data in historical_data]
                    amounts = [data['levy_amount'] for data in historical_data]
                    assessed_values = [data['total_assessed_value'] for data in historical_data]
                    
                    # Create multi-year analysis
                    multi_year_analysis = calculate_multi_year_changes(tax_code)
                    
                    # Prepare chart data
                    chart_data = {
                        'tax_code': tax_code,
                        'years': years,
                        'rates': rates,
                        'amounts': amounts,
                        'assessed_values': assessed_values,
                        'multi_year_analysis': multi_year_analysis
                    }
                else:
                    flash(f"No historical data found for tax code {tax_code}", 'warning')
            else:
                flash("Please select a tax code to view historical data", 'warning')
        
        elif 'import_historical_data' in request.form:
            # Handle file upload and import
            if 'csv_file' not in request.files:
                flash("No file selected for import", "warning")
                return redirect(request.url)
            
            file = request.files['csv_file']
            if file.filename == '':
                flash("No file selected for import", "warning")
                return redirect(request.url)
            
            if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'csv':
                # Process CSV file
                success, message, stats = import_historical_rates_from_csv(file)
                
                if success:
                    flash(message, "success")
                    # Refresh available years after import
                    available_years = get_available_years()
                else:
                    flash(f"Import error: {message}", "danger")
            else:
                flash("Invalid file type. Please upload a CSV file.", "warning")
                
        elif 'export_historical_data' in request.form:
            # Handle export request
            export_year = request.form.get('export_year')
            export_tax_code = request.form.get('export_tax_code')
            
            # Convert year to int if provided
            if export_year and export_year.isdigit():
                export_year = int(export_year)
            else:
                export_year = None
                
            # Empty string means "all tax codes"
            if not export_tax_code:
                export_tax_code = None
                
            # Generate export
            success, message, csv_data = export_historical_rates_to_csv(
                year=export_year, 
                tax_code=export_tax_code
            )
            
            if success and csv_data:
                # Generate filename
                year_part = f"_{export_year}" if export_year else "_all-years"
                code_part = f"_{export_tax_code}" if export_tax_code else "_all-codes"
                filename = f"historical_rates{year_part}{code_part}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
                
                # Send file to user
                response = send_file(
                    io.BytesIO(csv_data.getvalue().encode('utf-8')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=filename
                )
                
                # Flash success message on redirect
                flash(message, "success")
                return response
            else:
                flash(message, "warning")
    
    return render_template('historical_rates.html',
                          tax_codes=tax_codes,
                          available_years=available_years,
                          current_year=current_year,
                          chart_data=chart_data,
                          selected_tax_code=selected_tax_code,
                          multi_year_analysis=multi_year_analysis,
                          seeded=seeded,
                          stored=stored)


@app.route('/api/historical-data/<tax_code>')
def api_historical_data(tax_code):
    """
    API endpoint to get historical rate data for a specific tax code.
    """
    try:
        # Get historical data for this tax code
        historical_data = get_historical_rates_by_code(tax_code)
        
        if not historical_data:
            return jsonify({'error': f"No historical data found for tax code {tax_code}"}), 404
            
        # Create multi-year analysis
        multi_year_analysis = calculate_multi_year_changes(tax_code)
        
        # Return the data as JSON
        return jsonify({
            'tax_code': tax_code,
            'historical_data': historical_data,
            'multi_year_analysis': multi_year_analysis
        })
        
    except Exception as e:
        logger.error(f"Error retrieving historical data for {tax_code}: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/api/historical_export_preview')
def api_historical_export_preview():
    """
    API endpoint to preview historical rate data for export.
    """
    year = request.args.get('year', '')
    tax_code = request.args.get('tax_code', '')
    
    try:
        # Get data based on filters
        query = db.session.query(
            TaxCode.code.label('tax_code'),
            TaxCodeHistoricalRate.year,
            TaxCodeHistoricalRate.levy_rate,
            TaxCodeHistoricalRate.levy_amount,
            TaxCodeHistoricalRate.total_assessed_value
        ).join(
            TaxCodeHistoricalRate, 
            TaxCode.id == TaxCodeHistoricalRate.tax_code_id
        )
        
        # Apply filters if provided
        if year:
            query = query.filter(TaxCodeHistoricalRate.year == int(year))
        if tax_code:
            query = query.filter(TaxCode.code == tax_code)
            
        # Get results (limit to 100 for preview)
        results = query.limit(100).all()
        
        if not results:
            return jsonify({
                'success': False,
                'message': 'No historical rate data matching the criteria'
            })
        
        # Convert to list of dictionaries
        preview_data = []
        for row in results:
            preview_data.append({
                'tax_code': row.tax_code,
                'year': row.year,
                'levy_rate': float(row.levy_rate),
                'levy_amount': float(row.levy_amount) if row.levy_amount else None,
                'total_assessed_value': float(row.total_assessed_value) if row.total_assessed_value else None
            })
        
        return jsonify({
            'success': True,
            'preview': preview_data,
            'total_count': len(preview_data),
            'has_more': len(preview_data) == 100,
            'filters': {
                'year': year,
                'tax_code': tax_code
            }
        })
    
    except Exception as e:
        app.logger.error(f"Error generating export preview: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating preview: {str(e)}"
        })

@app.route('/api/compare_tax_codes', methods=['GET'])
def api_compare_tax_codes():
    """
    API endpoint to retrieve historical data for multiple tax codes for comparison.
    
    Query parameters:
    - tax_codes: Comma-separated list of tax codes to compare
    - years: Optional comma-separated list of years to filter by
    
    Returns:
    - Dictionary containing data for each tax code
    """
    try:
        # Get tax codes from the request
        tax_codes_param = request.args.get('tax_codes', '')
        if not tax_codes_param:
            return jsonify({
                'success': False,
                'message': 'No tax codes provided'
            })
        
        tax_codes = [code.strip() for code in tax_codes_param.split(',')]
        
        # Get optional year filter
        years_param = request.args.get('years', '')
        years_filter = None
        if years_param:
            try:
                years_filter = [int(year.strip()) for year in years_param.split(',')]
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid year format'
                })
        
        # Build response data
        comparison_data = {
            'tax_codes': tax_codes,
            'years_filter': years_filter,
            'data': {}
        }
        
        # For each tax code, get its historical data
        for tax_code in tax_codes:
            code_data = get_historical_rates_by_code(tax_code, years_filter)
            if code_data:
                # Calculate multi-year analysis for each tax code
                multi_year_analysis = calculate_multi_year_changes(tax_code, years=years_filter)
                
                comparison_data['data'][tax_code] = {
                    'historical_data': code_data,
                    'multi_year_analysis': multi_year_analysis
                }
            else:
                comparison_data['data'][tax_code] = {
                    'historical_data': [],
                    'multi_year_analysis': None,
                    'error': f"No historical data found for tax code {tax_code}"
                }
        
        # Check if any data was found
        if all('error' in comparison_data['data'][tc] for tc in tax_codes):
            return jsonify({
                'success': False,
                'message': 'No historical data found for any of the specified tax codes'
            })
        
        return jsonify({
            'success': True,
            'comparison_data': comparison_data
        })
    
    except Exception as e:
        app.logger.error(f"Error comparing tax codes: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error comparing tax codes: {str(e)}"
        })

@app.route('/api/historical_import_preview', methods=['POST'])
def api_historical_import_preview():
    """
    API endpoint to preview CSV data before import.
    """
    if 'csv_file' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No file provided'
        })
    
    csv_file = request.files['csv_file']
    if not csv_file.filename.lower().endswith('.csv'):
        return jsonify({
            'success': False,
            'message': 'File must be a CSV'
        })
    
    try:
        # Read CSV content
        csv_content = io.StringIO(csv_file.read().decode('utf-8'))
        
        # Reset file pointer for analysis
        csv_file.seek(0)
        
        # Process data for preview
        reader = csv.DictReader(csv_content)
        
        # Check if the CSV has the required headers
        required_headers = ['Tax Code', 'Year', 'Levy Rate']
        headers = reader.fieldnames
        if not headers or not all(header in headers for header in required_headers):
            return jsonify({
                'success': False,
                'message': 'CSV file is missing required headers: ' + ', '.join(required_headers)
            })
        
        # Process rows for preview
        preview_data = []
        warnings = []
        unique_tax_codes = set()
        stats = {
            'to_import': 0,
            'to_update': 0,
            'to_skip': 0,
            'unique_tax_codes': 0
        }
        
        # Get existing tax codes
        existing_tax_codes = {tc.code: tc.id for tc in TaxCode.query.all()}
        
        # Check for existing historical rates
        existing_rates = {}
        for rate in TaxCodeHistoricalRate.query.all():
            tax_code = next((tc for tc, tc_id in existing_tax_codes.items() 
                          if tc_id == rate.tax_code_id), None)
            if tax_code:
                key = f"{tax_code}_{rate.year}"
                existing_rates[key] = True
        
        for i, row in enumerate(reader):
            # Skip header row
            if i == 0 and 'Tax Code' in row and 'Year' in row:
                continue
                
            # Extract data
            tax_code = row.get('Tax Code', '').strip()
            year_str = row.get('Year', '').strip()
            levy_rate_str = row.get('Levy Rate', '').strip()
            levy_amount_str = row.get('Levy Amount', '').strip()
            total_assessed_value_str = row.get('Total Assessed Value', '').strip()
            
            # Basic validation
            row_status = 'new'
            row_valid = True
            
            # Check tax code exists
            if not tax_code or tax_code not in existing_tax_codes:
                warnings.append(f"Row {i+1}: Tax code '{tax_code}' not found in database")
                row_status = 'skip'
                row_valid = False
            else:
                unique_tax_codes.add(tax_code)
            
            # Check year format
            try:
                year = int(year_str) if year_str else None
                if not year:
                    raise ValueError("Invalid year")
            except ValueError:
                warnings.append(f"Row {i+1}: Invalid year format '{year_str}'")
                year = None
                row_status = 'skip'
                row_valid = False
            
            # Check rate format
            try:
                levy_rate = float(levy_rate_str) if levy_rate_str else None
                if levy_rate is None:
                    raise ValueError("Invalid rate")
            except ValueError:
                warnings.append(f"Row {i+1}: Invalid levy rate format '{levy_rate_str}'")
                levy_rate = None
                row_status = 'skip'
                row_valid = False
            
            # Try to parse other numeric fields
            try:
                levy_amount = float(levy_amount_str) if levy_amount_str else None
            except ValueError:
                warnings.append(f"Row {i+1}: Invalid levy amount format '{levy_amount_str}'")
                levy_amount = None
            
            try:
                total_assessed_value = float(total_assessed_value_str) if total_assessed_value_str else None
            except ValueError:
                warnings.append(f"Row {i+1}: Invalid assessed value format '{total_assessed_value_str}'")
                total_assessed_value = None
            
            # Check if this is an update to existing data
            if row_valid and f"{tax_code}_{year}" in existing_rates:
                row_status = 'update'
                stats['to_update'] += 1
            elif row_valid:
                stats['to_import'] += 1
            else:
                stats['to_skip'] += 1
            
            # Add to preview data
            preview_data.append({
                'tax_code': tax_code,
                'year': year,
                'levy_rate': levy_rate,
                'levy_amount': levy_amount,
                'total_assessed_value': total_assessed_value,
                'status': row_status
            })
            
            # Limit preview to first 100 rows
            if len(preview_data) >= 100:
                warnings.append(f"Preview limited to first 100 rows. Full import will process all {i+1} rows.")
                break
        
        stats['unique_tax_codes'] = len(unique_tax_codes)
        
        return jsonify({
            'success': True,
            'preview': preview_data,
            'warnings': warnings,
            'stats': stats,
            'has_more': len(preview_data) == 100 and reader.line_num > 100
        })
    
    except Exception as e:
        app.logger.error(f"Error analyzing CSV file: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error analyzing CSV file: {str(e)}"
        })
