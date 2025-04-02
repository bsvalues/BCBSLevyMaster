
"""Test core application startup and configuration."""
import pytest
from flask import Flask
import os
from app import create_app, db

def test_app_factory():
    """Test application factory creates app correctly."""
    app = create_app('testing')
    assert isinstance(app, Flask)
    assert app.config['TESTING'] is True
    assert app.config['SQLALCHEMY_DATABASE_URI'] is not None

def test_database_tables():
    """Test all required database tables are created."""
    app = create_app('testing')
    with app.app_context():
        # Test all models are registered
        from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog
        db.create_all()
        
        # Verify tables exist
        tables = db.engine.table_names()
        required_tables = ['property', 'tax_code', 'tax_district', 'import_log', 'export_log']
        for table in required_tables:
            assert table in tables

def test_blueprints_registered():
    """Test all blueprints are registered correctly."""
    app = create_app('testing')
    blueprint_names = ['data_management', 'forecasting', 'levy_exports', 
                      'public', 'admin', 'glossary']
    
    registered_blueprints = [bp.name for bp in app.blueprints.values()]
    for name in blueprint_names:
        assert name in registered_blueprints

def test_static_files():
    """Test essential static files are available."""
    app = create_app('testing')
    with app.test_client() as client:
        css_response = client.get('/static/css/styles.css')
        assert css_response.status_code == 200
        js_response = client.get('/static/js/main.js')
        assert js_response.status_code == 200
