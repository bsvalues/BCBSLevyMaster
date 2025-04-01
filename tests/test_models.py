"""
Tests for database models.
"""

import pytest
from datetime import datetime
from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog


def test_property_model(db):
    """Test Property model creation and constraints."""
    # Create a property
    property = Property(
        property_id="TEST-1234",
        assessed_value=275000.50,
        tax_code="00150"
    )
    db.session.add(property)
    db.session.commit()
    
    # Query the property
    queried_property = Property.query.filter_by(property_id="TEST-1234").first()
    
    # Assertions
    assert queried_property is not None
    assert queried_property.property_id == "TEST-1234"
    assert queried_property.assessed_value == 275000.50
    assert queried_property.tax_code == "00150"
    assert isinstance(queried_property.created_at, datetime)
    assert isinstance(queried_property.updated_at, datetime)
    
    # Test string representation
    assert str(queried_property) is not None


def test_tax_code_model(db):
    """Test TaxCode model creation and constraints."""
    # Create a tax code
    tax_code = TaxCode(
        code="00150",
        levy_amount=750000,
        levy_rate=3.25,
        previous_year_rate=3.15,
        total_assessed_value=230769230.77
    )
    db.session.add(tax_code)
    db.session.commit()
    
    # Query the tax code
    queried_tax_code = TaxCode.query.filter_by(code="00150").first()
    
    # Assertions
    assert queried_tax_code is not None
    assert queried_tax_code.code == "00150"
    assert queried_tax_code.levy_amount == 750000
    assert queried_tax_code.levy_rate == 3.25
    assert queried_tax_code.previous_year_rate == 3.15
    assert queried_tax_code.total_assessed_value == 230769230.77
    assert isinstance(queried_tax_code.created_at, datetime)
    assert isinstance(queried_tax_code.updated_at, datetime)
    
    # Test string representation
    assert str(queried_tax_code) is not None


def test_tax_district_model(db):
    """Test TaxDistrict model creation and constraints."""
    # Create a tax district
    tax_district = TaxDistrict(
        tax_district_id=5,
        year=2024,
        levy_code="00150",
        linked_levy_code="00160"
    )
    db.session.add(tax_district)
    db.session.commit()
    
    # Query the tax district
    queried_tax_district = TaxDistrict.query.filter_by(
        tax_district_id=5,
        year=2024,
        levy_code="00150",
        linked_levy_code="00160"
    ).first()
    
    # Assertions
    assert queried_tax_district is not None
    assert queried_tax_district.tax_district_id == 5
    assert queried_tax_district.year == 2024
    assert queried_tax_district.levy_code == "00150"
    assert queried_tax_district.linked_levy_code == "00160"
    assert isinstance(queried_tax_district.created_at, datetime)
    assert isinstance(queried_tax_district.updated_at, datetime)
    
    # Test string representation
    assert str(queried_tax_district) is not None
    
    # Test unique constraint
    duplicate = TaxDistrict(
        tax_district_id=5,
        year=2024,
        levy_code="00150",
        linked_levy_code="00160"
    )
    db.session.add(duplicate)
    
    # Assert that adding a duplicate violates the unique constraint
    with pytest.raises(Exception):
        db.session.commit()
    
    # Rollback the failed transaction
    db.session.rollback()


def test_import_log_model(db):
    """Test ImportLog model creation and querying."""
    # Create an import log
    import_log = ImportLog(
        filename="test_file.csv",
        rows_imported=100,
        rows_skipped=5,
        warnings="Some sample warnings",
        import_type="property"
    )
    db.session.add(import_log)
    db.session.commit()
    
    # Query the import log
    queried_log = ImportLog.query.filter_by(filename="test_file.csv").first()
    
    # Assertions
    assert queried_log is not None
    assert queried_log.filename == "test_file.csv"
    assert queried_log.rows_imported == 100
    assert queried_log.rows_skipped == 5
    assert queried_log.warnings == "Some sample warnings"
    assert queried_log.import_type == "property"
    assert isinstance(queried_log.import_date, datetime)
    
    # Test string representation
    assert str(queried_log) is not None


def test_export_log_model(db):
    """Test ExportLog model creation and querying."""
    # Create an export log
    export_log = ExportLog(
        filename="test_export.csv",
        rows_exported=150
    )
    db.session.add(export_log)
    db.session.commit()
    
    # Query the export log
    queried_log = ExportLog.query.filter_by(filename="test_export.csv").first()
    
    # Assertions
    assert queried_log is not None
    assert queried_log.filename == "test_export.csv"
    assert queried_log.rows_exported == 150
    assert isinstance(queried_log.export_date, datetime)
    
    # Test string representation
    assert str(queried_log) is not None