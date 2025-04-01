"""
Main application module for the Levy Calculation System.

This module serves as the entry point for the application and sets up
all the necessary routes and configurations.
"""

import os
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request, session

from app2 import app, db
from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register blueprints
try:
    from routes_data_management import data_management_bp
    app.register_blueprint(data_management_bp)
    logger.info("Registered data_management blueprint")
except ImportError as e:
    logger.warning(f"Could not register data_management blueprint: {str(e)}")

# Add other blueprints here when they are created
# e.g., from routes_public import public_bp
#       app.register_blueprint(public_bp)

# Define routes
@app.route('/')
def index():
    """Render the home page."""
    # Get dashboard statistics
    property_count = Property.query.count()
    district_count = TaxDistrict.query.count()
    tax_code_count = TaxCode.query.count()
    
    # Get years with data
    years_with_data = db.session.query(Property.year).distinct().all()
    years_with_data = [year[0] for year in years_with_data]
    
    return render_template(
        'index.html',
        property_count=property_count,
        district_count=district_count,
        tax_code_count=tax_code_count,
        years_with_data=years_with_data,
        current_year=datetime.now().year
    )

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'environment': os.environ.get('FLASK_ENV', 'development')
    })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(e)}")
    return render_template('500.html'), 500

# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)