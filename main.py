"""
Main application module for the Levy Calculation System.

This module serves as the entry point for the application and sets up
all the necessary routes and configurations.
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify

# Create Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database configuration after Flask app creation
from app2 import db
from routes_data_management import data_management_bp

# Register blueprints
app.register_blueprint(data_management_bp)

# Define routes
@app.route('/')
def index():
    """Render the home page."""
    year = datetime.now().year
    
    try:
        # Get counts for dashboard stats
        property_count = db.session.query(db.func.count()).select_from(db.metadata.tables['property']).scalar() or 0
        district_count = db.session.query(db.func.count()).select_from(db.metadata.tables['tax_district']).scalar() or 0
        tax_code_count = db.session.query(db.func.count()).select_from(db.metadata.tables['tax_code']).scalar() or 0
        
        # Get counts by year
        years_with_data = db.session.query(db.metadata.tables['property'].c.year).distinct().all()
        years_with_data = [y[0] for y in years_with_data]
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        property_count = 0
        district_count = 0
        tax_code_count = 0
        years_with_data = []
    
    return render_template(
        'index.html',
        property_count=property_count,
        district_count=district_count,
        tax_code_count=tax_code_count,
        years_with_data=years_with_data,
        current_year=year
    )

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

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
    # Create directories if they don't exist
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)