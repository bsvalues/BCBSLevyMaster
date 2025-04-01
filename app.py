"""
Flask application initialization and configuration.

This module initializes the Flask application, configures extensions,
and sets up database connections and other necessary components.
"""

import os
import logging
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Initialize extensions
db = SQLAlchemy(model_class=Base)


def create_app(config_name=None):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        config_name: The configuration to use (development, testing, production)
        
    Returns:
        The configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    # Configure the application
    if config_name == 'production':
        app.config.from_object('config.ProductionConfig')
    elif config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # Override config from environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    
    # Configure database connection pooling
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # Initialize extensions with the app
    db.init_app(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register template filters
    register_template_filters(app)
    
    # Configure logging
    configure_logging(app)
    
    return app


def register_error_handlers(app):
    """
    Register custom error handlers for the application.
    
    Args:
        app: The Flask application instance
    """
    @app.errorhandler(404)
    def page_not_found(error):
        if request.path.startswith('/api/'):
            return jsonify(error="Not found"), 404
        return render_template('simple_404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error="Internal server error"), 500
        return render_template('simple_404.html', 
                              error_code=500, 
                              error_title="Internal Server Error",
                              error_message="The server encountered an error processing your request."), 500


def register_template_filters(app):
    """
    Register custom template filters for Jinja templates.
    
    Args:
        app: The Flask application instance
    """
    @app.template_filter('format_currency')
    def format_currency(value):
        """Format a value as currency with $ sign and commas."""
        if value is None:
            return "$0.00"
        return "${:,.2f}".format(value)
    
    @app.template_filter('format_percent')
    def format_percent(value):
        """Format a value as a percentage."""
        if value is None:
            return "0.00%"
        return "{:.2f}%".format(value * 100)
    
    @app.template_filter('format_date')
    def format_date(value):
        """Format a date value."""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return value
        return value.strftime("%m/%d/%Y")


def configure_logging(app):
    """
    Configure logging for the application.
    
    Args:
        app: The Flask application instance
    """
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    
    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    app.logger.setLevel(log_level)
    app.logger.info('Levy Calculation System startup')


# Create the Flask application instance
app = create_app()

# Root route with welcome page
@app.route('/')
def index():
    """Render welcome page with system status"""
    return render_template('index.html')


# Import models after db is defined to avoid circular imports
with app.app_context():
    # Create tables if they don't exist
    try:
        from models import User, TaxDistrict, TaxCode, Property, ImportLog, ExportLog
        db.create_all()
        app.logger.info("Database tables created successfully")
    except Exception as e:
        app.logger.error(f"Error creating database tables: {str(e)}")