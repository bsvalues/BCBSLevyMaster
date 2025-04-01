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


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Initialize SQLAlchemy with no app yet
db = SQLAlchemy(model_class=Base)


def create_app(config_name=None):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        config_name: Configuration environment to use (development, testing, production)
        
    Returns:
        The configured Flask application
    """
    # Create and configure the app
    app = Flask(__name__)
    
    # Secret key for sessions and CSRF protection
    app.secret_key = os.environ.get("SESSION_SECRET") or "dev-secret-key"
    
    # Configure database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize SQLAlchemy with the app
    db.init_app(app)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Register template filters
    @app.template_filter('format_number')
    def format_number(value):
        """Format a number with commas as thousands separators."""
        return f"{value:,.0f}" if value else "0"
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors."""
        return app.render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        app.logger.error(f"Server error: {str(e)}")
        return app.render_template('500.html', error_details=str(e) if app.debug else None), 500
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app