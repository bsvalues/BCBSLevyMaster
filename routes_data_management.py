"""
Routes for the enhanced data management system.

This module includes routes for:
- Audit trail management and review
- Data archiving and retention
- Enhanced compliance reporting
"""

import os
import json
import logging
from datetime import datetime, timedelta

from flask import render_template, request, redirect, url_for, flash, jsonify, abort, send_file
from sqlalchemy import func, desc

from app import app, db
from models import (
    AuditLog, DataArchive, ComplianceReport,
    Property, TaxCode, TaxDistrict, TaxCodeHistoricalRate,
    BillImpactEvaluation, BillImpactTaxCode
)
from utils.audit_utils import (
    get_audit_logs_for_record, get_audit_logs_by_action,
    get_recent_audit_logs, get_audit_summary,
    format_audit_log_for_display
)
from utils.archive_utils import (
    create_table_archive, create_year_end_archives,
    apply_retention_policies, get_available_archives,
    restore_archive
)
from utils.enhanced_compliance_utils import (
    generate_levy_rate_compliance_report,
    generate_filing_deadline_compliance_report,
    generate_banked_capacity_report,
    generate_comprehensive_compliance_report,
    get_compliance_history,
    apply_statutory_limits_to_scenario
)

# Set up logger
logger = logging.getLogger(__name__)

# Audit Trail Routes
@app.route('/audit-trail')
def audit_trail():
    """
    View the audit trail of data changes.
    """
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    table = request.args.get('table')
    record_id = request.args.get('record_id', type=int)
    action = request.args.get('action')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert dates if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            start_date = None
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # Set to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            end_date = None
    
    # Build query with filters
    query = AuditLog.query
    
    if table:
        query = query.filter(AuditLog.table_name == table)
    if record_id:
        query = query.filter(AuditLog.record_id == record_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    # Get distinct tables for dropdown
    tables_query = db.session.query(AuditLog.table_name.distinct()).order_by(AuditLog.table_name)
    tables = [table[0] for table in tables_query.all()]
    
    # Paginate results
    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page)
    logs = pagination.items
    
    # Format logs for display
    formatted_logs = []
    for log in logs:
        formatted_logs.append(format_audit_log_for_display(log))
    
    # Get audit summary
    summary = get_audit_summary(start_date, end_date)
    
    return render_template('audit_trail.html',
                          logs=formatted_logs,
                          pagination=pagination,
                          tables=tables,
                          actions=['CREATE', 'UPDATE', 'DELETE'],
                          selected_table=table,
                          selected_record_id=record_id,
                          selected_action=action,
                          start_date=start_date.strftime('%Y-%m-%d') if start_date else '',
                          end_date=end_date.strftime('%Y-%m-%d') if end_date else '',
                          summary=summary)

@app.route('/audit-trail/entity/<string:table_name>/<int:record_id>')
def audit_trail_entity(table_name, record_id):
    """
    View audit trail for a specific entity.
    """
    # Get audit logs for the entity
    logs = get_audit_logs_for_record(table_name, record_id)
    
    # Format logs for display
    formatted_logs = []
    for log in logs:
        formatted_logs.append(format_audit_log_for_display(log))
    
    # Get entity details if available
    entity = None
    entity_name = None
    
    if table_name == 'property':
        entity = Property.query.get(record_id)
        if entity:
            entity_name = f"Property {entity.property_id}"
    elif table_name == 'tax_code':
        entity = TaxCode.query.get(record_id)
        if entity:
            entity_name = f"Tax Code {entity.code}"
    elif table_name == 'tax_district':
        entity = TaxDistrict.query.get(record_id)
        if entity:
            entity_name = f"Tax District {entity.tax_district_id}-{entity.levy_code}"
    
    return render_template('audit_trail_entity.html',
                          logs=formatted_logs,
                          table_name=table_name,
                          record_id=record_id,
                          entity=entity,
                          entity_name=entity_name)

@app.route('/api/audit-trail/log/<int:log_id>')
def api_audit_log_detail(log_id):
    """
    API endpoint to get details of a specific audit log.
    """
    log = AuditLog.query.get_or_404(log_id)
    return jsonify(format_audit_log_for_display(log))

# Data Archive Routes
@app.route('/data-archives')
def data_archives():
    """
    View and manage data archives.
    """
    # Get filter parameters
    table = request.args.get('table')
    archive_type = request.args.get('type')
    status = request.args.get('status', 'active')
    
    # Build query with filters
    query = DataArchive.query
    
    if table:
        query = query.filter(DataArchive.table_name == table)
    if archive_type:
        query = query.filter(DataArchive.archive_type == archive_type)
    if status:
        query = query.filter(DataArchive.status == status)
    
    # Get distinct tables and types for dropdowns
    tables_query = db.session.query(DataArchive.table_name.distinct()).order_by(DataArchive.table_name)
    tables = [table[0] for table in tables_query.all()]
    
    types_query = db.session.query(DataArchive.archive_type.distinct()).order_by(DataArchive.archive_type)
    archive_types = [type[0] for type in types_query.all()]
    
    # Get archives
    archives = query.order_by(DataArchive.archive_date.desc()).all()
    
    return render_template('data_archives.html',
                          archives=archives,
                          tables=tables,
                          archive_types=archive_types,
                          selected_table=table,
                          selected_type=archive_type,
                          selected_status=status)

@app.route('/data-archives/create', methods=['GET', 'POST'])
def create_archive():
    """
    Create a new data archive.
    """
    if request.method == 'POST':
        table_name = request.form.get('table_name')
        archive_type = request.form.get('archive_type', 'backup')
        description = request.form.get('description')
        
        # Get retention days
        retention_days = None
        retention_days_str = request.form.get('retention_days')
        if retention_days_str:
            try:
                retention_days = int(retention_days_str)
            except ValueError:
                flash("Invalid retention days", 'danger')
                return redirect(url_for('create_archive'))
        
        # Create archive
        try:
            archive = create_table_archive(
                table_name=table_name,
                archive_type=archive_type,
                retention_days=retention_days,
                description=description
            )
            
            flash(f"Archive created successfully with {archive.record_count} records", 'success')
            return redirect(url_for('data_archives'))
        except Exception as e:
            logger.error(f"Error creating archive: {str(e)}")
            flash(f"Error creating archive: {str(e)}", 'danger')
            return redirect(url_for('create_archive'))
    
    # GET request - show form
    return render_template('create_archive.html',
                         tables=[
                             {'value': 'property', 'label': 'Properties'},
                             {'value': 'tax_code', 'label': 'Tax Codes'},
                             {'value': 'tax_district', 'label': 'Tax Districts'},
                             {'value': 'tax_code_historical_rate', 'label': 'Historical Rates'},
                             {'value': 'import_log', 'label': 'Import Logs'},
                             {'value': 'export_log', 'label': 'Export Logs'},
                             {'value': 'bill_impact_evaluation', 'label': 'Bill Impact Evaluations'}
                         ],
                         archive_types=[
                             {'value': 'backup', 'label': 'Backup'},
                             {'value': 'year_end', 'label': 'Year-End'},
                             {'value': 'quarterly', 'label': 'Quarterly'},
                             {'value': 'monthly', 'label': 'Monthly'},
                             {'value': 'pre_change', 'label': 'Pre-Change'}
                         ])

@app.route('/data-archives/year-end', methods=['GET', 'POST'])
def create_year_end_archive():
    """
    Create year-end archives for all relevant tables.
    """
    if request.method == 'POST':
        # Get year
        year_str = request.form.get('year')
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            year = datetime.now().year
        
        # Get retention years
        retention_years = 5  # Default 5 years
        retention_years_str = request.form.get('retention_years')
        if retention_years_str:
            try:
                retention_years = int(retention_years_str)
            except ValueError:
                pass
        
        # Convert to days
        retention_days = retention_years * 365
        
        # Create archives
        try:
            archives = create_year_end_archives(
                year=year,
                retention_days=retention_days
            )
            
            flash(f"Created {len(archives)} year-end archives for {year}", 'success')
            return redirect(url_for('data_archives'))
        except Exception as e:
            logger.error(f"Error creating year-end archives: {str(e)}")
            flash(f"Error creating year-end archives: {str(e)}", 'danger')
            return redirect(url_for('create_year_end_archive'))
    
    # GET request - show form
    current_year = datetime.now().year
    years = list(range(current_year - 5, current_year + 1))
    
    return render_template('create_year_end_archive.html',
                         years=years,
                         selected_year=current_year)

@app.route('/data-archives/restore/<int:archive_id>', methods=['GET', 'POST'])
def restore_data_archive(archive_id):
    """
    Restore data from an archive.
    """
    archive = DataArchive.query.get_or_404(archive_id)
    
    if request.method == 'POST':
        restore_type = request.form.get('restore_type', 'merge')
        
        try:
            result = restore_archive(
                archive_id=archive_id,
                restore_type=restore_type
            )
            
            flash(f"Restored {result['stats']['updated']} updated and {result['stats']['created']} new records", 'success')
            return redirect(url_for('data_archives'))
        except Exception as e:
            logger.error(f"Error restoring archive: {str(e)}")
            flash(f"Error restoring archive: {str(e)}", 'danger')
            return redirect(url_for('restore_data_archive', archive_id=archive_id))
    
    # GET request - show form
    # Get preview of what would be restored
    try:
        preview = restore_archive(
            archive_id=archive_id,
            restore_type='preview'
        )
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        preview = {'stats': {'total_records': 0}}
    
    return render_template('restore_archive.html',
                         archive=archive,
                         preview=preview)

@app.route('/api/data-archives/preview/<int:archive_id>')
def api_archive_preview(archive_id):
    """
    API endpoint to preview archive contents.
    """
    archive = DataArchive.query.get_or_404(archive_id)
    
    # Get limit and offset for pagination
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Get data preview with pagination
    data = archive.get_data()
    total = len(data)
    preview = data[offset:offset+limit] if data else []
    
    return jsonify({
        'archive': {
            'id': archive.id,
            'table_name': archive.table_name,
            'archive_date': archive.archive_date.strftime('%Y-%m-%d %H:%M:%S'),
            'record_count': archive.record_count
        },
        'preview': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'records': preview
        }
    })

# Enhanced Compliance Routes
@app.route('/enhanced-compliance')
def enhanced_compliance():
    """
    View enhanced compliance reports.
    """
    # Get selected report
    report_id = request.args.get('report_id', type=int)
    
    # If no report selected, get the most recent
    if not report_id:
        report = ComplianceReport.query.order_by(ComplianceReport.report_date.desc()).first()
        if report:
            report_id = report.id
    
    # Get the report
    report = None
    report_data = None
    if report_id:
        report = ComplianceReport.query.get(report_id)
        if report:
            report_data = report.get_report_data()
    
    # Get compliance history
    history = get_compliance_history()
    
    return render_template('enhanced_compliance.html',
                         report=report,
                         report_data=report_data,
                         history=history)

@app.route('/enhanced-compliance/generate', methods=['POST'])
def generate_compliance_report():
    """
    Generate a new comprehensive compliance report.
    """
    try:
        year_str = request.form.get('year')
        year = int(year_str) if year_str else None
        
        report = generate_comprehensive_compliance_report(year)
        
        flash("Compliance report generated successfully", 'success')
        return redirect(url_for('enhanced_compliance', report_id=report['report_id']))
    except Exception as e:
        logger.error(f"Error generating compliance report: {str(e)}")
        flash(f"Error generating compliance report: {str(e)}", 'danger')
        return redirect(url_for('enhanced_compliance'))

@app.route('/enhanced-compliance/download/<int:report_id>')
def download_compliance_report(report_id):
    """
    Download a compliance report as CSV.
    """
    report = ComplianceReport.query.get_or_404(report_id)
    report_data = report.get_report_data()
    
    # Create CSV data
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Comprehensive Compliance Report', report.report_date.strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow(['Year', report.year])
    writer.writerow(['Overall Compliance', 'Yes' if report.overall_compliant else 'No'])
    writer.writerow(['Compliance Percentage', f"{report.compliance_percentage:.2f}%"])
    writer.writerow([])
    
    # Write critical issues
    writer.writerow(['Critical Issues'])
    critical_issues = report.get_critical_issues()
    if critical_issues:
        for issue in critical_issues:
            writer.writerow([issue])
    else:
        writer.writerow(['No critical issues found'])
    writer.writerow([])
    
    # Write levy rate compliance
    levy_data = report_data.get('levy_rate_compliance', {})
    writer.writerow(['Levy Rate Compliance'])
    writer.writerow(['Tax Code', 'Levy Rate', 'Previous Rate', 'Regular Levy Compliant', 'Annual Increase Compliant', 'Issues'])
    
    for code_data in levy_data.get('regular_levy_compliance', []):
        writer.writerow([
            code_data.get('code'),
            code_data.get('levy_rate'),
            code_data.get('previous_rate'),
            'Yes' if code_data.get('regular_levy_compliant') else 'No',
            'Yes' if code_data.get('annual_increase_compliant') else 'No',
            '; '.join(code_data.get('issues', []))
        ])
    writer.writerow([])
    
    # Write filing deadline compliance
    filing_data = report_data.get('filing_deadline_compliance', {})
    writer.writerow(['Filing Deadline Compliance'])
    writer.writerow(['Deadline Date', filing_data.get('deadline_date')])
    writer.writerow(['Days Remaining', filing_data.get('days_remaining')])
    writer.writerow(['Status', filing_data.get('status')])
    warnings = filing_data.get('warnings', [])
    writer.writerow(['Warnings', '; '.join(warnings) if warnings else 'None'])
    writer.writerow([])
    
    # Write banked capacity
    banked_data = report_data.get('banked_capacity_compliance', {})
    writer.writerow(['Banked Capacity'])
    writer.writerow(['Total Banked Capacity', f"${banked_data.get('total_banked_capacity', 0):,.2f}"])
    writer.writerow(['Tax Codes with Banked Capacity', len(banked_data.get('tax_codes_with_banked_capacity', []))])
    writer.writerow([])
    
    # Write recommendations
    writer.writerow(['Recommendations'])
    recommendations = report_data.get('recommendations', [])
    for recommendation in recommendations:
        writer.writerow([recommendation])
    
    # Prepare response
    output.seek(0)
    filename = f"compliance_report_{report.year}_{report.report_date.strftime('%Y%m%d')}.csv"
    
    # Save to temporary file
    temp_path = os.path.join('/tmp', filename)
    with open(temp_path, 'w') as f:
        f.write(output.getvalue())
    
    return send_file(temp_path, as_attachment=True, download_name=filename)

# Initialize the routes
def init_data_management_routes():
    """Initialize data management routes."""
    logger.info("Initializing data management routes")
    # Routes are automatically loaded from this module