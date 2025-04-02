
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
