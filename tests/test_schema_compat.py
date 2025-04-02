"""
Tests for schema compatibility utilities.

This module tests the schema compatibility utilities to ensure they correctly
handle discrepancies between ORM models and actual database schema.
"""

import pytest
from sqlalchemy import text
from datetime import datetime


def test_get_import_log_entries(app, db):
    """Test getting import log entries with schema compatibility."""
    from utils.schema_compat import get_import_log_entries
    
    with app.app_context():
        # Create test import log entries using raw SQL (database schema)
        db.session.execute(
            text("""
            INSERT INTO import_log (filename, import_type, records_imported, records_skipped, status, import_date, notes) 
            VALUES (:filename, :import_type, :records_imported, :records_skipped, :status, :import_date, :notes)
            """),
            {
                "filename": "test_compat1.csv",
                "import_type": "property",
                "records_imported": 100,
                "records_skipped": 0,
                "status": "COMPLETED",
                "import_date": datetime.utcnow(),
                "notes": "Test import 1"
            }
        )
        
        db.session.execute(
            text("""
            INSERT INTO import_log (filename, import_type, records_imported, records_skipped, status, import_date, notes) 
            VALUES (:filename, :import_type, :records_imported, :records_skipped, :status, :import_date, :notes)
            """),
            {
                "filename": "test_compat2.csv",
                "import_type": "tax_code",
                "records_imported": 50,
                "records_skipped": 5,
                "status": "COMPLETED",
                "import_date": datetime.utcnow(),
                "notes": "Test import 2"
            }
        )
        db.session.commit()
        
        # Test the compatibility function
        entries = get_import_log_entries()
        
        # Verify we can access entries through the compatibility layer
        assert len(entries) >= 2
        
        # Verify field mappings work correctly
        for entry in entries:
            if entry.get('filename') == 'test_compat1.csv':
                assert entry.get('records_imported') == 100
                assert entry.get('record_count') == 100  # mapped field
                assert entry.get('import_type') == 'property'
                assert entry.get('status') == 'COMPLETED'
                assert entry.get('notes') == 'Test import 1'
            elif entry.get('filename') == 'test_compat2.csv':
                assert entry.get('records_imported') == 50
                assert entry.get('record_count') == 50  # mapped field
                assert entry.get('import_type') == 'tax_code'
                assert entry.get('status') == 'COMPLETED'
                assert entry.get('notes') == 'Test import 2'


def test_get_tax_codes(app, db):
    """Test getting tax codes with schema compatibility."""
    from utils.schema_compat import get_tax_codes
    
    with app.app_context():
        # Create test tax codes using raw SQL (database schema)
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, district_name, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, :district_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "SC-COMPAT-1",
                "levy_amount": 200000,
                "levy_rate": 2.75,
                "total_assessed_value": 72727272.73,
                "year": 2023,
                "district_name": "School District 1"
            }
        )
        
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, district_name, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, :district_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "SC-COMPAT-2",
                "levy_amount": 300000,
                "levy_rate": 3.25,
                "total_assessed_value": 92307692.31,
                "year": 2023,
                "district_name": "School District 2"
            }
        )
        db.session.commit()
        
        # Test the compatibility function
        tax_codes = get_tax_codes(year=2023)
        
        # Verify we can access tax codes through the compatibility layer
        assert len(tax_codes) >= 2
        
        # Verify field mappings work correctly
        for tax_code in tax_codes:
            if tax_code.get('code') == 'SC-COMPAT-1':
                assert tax_code.get('levy_amount') == 200000
                assert tax_code.get('levy_rate') == 2.75
                assert tax_code.get('total_assessed_value') == 72727272.73
                assert tax_code.get('district_name') == 'School District 1'
                assert tax_code.get('year') == 2023
            elif tax_code.get('code') == 'SC-COMPAT-2':
                assert tax_code.get('levy_amount') == 300000
                assert tax_code.get('levy_rate') == 3.25
                assert tax_code.get('total_assessed_value') == 92307692.31
                assert tax_code.get('district_name') == 'School District 2'
                assert tax_code.get('year') == 2023


def test_get_properties(app, db):
    """Test getting properties with schema compatibility."""
    from utils.schema_compat import get_properties
    
    with app.app_context():
        # Create test properties using raw SQL (database schema)
        db.session.execute(
            text("""
            INSERT INTO property (property_id, assessed_value, tax_code, address, owner_name, created_at, updated_at) 
            VALUES (:property_id, :assessed_value, :tax_code, :address, :owner_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "property_id": "PROP-COMPAT-1",
                "assessed_value": 250000,
                "tax_code": "SC-COMPAT-1",
                "address": "123 Compatibility Ave, Benton City, WA",
                "owner_name": "Schema Compat Owner 1"
            }
        )
        
        db.session.execute(
            text("""
            INSERT INTO property (property_id, assessed_value, tax_code, address, owner_name, created_at, updated_at) 
            VALUES (:property_id, :assessed_value, :tax_code, :address, :owner_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "property_id": "PROP-COMPAT-2",
                "assessed_value": 350000,
                "tax_code": "SC-COMPAT-2",
                "address": "456 Schema Lane, Benton City, WA",
                "owner_name": "Schema Compat Owner 2"
            }
        )
        db.session.commit()
        
        # Test the compatibility function
        properties = get_properties(tax_code="SC-COMPAT-1")
        
        # Verify we can access properties through the compatibility layer
        assert len(properties) >= 1
        
        # Verify field mappings work correctly
        for prop in properties:
            if prop.get('property_id') == 'PROP-COMPAT-1':
                assert prop.get('assessed_value') == 250000
                assert prop.get('tax_code') == 'SC-COMPAT-1'
                assert prop.get('address') == '123 Compatibility Ave, Benton City, WA'
                assert prop.get('owner_name') == 'Schema Compat Owner 1'


def test_get_total_assessed_value(app, db):
    """Test getting total assessed value with schema compatibility."""
    from utils.schema_compat import get_total_assessed_value
    
    with app.app_context():
        # Test the compatibility function
        total_value = get_total_assessed_value(tax_code="SC-COMPAT-1")
        
        # Verify the calculation works correctly
        assert total_value == 250000  # Based on the property created in test_get_properties


def test_get_total_levy_amount(app, db):
    """Test getting total levy amount with schema compatibility."""
    from utils.schema_compat import get_total_levy_amount
    
    with app.app_context():
        # Test the compatibility function
        levy_amount = get_total_levy_amount(tax_code="SC-COMPAT-1", year=2023)
        
        # Verify the retrieval works correctly
        assert levy_amount == 200000  # Based on the tax code created in test_get_tax_codes


def test_create_import_log(app, db):
    """Test creating import log entry with schema compatibility."""
    from utils.schema_compat import create_import_log
    
    with app.app_context():
        # Test the compatibility function
        import_id = create_import_log(
            filename="compat_test_create.csv",
            import_type="property",
            record_count=42,
            status="COMPLETED",
            description="Created through compatibility layer"
        )
        
        # Verify the entry was created
        assert import_id is not None
        
        # Verify we can retrieve the created entry
        created_entry = db.session.execute(
            text("""
            SELECT filename, import_type, records_imported, status, notes
            FROM import_log
            WHERE id = :import_id
            """),
            {"import_id": import_id}
        ).fetchone()
        
        assert created_entry is not None
        assert created_entry[0] == "compat_test_create.csv"
        assert created_entry[1] == "property"
        assert created_entry[2] == 42
        assert created_entry[3] == "COMPLETED"
        assert created_entry[4] == "Created through compatibility layer"