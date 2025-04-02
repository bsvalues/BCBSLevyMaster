"""
Test database schema compatibility between ORM models and actual database.
"""

import pytest
import os
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, text
from sqlalchemy.orm import declarative_base
from app import db

def test_import_log_schema_compatibility(app):
    """Test that the ImportLog model matches the actual database schema."""
    with app.app_context():
        # Get database URI from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            pytest.skip("DATABASE_URL environment variable not set")
            
        # Create an engine to connect to the actual database
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Verify the import_log table exists
        assert 'import_log' in inspector.get_table_names()
        
        # Get the columns from the actual database
        columns = {column['name']: column for column in inspector.get_columns('import_log')}
        
        # Verify essential columns exist
        assert 'id' in columns
        assert 'filename' in columns
        assert 'import_type' in columns
        assert 'status' in columns
        
        # Check specific columns based on our current knowledge of schema issues
        # Verify records_imported exists (not record_count)
        assert 'records_imported' in columns
        assert 'records_skipped' in columns

def test_tax_code_schema_compatibility(app):
    """Test that the TaxCode model matches the actual database schema."""
    with app.app_context():
        # Get database URI from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            pytest.skip("DATABASE_URL environment variable not set")
            
        # Create an engine to connect to the actual database
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Verify the tax_code table exists
        assert 'tax_code' in inspector.get_table_names()
        
        # Get the columns from the actual database
        columns = {column['name']: column for column in inspector.get_columns('tax_code')}
        
        # Verify essential columns exist
        assert 'id' in columns
        assert 'code' in columns  # Not tax_code in actual DB
        assert 'levy_amount' in columns
        assert 'levy_rate' in columns
        assert 'total_assessed_value' in columns
        assert 'year' in columns

def test_property_schema_compatibility(app):
    """Test that the Property model matches the actual database schema."""
    with app.app_context():
        # Get database URI from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            pytest.skip("DATABASE_URL environment variable not set")
            
        # Create an engine to connect to the actual database
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Verify the property table exists
        assert 'property' in inspector.get_table_names()
        
        # Get the columns from the actual database
        columns = {column['name']: column for column in inspector.get_columns('property')}
        
        # Verify essential columns exist
        assert 'id' in columns
        assert 'property_id' in columns  # Not parcel_id in actual DB
        assert 'assessed_value' in columns
        assert 'tax_code' in columns  # Direct reference to tax_code.code, not tax_code_id
        assert 'year' in columns

def test_raw_sql_query_compatibility(app):
    """Test that raw SQL queries work properly with the actual schema."""
    with app.app_context():
        # Test import_log query
        try:
            result = db.session.execute(text(
                "SELECT id, filename, records_imported, status, import_date FROM import_log LIMIT 5"
            ))
            # If no error, we're good
            assert True
        except Exception as e:
            pytest.fail(f"Raw SQL query for import_log failed: {str(e)}")
        
        # Test tax_code query
        try:
            result = db.session.execute(text(
                "SELECT id, code, levy_amount, levy_rate, total_assessed_value FROM tax_code LIMIT 5"
            ))
            # If no error, we're good
            assert True
        except Exception as e:
            pytest.fail(f"Raw SQL query for tax_code failed: {str(e)}")
        
        # Test property query
        try:
            result = db.session.execute(text(
                "SELECT id, property_id, assessed_value, tax_code FROM property LIMIT 5"
            ))
            # If no error, we're good
            assert True
        except Exception as e:
            pytest.fail(f"Raw SQL query for property failed: {str(e)}")