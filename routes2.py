import os
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app2 import db
from models import Property, TaxCode, ImportLog, ExportLog, TaxDistrict, TaxCodeHistoricalRate

# Create main routes blueprint
main_bp = Blueprint('main', __name__)

# Configure logger
logger = logging.getLogger(__name__)

@main_bp.route('/')
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

@main_bp.route('/import', methods=['GET', 'POST'])
def import_data():
    """
    Handle property data import via CSV upload.
    """
    return render_template('import.html')