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
from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog


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
        
        # Clean up after tests
        db.session.remove()
        db.drop_all()


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
    # Create test tax codes
    tax_codes = [
        TaxCode(
            code="00120",
            levy_amount=1000000,
            levy_rate=2.5,
            previous_year_rate=2.4,
            total_assessed_value=400000000
        ),
        TaxCode(
            code="00130", 
            levy_amount=500000,
            levy_rate=3.1,
            previous_year_rate=3.0,
            total_assessed_value=161290322.58
        )
    ]
    db.session.add_all(tax_codes)
    
    # Create test properties
    properties = [
        Property(
            property_id="12345-6789",
            assessed_value=250000,
            tax_code="00120"
        ),
        Property(
            property_id="98765-4321",
            assessed_value=350000,
            tax_code="00120"
        ),
        Property(
            property_id="45678-9012",
            assessed_value=175000,
            tax_code="00130"
        )
    ]
    db.session.add_all(properties)
    
    # Create test tax districts
    tax_districts = [
        TaxDistrict(
            tax_district_id=1,
            year=2023,
            levy_code="00120",
            linked_levy_code="00130"
        ),
        TaxDistrict(
            tax_district_id=1,
            year=2023,
            levy_code="00130",
            linked_levy_code="00120"
        )
    ]
    db.session.add_all(tax_districts)
    
    # Create test import log
    import_log = ImportLog(
        filename="test_import.csv",
        rows_imported=3,
        rows_skipped=0,
        import_type="property"
    )
    db.session.add(import_log)
    
    # Create test export log
    export_log = ExportLog(
        filename="test_export.csv",
        rows_exported=3
    )
    db.session.add(export_log)
    
    db.session.commit()