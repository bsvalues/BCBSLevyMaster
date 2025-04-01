"""
Tests for the enhanced levy rate calculator functionality.
"""
import pytest
import math
from decimal import Decimal, ROUND_HALF_UP

from app import app, db
from models import Property, TaxCode
from utils.levy_utils import (
    calculate_levy_rates, 
    apply_statutory_limits,
    calculate_property_tax,
    simulate_levy_scenarios,
    calculate_historical_comparison
)

# Helper function to round to 4 decimal places (same as application code)
def round_to_4(value):
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


class TestLevyCalculator:
    """Test suite for levy calculator functionality."""

    def test_levy_rate_calculation_accuracy(self, db):
        """Test that levy rates are calculated correctly based on assessed values and levy amounts."""
        # Create test tax codes with assessed values
        tax_codes = [
            TaxCode(code='100', total_assessed_value=10000000.0, levy_amount=None, levy_rate=None),
            TaxCode(code='200', total_assessed_value=5000000.0, levy_amount=None, levy_rate=None),
            TaxCode(code='300', total_assessed_value=20000000.0, levy_amount=None, levy_rate=None),
        ]
        
        for tc in tax_codes:
            db.session.add(tc)
        db.session.commit()
        
        # Define levy amounts for testing
        levy_amounts = {
            '100': 100000.0,  # Expected rate: 10.0000
            '200': 75000.0,   # Expected rate: 15.0000
            '300': 140000.0,  # Expected rate: 7.0000
        }
        
        # Calculate levy rates
        rates = calculate_levy_rates(levy_amounts)
        
        # Verify rates are correctly calculated 
        # (rate = levy_amount / (total_assessed_value / 1000))
        assert round_to_4(rates.get('100')) == round_to_4(10.0)
        assert round_to_4(rates.get('200')) == round_to_4(15.0)
        assert round_to_4(rates.get('300')) == round_to_4(7.0)
    
    def test_statutory_limit_application(self, db):
        """Test that statutory limits are correctly applied to calculated rates."""
        # Create test tax codes with previous year rates
        tax_codes = [
            TaxCode(code='100', total_assessed_value=10000000.0, levy_amount=None, 
                   levy_rate=None, previous_year_rate=5.0),
            TaxCode(code='200', total_assessed_value=5000000.0, levy_amount=None, 
                   levy_rate=None, previous_year_rate=10.0),
            TaxCode(code='300', total_assessed_value=20000000.0, levy_amount=None, 
                   levy_rate=None, previous_year_rate=2.0),
        ]
        
        for tc in tax_codes:
            db.session.add(tc)
        db.session.commit()
        
        # Test rates before applying limits
        original_rates = {
            '100': 10.0,      # Exceeds previous year by >101%
            '200': 10.1,      # Within 101% of previous year
            '300': 6.0,       # Exceeds $5.90 limit and previous year
        }
        
        # Apply statutory limits to the rates
        limited_rates = apply_statutory_limits(original_rates)
        
        # Check rate limitations
        # - 101% cap of previous year rate (5.0 * 1.01 = 5.05)
        assert round_to_4(limited_rates.get('100')) == round_to_4(5.05)
        
        # - Within 101% cap, so unchanged
        assert round_to_4(limited_rates.get('200')) == round_to_4(10.1)
        
        # - Exceeds both previous year rate and $5.90 max, should be limited to $5.90
        assert round_to_4(limited_rates.get('300')) == round_to_4(5.90)
    
    def test_property_tax_calculation(self, db):
        """Test tax calculation for a specific property."""
        # Create a test tax code
        tax_code = TaxCode(code='400', levy_rate=12.5, total_assessed_value=50000000.0)
        db.session.add(tax_code)
        db.session.commit()
        
        # Create a test property
        property_obj = Property(
            property_id='PROP-001',
            assessed_value=250000.0,
            tax_code='400'
        )
        db.session.add(property_obj)
        db.session.commit()
        
        # Calculate property tax
        tax_amount = calculate_property_tax(property_obj)
        
        # Expected tax: (assessed_value / 1000) * levy_rate
        expected_tax = (250000.0 / 1000) * 12.5
        
        # Verify tax calculation
        assert round_to_4(tax_amount) == round_to_4(expected_tax)
    
    def test_property_tax_calculation_no_rate(self, db):
        """Test tax calculation when levy rate is not available."""
        # Create a test tax code with no levy rate
        tax_code = TaxCode(code='500', levy_rate=None, total_assessed_value=30000000.0)
        db.session.add(tax_code)
        db.session.commit()
        
        # Create a test property
        property_obj = Property(
            property_id='PROP-002',
            assessed_value=300000.0,
            tax_code='500'
        )
        db.session.add(property_obj)
        db.session.commit()
        
        # Calculate property tax (should return None when rate is not available)
        tax_amount = calculate_property_tax(property_obj)
        
        # Verify tax calculation returns None
        assert tax_amount is None
    
    def test_historical_comparison(self, db):
        """Test comparison between current and historical rates."""
        # Create test tax codes with previous year rates and current rates
        tax_codes = [
            TaxCode(code='600', levy_rate=10.0, previous_year_rate=9.5),
            TaxCode(code='700', levy_rate=8.0, previous_year_rate=8.5),
            TaxCode(code='800', levy_rate=6.0, previous_year_rate=6.0),
        ]
        
        for tc in tax_codes:
            db.session.add(tc)
        db.session.commit()
        
        # Calculate historical comparison
        comparison = calculate_historical_comparison()
        
        # Verify comparison results
        assert len(comparison) >= 3
        
        for comp in comparison:
            if comp['code'] == '600':
                assert comp['change_pct'] == pytest.approx(5.26, 0.01)  # (10.0 - 9.5) / 9.5 * 100
                assert comp['direction'] == 'increase'
            elif comp['code'] == '700':
                assert comp['change_pct'] == pytest.approx(-5.88, 0.01)  # (8.0 - 8.5) / 8.5 * 100
                assert comp['direction'] == 'decrease'
            elif comp['code'] == '800':
                assert comp['change_pct'] == pytest.approx(0.0, 0.01)
                assert comp['direction'] == 'unchanged'
    
    def test_levy_scenario_simulation(self, db):
        """Test levy scenario simulation with different amounts."""
        # Create test tax codes
        tax_codes = [
            TaxCode(code='900', total_assessed_value=15000000.0, levy_amount=150000.0, 
                   levy_rate=10.0, previous_year_rate=9.8),
        ]
        
        for tc in tax_codes:
            db.session.add(tc)
        db.session.commit()
        
        # Define scenarios to test
        scenarios = [
            {'name': 'Baseline', 'adjustments': {}},
            {'name': '5% Increase', 'adjustments': {'900': 1.05}},  # 5% increase
            {'name': '10% Increase', 'adjustments': {'900': 1.10}},  # 10% increase
        ]
        
        # Run simulation
        results = simulate_levy_scenarios(scenarios)
        
        # Verify simulation results
        assert len(results) == 3
        
        # Check baseline scenario
        baseline = next((s for s in results if s['name'] == 'Baseline'), None)
        assert baseline is not None
        assert round_to_4(baseline['scenarios']['900']['rate']) == round_to_4(10.0)
        
        # Check 5% increase scenario
        increase5 = next((s for s in results if s['name'] == '5% Increase'), None)
        assert increase5 is not None
        # 5% more levy amount should yield 5% higher rate
        assert round_to_4(increase5['scenarios']['900']['rate']) == round_to_4(10.5)
        
        # Check if limit was applied (should be capped at 101% of previous year rate)
        if increase5['scenarios']['900'].get('limited') is True:
            assert round_to_4(increase5['scenarios']['900']['limited_rate']) == round_to_4(9.8 * 1.01)
            
        # Check 10% increase scenario
        increase10 = next((s for s in results if s['name'] == '10% Increase'), None)
        assert increase10 is not None
        # 10% more levy amount should yield 10% higher rate
        assert round_to_4(increase10['scenarios']['900']['rate']) == round_to_4(11.0)
        
        # Check if limit was applied
        if increase10['scenarios']['900'].get('limited') is True:
            assert round_to_4(increase10['scenarios']['900']['limited_rate']) == round_to_4(9.8 * 1.01)