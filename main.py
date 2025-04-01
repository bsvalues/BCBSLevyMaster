"""
Main application module for the Levy Calculation System.

This module serves as the entry point for the application and sets up
all the necessary routes and configurations.
"""

import os
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from sqlalchemy.orm import DeclarativeBase

# Create the base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Create and configure the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "dev-secret-key"

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database and models (must be done after app is created)
from app import db
import models

# Import routes
from routes_data_management import data_management_bp
from routes_forecasting import forecasting_bp
from routes_historical_analysis import historical_analysis_bp
from routes_glossary import glossary_bp
from routes_public import public_bp
from routes_reports import reports_bp

# Register blueprints
app.register_blueprint(data_management_bp)
app.register_blueprint(forecasting_bp)
app.register_blueprint(historical_analysis_bp)
app.register_blueprint(glossary_bp)
app.register_blueprint(public_bp)
app.register_blueprint(reports_bp)

# Mock data for the dashboard (in production, this would come from the database)
mock_stats = {
    "property_count": 45892,
    "total_assessed_value": 8723500000,
    "district_count": 32,
    "taxcode_count": 156
}

mock_recent_activity = [
    {
        "action": "Data Import",
        "description": "Imported 1,256 new properties from assessment roll",
        "user": "john.doe@bentoncounty.gov",
        "timestamp": "2025-03-28 14:22:35"
    },
    {
        "action": "Levy Rate Update",
        "description": "Updated levy rates for Fire District #3",
        "user": "sarah.smith@bentoncounty.gov",
        "timestamp": "2025-03-27 11:15:42"
    },
    {
        "action": "Compliance Report",
        "description": "Generated annual compliance report for 2024",
        "user": "admin@bentoncounty.gov",
        "timestamp": "2025-03-26 16:30:10"
    }
]

mock_ai_insights = {
    "trends": [
        "Property values in downtown areas have increased by 12.3% over the past year",
        "Rural agricultural property assessments have remained stable with only 1.2% change",
        "Commercial property tax revenue shows a 5.7% increase compared to last year"
    ],
    "recommendations": [
        "Consider reassessing properties in the northwest district due to rapid development",
        "Update tax codes for newly annexed areas to ensure proper district allocation",
        "Review senior citizen exemption applications as demographic trends show increased eligibility"
    ],
    "anomalies": [
        "Unusual spike in property value changes in tax district 203",
        "Higher than expected number of appeals in the Riverview neighborhood"
    ]
}

# Mock data for charts
mock_tax_codes = ["101", "102", "103", "104", "105", "106", "107", "108"]
mock_rates = [9.84, 10.25, 8.75, 9.35, 11.25, 8.95, 10.55, 9.15]


@app.route('/')
def index():
    """Render the home page."""
    return render_template(
        'index.html',
        stats=mock_stats,
        recent_activity=mock_recent_activity,
        ai_insights=mock_ai_insights,
        tax_codes=mock_tax_codes,
        labels=mock_tax_codes,
        rates=mock_rates
    )


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# Custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(e)}")
    return render_template('500.html', error_details=str(e) if app.debug else None), 500


# Add template filter for formatting numbers
@app.template_filter('format_number')
def format_number(value):
    """Format a number with commas as thousands separators."""
    return f"{value:,.0f}" if value else "0"


@app.template_filter('tojson')
def to_json(value):
    """Convert a value to JSON."""
    return jsonify(value).get_data(as_text=True)


if __name__ == "__main__":
    # Initialize the database
    with app.app_context():
        db.create_all()
        
    # Run the app
    app.run(host="0.0.0.0", port=5000, debug=True)