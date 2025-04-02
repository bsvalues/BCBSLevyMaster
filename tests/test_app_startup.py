"""
Test the application startup process and core functionality.
"""

import pytest
from sqlalchemy import text
from flask import Flask
import os

def test_app_initialization(app):
    """Test that the Flask app initializes successfully."""
    assert app is not None
    assert app.testing is True

def test_database_connection(app, db):
    """Test database connection and basic operations."""
    # Simple query to verify database connection
    with app.app_context():
        # Execute a simple query using text()
        result = db.session.execute(text("SELECT 1")).scalar()
        assert result == 1

def test_model_basic_query(app, db):
    """Test basic model query without creating new records."""
    with app.app_context():
        # Import here to avoid circular imports
        from models import User
        
        # Just count users - doesn't create anything
        user_count = User.query.count()
        # Just verify the query worked
        assert isinstance(user_count, int)

def test_environment_variables():
    """Test that required environment variables are set."""
    # Check essential environment variables
    assert os.environ.get('DATABASE_URL') is not None, "DATABASE_URL not set"
    assert os.environ.get('PGHOST') is not None, "PGHOST not set"
    
    # Check for Anthropic API key
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if anthropic_key is None:
        pytest.skip("ANTHROPIC_API_KEY not set - skipping this test")
    else:
        assert len(anthropic_key) > 20, "ANTHROPIC_API_KEY appears to be invalid"

def test_app_configuration():
    """Test application configuration."""
    # Import app factory
    from app import create_app
    
    # Create app with test configuration
    app = create_app('testing')
    
    # Verify essential configuration
    assert app.config['TESTING'] is True
    assert app.config['SQLALCHEMY_DATABASE_URI'] is not None
    assert app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] is not None