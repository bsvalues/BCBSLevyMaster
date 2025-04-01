"""
Tests for utility functions.
"""

import os
import pytest
import tempfile
import csv
import json
from utils.levy_utils import calculate_levy_rates, apply_statutory_limits, calculate_property_tax
from utils.import_utils import update_tax_code_totals
from utils.district_utils import get_linked_levy_codes
from models import Property, TaxCode, TaxDistrict


def test_calculate_levy_rates(db, seed_test_data):
    """Test calculation of levy rates."""
    # Set up test data
    levy_amounts = {
        "00120": 1200000,
        "00130": 600000
    }
    
    # Calculate levy rates
    levy_rates = calculate_levy_rates(levy_amounts)
    
    # Get the tax codes and verify their total_assessed_value is set
    tax_code_120 = TaxCode.query.filter_by(code="00120").first()
    tax_code_130 = TaxCode.query.filter_by(code="00130").first()
    
    assert tax_code_120 is not None
    assert tax_code_130 is not None
    assert tax_code_120.total_assessed_value is not None
    assert tax_code_130.total_assessed_value is not None
    
    # Calculate expected rates
    expected_rate_120 = (1200000 / tax_code_120.total_assessed_value) * 1000
    expected_rate_130 = (600000 / tax_code_130.total_assessed_value) * 1000
    
    # Verify rates
    assert levy_rates["00120"] == pytest.approx(expected_rate_120, rel=1e-2)
    assert levy_rates["00130"] == pytest.approx(expected_rate_130, rel=1e-2)


def test_apply_statutory_limits(db, seed_test_data):
    """Test application of statutory limits to levy rates."""
    # Create test levy rates
    levy_rates = {
        "00120": 3.0,  # Above previous year rate * 1.01 (2.4 * 1.01 = 2.424)
        "00130": 6.5   # Above $5.90 maximum
    }
    
    # Apply statutory limits
    limited_rates = apply_statutory_limits(levy_rates)
    
    # Get the tax codes
    tax_code_120 = TaxCode.query.filter_by(code="00120").first()
    tax_code_130 = TaxCode.query.filter_by(code="00130").first()
    
    # Verify 101% cap is applied
    expected_rate_120 = tax_code_120.previous_year_rate * 1.01
    assert limited_rates["00120"] == pytest.approx(expected_rate_120, rel=1e-2)
    
    # Verify $5.90 cap is applied
    assert limited_rates["00130"] == 5.90


def test_calculate_property_tax(db, seed_test_data):
    """Test calculation of property tax."""
    # Get a property and its tax code
    property = Property.query.filter_by(property_id="12345-6789").first()
    tax_code = TaxCode.query.filter_by(code=property.tax_code).first()
    
    # Calculate property tax
    tax = calculate_property_tax(property)
    
    # Calculate expected tax
    expected_tax = (property.assessed_value / 1000) * tax_code.levy_rate
    
    # Verify tax calculation
    assert tax == pytest.approx(expected_tax, rel=1e-2)


def test_update_tax_code_totals(db, seed_test_data):
    """Test updating tax code totals from property data."""
    # Get the initial assessed values
    initial_total_120 = TaxCode.query.filter_by(code="00120").first().total_assessed_value
    initial_total_130 = TaxCode.query.filter_by(code="00130").first().total_assessed_value
    
    # Add a new property
    new_property = Property(
        property_id="NEW-12345",
        assessed_value=500000,
        tax_code="00120"
    )
    db.session.add(new_property)
    db.session.commit()
    
    # Update tax code totals
    update_tax_code_totals()
    
    # Get the updated totals
    updated_total_120 = TaxCode.query.filter_by(code="00120").first().total_assessed_value
    updated_total_130 = TaxCode.query.filter_by(code="00130").first().total_assessed_value
    
    # Verify the totals are updated correctly
    assert updated_total_120 == initial_total_120 + 500000
    assert updated_total_130 == initial_total_130  # Should be unchanged


def test_get_linked_levy_codes(db, seed_test_data):
    """Test getting linked levy codes."""
    # Get linked levy codes for "00120"
    linked_codes = get_linked_levy_codes("00120", 2023)
    
    # Verify the linked code is found
    assert "00130" in linked_codes
    
    # Get linked levy codes for "00130"
    linked_codes = get_linked_levy_codes("00130", 2023)
    
    # Verify the linked code is found
    assert "00120" in linked_codes
    
    # Test with a non-existent levy code
    linked_codes = get_linked_levy_codes("NONEXISTENT", 2023)
    
    # Verify empty list is returned
    assert linked_codes == []
    
    # Test with a default year (should use most recent year)
    linked_codes = get_linked_levy_codes("00120")
    
    # Verify the linked code is found
    assert "00130" in linked_codes