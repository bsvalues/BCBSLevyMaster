"""
Configuration file for pytest.
"""

import os
import sys
import pytest
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app
# Using raw SQL instead of model imports to avoid database schema mismatches


@pytest.fixture
def app():
    """
    Create a Flask app for testing.
    """
    # Set testing configuration
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False
    })

    with flask_app.app_context():
        # Create tables in the test database
        from app import db
        db.create_all()
        
        # Return app for testing
        yield flask_app
        
        # Clean up after tests - skip dropping tables to avoid SQLAlchemy errors
        db.session.remove()


@pytest.fixture
def client(app):
    """
    Create a test client for the Flask app.
    """
    return app.test_client()


@pytest.fixture
def db(app):
    """
    Provide access to the database during tests.
    """
    from app import db
    return db


@pytest.fixture
def seed_test_data(db):
    """
    Seed the database with test data.
    """
    # Create test tax codes - field names aligned with database schema
    from sqlalchemy import text
    db.session.execute(
        text("""
        INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
        VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "code": "00120",
            "levy_amount": 1000000,
            "levy_rate": 2.5,
            "total_assessed_value": 400000000,
            "year": 2023
        }
    )
    
    db.session.execute(
        text("""
        INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at)
        VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "code": "00130",
            "levy_amount": 500000,
            "levy_rate": 3.1,
            "total_assessed_value": 161290322.58,
            "year": 2023
        }
    )
    
    # Create test properties - field names aligned with database schema
    db.session.execute(
        text("""
        INSERT INTO property (property_id, assessed_value, tax_code, address, owner_name, created_at, updated_at) 
        VALUES (:property_id, :assessed_value, :tax_code, :address, :owner_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "property_id": "12345-6789",
            "assessed_value": 250000,
            "tax_code": "00120",
            "address": "123 Main St, Benton City, WA",
            "owner_name": "Test Owner 1"
        }
    )
    
    db.session.execute(
        text("""
        INSERT INTO property (property_id, assessed_value, tax_code, address, owner_name, created_at, updated_at)
        VALUES (:property_id, :assessed_value, :tax_code, :address, :owner_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "property_id": "98765-4321",
            "assessed_value": 350000,
            "tax_code": "00120",
            "address": "456 Oak Ave, Benton City, WA",
            "owner_name": "Test Owner 2"
        }
    )
    
    db.session.execute(
        text("""
        INSERT INTO property (property_id, assessed_value, tax_code, address, owner_name, created_at, updated_at)
        VALUES (:property_id, :assessed_value, :tax_code, :address, :owner_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "property_id": "45678-9012",
            "assessed_value": 175000,
            "tax_code": "00130",
            "address": "789 Pine Ln, Benton City, WA",
            "owner_name": "Test Owner 3"
        }
    )
    
    # Create test tax districts - field names aligned with database schema
    db.session.execute(
        text("""
        INSERT INTO tax_district (district_id, year, levy_code, linked_levy_code, created_at, updated_at) 
        VALUES (:district_id, :year, :levy_code, :linked_levy_code, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "district_id": 1,
            "year": 2023,
            "levy_code": "00120",
            "linked_levy_code": "00130"
        }
    )
    
    db.session.execute(
        text("""
        INSERT INTO tax_district (district_id, year, levy_code, linked_levy_code, created_at, updated_at)
        VALUES (:district_id, :year, :levy_code, :linked_levy_code, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "district_id": 1,
            "year": 2023,
            "levy_code": "00130",
            "linked_levy_code": "00120"
        }
    )
    
    # Create test import log - field names aligned with database schema
    db.session.execute(
        text("""
        INSERT INTO import_log (filename, import_type, records_imported, status, import_date) 
        VALUES (:filename, :import_type, :records_imported, :status, CURRENT_TIMESTAMP)
        """),
        {
            "filename": "test_import.csv",
            "import_type": "property",
            "records_imported": 3,
            "status": "COMPLETED"
        }
    )
    
    # Create test export log - field names aligned with database schema
    db.session.execute(
        text("""
        INSERT INTO export_log (filename, records_exported, status, export_date) 
        VALUES (:filename, :records_exported, :status, CURRENT_TIMESTAMP)
        """),
        {
            "filename": "test_export.csv",
            "records_exported": 3,
            "status": "COMPLETED"
        }
    )
    
    db.session.commit()