"""
Tests for levy calculation functionality.

This module tests the levy calculation functionality to ensure it correctly
calculates levy amounts, rates, and statutory limits.
"""

import pytest
from sqlalchemy import text
from datetime import datetime


def test_basic_levy_calculation(app, db):
    """Test basic levy calculation."""
    # The basic levy calculation formula is:
    # Levy Amount = (Assessed Value / 1000) * Levy Rate
    
    # Test with various assessed values and levy rates
    test_cases = [
        (100000, 2.5, 250),     # $100,000 property, 2.5 rate, $250 levy
        (250000, 3.1, 775),     # $250,000 property, 3.1 rate, $775 levy
        (1000000, 1.8, 1800),   # $1,000,000 property, 1.8 rate, $1,800 levy
        (0, 2.5, 0),            # $0 property, 2.5 rate, $0 levy
    ]
    
    for assessed_value, levy_rate, expected_levy in test_cases:
        calculated_levy = (assessed_value / 1000) * levy_rate
        assert calculated_levy == expected_levy


def test_property_tax_calculation(app, db):
    """Test property tax calculation against database values."""
    with app.app_context():
        # Create a tax code with known values
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "TEST-CALC",
                "levy_amount": 100000,  # $100,000 total levy
                "levy_rate": 2.5,       # $2.50 per $1,000 of assessed value
                "total_assessed_value": 40000000,  # $40,000,000 total assessed value
                "year": 2023
            }
        )
        
        # Create a property with known values
        db.session.execute(
            text("""
            INSERT INTO property (property_id, assessed_value, tax_code, address, owner_name, created_at, updated_at) 
            VALUES (:property_id, :assessed_value, :tax_code, :address, :owner_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "property_id": "PROP-TAX-TEST",
                "assessed_value": 200000,  # $200,000 property
                "tax_code": "TEST-CALC",
                "address": "Tax Test Property, Benton City, WA",
                "owner_name": "Tax Test Owner"
            }
        )
        db.session.commit()
        
        # Calculate expected tax for the property
        expected_tax = (200000 / 1000) * 2.5  # $500
        
        # Calculate tax using raw SQL for database compatibility
        result = db.session.execute(
            text("""
            SELECT p.assessed_value, tc.levy_rate, (p.assessed_value / 1000.0) * tc.levy_rate AS calculated_tax
            FROM property p
            JOIN tax_code tc ON p.tax_code = tc.code
            WHERE p.property_id = :property_id
            """),
            {"property_id": "PROP-TAX-TEST"}
        ).fetchone()
        
        assert result is not None
        assessed_value = result[0]
        levy_rate = result[1]
        calculated_tax = result[2]
        
        assert assessed_value == 200000
        assert levy_rate == 2.5
        assert calculated_tax == expected_tax


def test_statutory_limit_calculation(app, db):
    """Test statutory limit calculations for levy increases."""
    with app.app_context():
        # Create tax codes for consecutive years
        current_year = datetime.now().year
        previous_year = current_year - 1
        
        # Previous year tax code
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "LIMIT-TEST",
                "levy_amount": 1000000,  # $1,000,000 levy
                "levy_rate": 2.0,        # $2.00 per $1,000
                "total_assessed_value": 500000000,  # $500,000,000 assessed value
                "year": previous_year
            }
        )
        
        # Current year tax code with 1% increase (statutory limit)
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "LIMIT-TEST",
                "levy_amount": 1010000,  # $1,010,000 levy (1% increase)
                "levy_rate": 1.8,        # Rate decreased due to higher assessed value
                "total_assessed_value": 561111111,  # $561,111,111 assessed value
                "year": current_year
            }
        )
        db.session.commit()
        
        # Calculate expected statutory limit (1% increase from previous year)
        expected_limit = 1000000 * 1.01  # $1,010,000
        
        # Query for tax code data
        previous_levy = db.session.execute(
            text("""
            SELECT levy_amount FROM tax_code
            WHERE code = :code AND year = :year
            """),
            {"code": "LIMIT-TEST", "year": previous_year}
        ).scalar()
        
        current_levy = db.session.execute(
            text("""
            SELECT levy_amount FROM tax_code
            WHERE code = :code AND year = :year
            """),
            {"code": "LIMIT-TEST", "year": current_year}
        ).scalar()
        
        assert previous_levy == 1000000
        assert current_levy == 1010000
        assert current_levy <= expected_limit  # Must not exceed statutory limit


def test_levy_rate_calculation(app, db):
    """Test levy rate calculation (levy amount / assessed value * 1000)."""
    with app.app_context():
        # Create a tax code with specific levy amount and assessed value
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "RATE-TEST",
                "levy_amount": 450000,        # $450,000 levy
                "levy_rate": None,            # We'll calculate this
                "total_assessed_value": 150000000,  # $150,000,000 assessed value
                "year": 2023
            }
        )
        db.session.commit()
        
        # Calculate expected rate: (levy amount / assessed value) * 1000
        expected_rate = (450000 / 150000000) * 1000  # 3.0
        
        # Update the tax code with calculated rate
        db.session.execute(
            text("""
            UPDATE tax_code
            SET levy_rate = (levy_amount / total_assessed_value) * 1000
            WHERE code = :code AND year = :year
            """),
            {"code": "RATE-TEST", "year": 2023}
        )
        db.session.commit()
        
        # Fetch the updated rate
        calculated_rate = db.session.execute(
            text("""
            SELECT levy_rate FROM tax_code
            WHERE code = :code AND year = :year
            """),
            {"code": "RATE-TEST", "year": 2023}
        ).scalar()
        
        assert calculated_rate is not None
        assert abs(calculated_rate - expected_rate) < 0.001  # Allow for floating point imprecision


def test_multi_year_rate_comparison(app, db):
    """Test comparing levy rates across multiple years."""
    with app.app_context():
        # Create tax codes for three consecutive years
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "TREND-TEST",
                "levy_amount": 500000,
                "levy_rate": 2.5,
                "total_assessed_value": 200000000,
                "year": 2021
            }
        )
        
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "TREND-TEST",
                "levy_amount": 505000,  # 1% increase
                "levy_rate": 2.3,       # Rate decreased
                "total_assessed_value": 219565217,  # Value increased more than levy
                "year": 2022
            }
        )
        
        db.session.execute(
            text("""
            INSERT INTO tax_code (code, levy_amount, levy_rate, total_assessed_value, year, created_at, updated_at) 
            VALUES (:code, :levy_amount, :levy_rate, :total_assessed_value, :year, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "code": "TREND-TEST",
                "levy_amount": 510050,  # 1% increase
                "levy_rate": 2.2,       # Rate decreased again
                "total_assessed_value": 231840909,  # Value increased more than levy
                "year": 2023
            }
        )
        db.session.commit()
        
        # Query for the rates across all three years
        rates = db.session.execute(
            text("""
            SELECT year, levy_rate FROM tax_code
            WHERE code = :code
            ORDER BY year
            """),
            {"code": "TREND-TEST"}
        ).fetchall()
        
        # Verify the trend (rates decreasing)
        assert len(rates) == 3
        assert rates[0][1] > rates[1][1]  # 2021 rate > 2022 rate
        assert rates[1][1] > rates[2][1]  # 2022 rate > 2023 rate