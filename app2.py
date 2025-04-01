"""
Application factory module for the Levy Calculation System.

This module provides the Flask application factory pattern
for better test isolation and configuration flexibility.
"""

import os
import logging
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define database base class
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

# Initialize SQLAlchemy extension
db = SQLAlchemy(model_class=Base)

# Create application
app = Flask(__name__)

# Configure application
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')

# Initialize database
db.init_app(app)

# Import models (after db initialization)
with app.app_context():
    from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog  # noqa: F401

def create_app(config_name=None):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        config_name: Configuration environment to use (development, testing, production)
        
    Returns:
        The configured Flask application
    """
    # Create application instance
    app_instance = Flask(__name__)
    
    # Configure app based on environment
    if config_name == 'testing':
        app_instance.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
        app_instance.config['TESTING'] = True
    else:
        app_instance.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    
    # Common configuration
    app_instance.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app_instance.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True
    }
    app_instance.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    
    # Initialize database with app
    db.init_app(app_instance)
    
    # Register blueprints
    with app_instance.app_context():
        # Import models (after db initialization)
        from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog  # noqa: F401
        
        # Import and register blueprints
        try:
            from routes_data_management import data_management_bp
            app_instance.register_blueprint(data_management_bp)
            logger.info("Registered data_management blueprint")
        except ImportError as e:
            logger.warning(f"Could not register data_management blueprint: {str(e)}")
        
        try:
            # Add other blueprints here as they are created
            pass
        except ImportError as e:
            logger.warning(f"Could not register additional blueprints: {str(e)}")
    
    return app_instance