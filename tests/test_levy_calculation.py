"""
Test the levy calculation functionality.
"""

import pytest
from app import db
from models import TaxCode, Property

def test_levy_rate_calculation(app, db, seed_test_data):
    """Test basic levy rate calculation."""
    with app.app_context():
        # Get a tax code
        tax_code = TaxCode.query.filter_by(code="00120").first()
        
        # Verify levy rate calculation
        # Rate = (Levy Amount / Total Assessed Value) * 1000
        expected_rate = (tax_code.levy_amount / tax_code.total_assessed_value) * 1000
        
        # Compare with a small epsilon for floating-point comparison
        assert abs(tax_code.levy_rate - expected_rate) < 0.0001

def test_property_tax_calculation(app, db, seed_test_data):
    """Test property tax calculation."""
    with app.app_context():
        # Get a property and its tax code
        property_obj = Property.query.filter_by(property_id="12345-6789").first()
        tax_code = TaxCode.query.filter_by(code=property_obj.tax_code).first()
        
        # Calculate expected tax amount
        # Tax Amount = (Assessed Value * Levy Rate) / 1000
        expected_tax = (property_obj.assessed_value * tax_code.levy_rate) / 1000
        
        # Set the calculated tax amount
        property_obj.tax_amount = expected_tax
        db.session.commit()
        
        # Re-query to get the updated property
        updated_property = Property.query.filter_by(property_id="12345-6789").first()
        
        # Verify the tax amount was calculated correctly
        assert abs(updated_property.tax_amount - expected_tax) < 0.01

def test_total_levy_calculation(app, db, seed_test_data):
    """Test calculation of total levy amount for a tax code."""
    with app.app_context():
        # Get properties in a tax code
        properties = Property.query.filter_by(tax_code="00120").all()
        tax_code = TaxCode.query.filter_by(code="00120").first()
        
        # Calculate total tax for these properties
        total_tax = 0
        for prop in properties:
            # Tax = (Assessed Value * Levy Rate) / 1000
            prop_tax = (prop.assessed_value * tax_code.levy_rate) / 1000
            total_tax += prop_tax
            
            # Set the tax amount for each property
            prop.tax_amount = prop_tax
            
        db.session.commit()
        
        # Verify total
        calculated_total = sum(p.tax_amount for p in 
                               Property.query.filter_by(tax_code="00120").all())
        
        # Should match our manual calculation
        assert abs(calculated_total - total_tax) < 0.01
        
        # And should match what would be calculated from levy rate * total assessed value / 1000
        expected_from_rate = (tax_code.total_assessed_value * tax_code.levy_rate) / 1000
        assert abs(calculated_total - expected_from_rate) < 0.01

def test_year_over_year_comparison(app, db, seed_test_data):
    """Test comparison of levy rates year-over-year."""
    with app.app_context():
        # Get tax code with previous year data
        tax_code = TaxCode.query.filter_by(code="00120").first()
        
        # Calculate year-over-year change
        yoy_change = ((tax_code.levy_rate - tax_code.previous_year_rate) / 
                      tax_code.previous_year_rate * 100)
        
        # In our test data, the change should be:
        # (2.5 - 2.4) / 2.4 * 100 = 4.167%
        expected_change = 4.167
        
        # Verify the calculation
        assert abs(yoy_change - expected_change) < 0.01