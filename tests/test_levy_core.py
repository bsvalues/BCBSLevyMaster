
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
