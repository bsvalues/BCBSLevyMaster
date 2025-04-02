
"""Test core levy calculation functionality."""
import pytest
from utils.levy_utils import calculate_levy_rate
from models import TaxCode, Property

def test_levy_rate_calculation():
    """Test basic levy rate calculation."""
    assessed_value = 1000000  # $1M assessed value
    levy_amount = 30000      # $30K levy amount
    expected_rate = 3.0      # 3% rate
    
    calculated_rate = calculate_levy_rate(levy_amount, assessed_value)
    assert abs(calculated_rate - expected_rate) < 0.0001

def test_zero_assessed_value():
    """Test handling of zero assessed value."""
    with pytest.raises(ValueError):
        calculate_levy_rate(1000, 0)

def test_negative_values():
    """Test handling of negative values."""
    with pytest.raises(ValueError):
        calculate_levy_rate(-1000, 1000)
    with pytest.raises(ValueError):
        calculate_levy_rate(1000, -1000)

def test_large_numbers():
    """Test handling of large numbers."""
    # Test with $1B assessed value and $30M levy
    calculated_rate = calculate_levy_rate(30000000, 1000000000)
    assert abs(calculated_rate - 3.0) < 0.0001

def test_statutory_limit_compliance():
    """Test statutory limit compliance checks."""
    test_cases = [
        (1000000, 25000, 2.5),    # Within limit
        (1000000, 50000, 5.0),    # At limit
        (1000000, 70000, 5.9),    # Should be capped
    ]
    
    for assessed_value, levy_amount, expected_rate in test_cases:
        rate = calculate_levy_rate(levy_amount, assessed_value)
        limited_rate = apply_statutory_limits(rate)
        assert abs(limited_rate - expected_rate) < 0.0001

def test_complex_rate_scenarios():
    """Test complex scenarios with multiple calculations."""
    # Test sequential calculations
    base_value = 2000000
    base_levy = 50000
    base_rate = calculate_levy_rate(base_levy, base_value)
    assert abs(base_rate - 2.5) < 0.0001
    
    # Test with 5% increase
    increased_levy = base_levy * 1.05
    new_rate = calculate_levy_rate(increased_levy, base_value)
    assert abs(new_rate - 2.625) < 0.0001
    
    # Verify statutory limits still apply
    limited_rate = apply_statutory_limits(new_rate)
    assert abs(limited_rate - 2.625) < 0.0001

def test_multi_year_levy_comparison():
    """Test levy comparisons across multiple years."""
    base_year_data = {
        'assessed_value': 5000000,
        'levy_amount': 150000,
        'year': 2024
    }
    
    comparison_years = [
        {'assessed_value': 5250000, 'levy_amount': 162750, 'year': 2025},  # 5% increase
        {'assessed_value': 5512500, 'levy_amount': 176400, 'year': 2026},  # 5% increase
        {'assessed_value': 5788125, 'levy_amount': 191700, 'year': 2027}   # 5% increase
    ]
    
    # Calculate and verify base year rate
    base_rate = calculate_levy_rate(base_year_data['levy_amount'], 
                                  base_year_data['assessed_value'])
    assert abs(base_rate - 3.0) < 0.0001
    
    # Test each comparison year
    for year_data in comparison_years:
        rate = calculate_levy_rate(year_data['levy_amount'],
                                 year_data['assessed_value'])
        # Rate should remain constant at 3.0 despite value increases
        assert abs(rate - 3.0) < 0.0001

def test_levy_rate_rounding():
    """Test levy rate rounding behavior."""
    test_cases = [
        (100000, 3001, 3.001),    # Test to 3 decimal places
        (100000, 3000.5, 3.001),  # Test rounding up
        (100000, 3000.4, 3.000),  # Test rounding down
        (100000, 3000.0, 3.000),  # Test exact value
    ]
    
    for assessed_value, levy_amount, expected_rate in test_cases:
        rate = calculate_levy_rate(levy_amount, assessed_value)
        assert abs(rate - expected_rate) < 0.0001

def test_levy_rate_validation():
    """Test levy rate validation with edge cases."""
    from utils.validation_framework import levy_consistency_validator
    
    test_cases = [
        # Valid cases
        {'levy_rate': 2.5, 'levy_amount': 25000, 'total_assessed_value': 10000000},
        {'levy_rate': 0.1, 'levy_amount': 100, 'total_assessed_value': 100000},
        
        # Edge cases
        {'levy_rate': 0.0, 'levy_amount': 0, 'total_assessed_value': 1000000},
        {'levy_rate': 5.9, 'levy_amount': 59000, 'total_assessed_value': 10000000},
        
        # Missing values should pass validation
        {'levy_rate': None, 'levy_amount': 1000, 'total_assessed_value': 100000},
        {'levy_rate': 2.5, 'levy_amount': None, 'total_assessed_value': 100000}
    ]
    
    for case in test_cases:
        assert levy_consistency_validator(case), f"Validation failed for case: {case}"

def test_levy_edge_cases():
    """Test edge cases for levy calculations."""
    test_cases = [
        # Minimum possible values
        (100, 1, 1.000),  # $100 value, $1 levy
        # Large values
        (1000000000, 50000000, 5.000),  # $1B value, $50M levy
        # Precision testing
        (100000, 3333.33, 3.333),  # Test decimal handling
        (200000, 6666.67, 3.333),  # Test rounding consistency
    ]
    
    for value, levy, expected in test_cases:
        rate = calculate_levy_rate(levy, value)
        assert abs(rate - expected) < 0.0001, f"Failed for case: value={value}, levy={levy}"
