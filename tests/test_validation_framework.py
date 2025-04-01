"""
Tests for the data validation framework.

This module contains tests for the data validation capabilities, ensuring that:
1. Validation rules can be defined and enforced
2. Different data types are properly validated
3. Validation errors are properly reported
4. Custom validation rules can be added
"""

import pytest
from utils.validation_framework import (
    Validator, ValidationError, ValidationRule,
    IntegerRule, FloatRule, StringRule, DateRule, RegexRule, 
    RangeRule, RequiredRule, UniqueRule
)


class TestValidationRules:
    """Tests for individual validation rules."""

    def test_required_rule(self):
        """Test RequiredRule correctly validates required fields."""
        rule = RequiredRule()
        
        # Should pass with any non-None value
        assert rule.validate("test") is True
        assert rule.validate(0) is True
        assert rule.validate(False) is True
        
        # Should fail with None
        with pytest.raises(ValidationError):
            rule.validate(None)
    
    def test_integer_rule(self):
        """Test IntegerRule correctly validates integers."""
        rule = IntegerRule()
        
        # Should pass with integers
        assert rule.validate(42) is True
        assert rule.validate(0) is True
        assert rule.validate(-10) is True
        
        # Should fail with non-integers
        with pytest.raises(ValidationError):
            rule.validate("42")
        with pytest.raises(ValidationError):
            rule.validate(42.5)
    
    def test_float_rule(self):
        """Test FloatRule correctly validates floating-point numbers."""
        rule = FloatRule()
        
        # Should pass with numbers
        assert rule.validate(42.5) is True
        assert rule.validate(0.0) is True
        assert rule.validate(-10.5) is True
        assert rule.validate(42) is True  # Integers should be valid floats
        
        # Should fail with non-numbers
        with pytest.raises(ValidationError):
            rule.validate("42.5")
    
    def test_string_rule(self):
        """Test StringRule correctly validates strings."""
        rule = StringRule()
        
        # Should pass with strings
        assert rule.validate("test") is True
        assert rule.validate("") is True
        
        # Should fail with non-strings
        with pytest.raises(ValidationError):
            rule.validate(42)
    
    def test_regex_rule(self):
        """Test RegexRule correctly validates against patterns."""
        # Tax code pattern (simple example: 5-6 digits)
        rule = RegexRule(pattern=r"^\d{5,6}$")
        
        # Should pass with matching patterns
        assert rule.validate("12345") is True
        assert rule.validate("123456") is True
        
        # Should fail with non-matching patterns
        with pytest.raises(ValidationError):
            rule.validate("1234")  # Too short
        with pytest.raises(ValidationError):
            rule.validate("1234567")  # Too long
        with pytest.raises(ValidationError):
            rule.validate("ABCDE")  # Not digits
    
    def test_range_rule(self):
        """Test RangeRule correctly validates value ranges."""
        # Levy rate should be positive and less than 1
        rule = RangeRule(min_value=0.0, max_value=1.0, include_min=True, include_max=False)
        
        # Should pass with values in range
        assert rule.validate(0.0) is True
        assert rule.validate(0.5) is True
        assert rule.validate(0.9999) is True
        
        # Should fail with values outside range
        with pytest.raises(ValidationError):
            rule.validate(-0.1)  # Below min
        with pytest.raises(ValidationError):
            rule.validate(1.0)  # At max but not included
        with pytest.raises(ValidationError):
            rule.validate(1.1)  # Above max
    
    def test_date_rule(self):
        """Test DateRule correctly validates dates."""
        from datetime import date
        rule = DateRule(min_date=date(2000, 1, 1), max_date=date(2030, 12, 31))
        
        # Should pass with dates in range
        assert rule.validate(date(2000, 1, 1)) is True
        assert rule.validate(date(2020, 6, 15)) is True
        assert rule.validate(date(2030, 12, 31)) is True
        
        # Should fail with dates outside range
        with pytest.raises(ValidationError):
            rule.validate(date(1999, 12, 31))  # Before min
        with pytest.raises(ValidationError):
            rule.validate(date(2031, 1, 1))  # After max


class TestValidator:
    """Tests for the Validator class that combines multiple rules."""

    def test_simple_validation(self):
        """Test validation of a simple object with basic rules."""
        validator = Validator({
            "tax_code": [RequiredRule(), StringRule(), RegexRule(r"^\d{5,6}$")],
            "levy_rate": [RequiredRule(), FloatRule(), RangeRule(0.0, 1.0)],
            "year": [RequiredRule(), IntegerRule(), RangeRule(2000, 2100)]
        })
        
        # Valid data should pass
        valid_data = {
            "tax_code": "12345",
            "levy_rate": 0.154,
            "year": 2024
        }
        assert validator.validate(valid_data) is True
        
        # Invalid tax_code should fail
        invalid_tax_code = valid_data.copy()
        invalid_tax_code["tax_code"] = "ABC"
        with pytest.raises(ValidationError) as exc:
            validator.validate(invalid_tax_code)
        assert "tax_code" in str(exc.value)
        
        # Invalid levy_rate should fail
        invalid_rate = valid_data.copy()
        invalid_rate["levy_rate"] = -0.1
        with pytest.raises(ValidationError) as exc:
            validator.validate(invalid_rate)
        assert "levy_rate" in str(exc.value)
        
        # Invalid year should fail
        invalid_year = valid_data.copy()
        invalid_year["year"] = 1950
        with pytest.raises(ValidationError) as exc:
            validator.validate(invalid_year)
        assert "year" in str(exc.value)
    
    def test_missing_fields(self):
        """Test validation when required fields are missing."""
        validator = Validator({
            "tax_code": [RequiredRule()],
            "levy_rate": [RequiredRule()],
            "year": [RequiredRule()]
        })
        
        # Missing required field should fail
        missing_field = {
            "tax_code": "12345",
            "year": 2024
            # levy_rate is missing
        }
        with pytest.raises(ValidationError) as exc:
            validator.validate(missing_field)
        assert "levy_rate" in str(exc.value)
    
    def test_custom_rule(self):
        """Test validation with a custom rule."""
        # Create a custom rule that ensures tax codes from specific districts
        class DistrictRule(ValidationRule):
            def __init__(self, allowed_districts):
                self.allowed_districts = allowed_districts
                
            def validate(self, value):
                # First 2 digits represent district
                district = value[:2]
                if district not in self.allowed_districts:
                    raise ValidationError(f"District code must be one of: {', '.join(self.allowed_districts)}")
                return True
        
        validator = Validator({
            "tax_code": [RequiredRule(), StringRule(), RegexRule(r"^\d{5,6}$"), 
                         DistrictRule(["10", "20", "30"])]
        })
        
        # Valid district should pass
        assert validator.validate({"tax_code": "105123"}) is True
        
        # Invalid district should fail
        with pytest.raises(ValidationError) as exc:
            validator.validate({"tax_code": "405123"})
        assert "District code" in str(exc.value)
    
    def test_validate_collection(self):
        """Test validation of a collection of objects."""
        validator = Validator({
            "tax_code": [RequiredRule(), StringRule()],
            "levy_rate": [RequiredRule(), FloatRule(), RangeRule(0, 1)]
        })
        
        collection = [
            {"tax_code": "12345", "levy_rate": 0.154},
            {"tax_code": "23456", "levy_rate": 0.253},
            {"tax_code": "34567", "levy_rate": 1.1}  # Invalid levy_rate
        ]
        
        with pytest.raises(ValidationError) as exc:
            validator.validate_collection(collection)
        
        # Should provide info about which item failed
        assert "item #2" in str(exc.value) or "index 2" in str(exc.value)
        assert "levy_rate" in str(exc.value)
        
        # With strict=False, should return all errors rather than raising
        errors = validator.validate_collection(collection, strict=False)
        assert len(errors) == 1
        assert "levy_rate" in str(errors[0]['error'])
        assert errors[0]['index'] == 2


class TestValidationIntegraion:
    """Integration tests for validation in real-world scenarios."""
    
    def test_tax_code_validation(self):
        """Test validation of tax code data."""
        from utils.validation_framework import create_tax_code_validator
        
        validator = create_tax_code_validator()
        
        # Calculate a consistent value: levy_amount = levy_rate * total_assessed_value
        levy_rate = 0.154
        total_assessed_value = 9700000000
        levy_amount = levy_rate * total_assessed_value
        
        valid_tax_code = {
            "code": "12345",
            "levy_rate": levy_rate,
            "levy_amount": levy_amount,
            "total_assessed_value": total_assessed_value
        }
        
        # Valid data should pass
        assert validator.validate(valid_tax_code) is True
        
        # Test various invalid scenarios
        invalid_code = valid_tax_code.copy()
        invalid_code["code"] = "ABC"
        with pytest.raises(ValidationError):
            validator.validate(invalid_code)
        
        negative_rate = valid_tax_code.copy()
        negative_rate["levy_rate"] = -0.1
        with pytest.raises(ValidationError):
            validator.validate(negative_rate)
        
        # Levy amount should correspond roughly to rate * value
        inconsistent_amount = valid_tax_code.copy()
        inconsistent_amount["levy_amount"] = 5000000  # Too high for the rate and value
        with pytest.raises(ValidationError):
            validator.validate(inconsistent_amount)
    
    def test_property_validation(self):
        """Test validation of property data."""
        from utils.validation_framework import create_property_validator
        
        validator = create_property_validator()
        
        valid_property = {
            "property_id": "R12345678",
            "assessed_value": 450000,
            "tax_code": "12345"
        }
        
        # Valid data should pass
        assert validator.validate(valid_property) is True
        
        # Test various invalid scenarios
        invalid_id = valid_property.copy()
        invalid_id["property_id"] = "12345"  # Missing R prefix
        with pytest.raises(ValidationError):
            validator.validate(invalid_id)
        
        negative_value = valid_property.copy()
        negative_value["assessed_value"] = -100
        with pytest.raises(ValidationError):
            validator.validate(negative_value)
    
    def test_import_validation(self):
        """Test validation of import data."""
        from utils.validation_framework import create_import_validator
        
        validator = create_import_validator()
        
        valid_import = {
            "filename": "property_data_2024.csv",
            "row_count": 1000,
            "columns": ["property_id", "assessed_value", "tax_code"],
            "data_type": "property"
        }
        
        # Valid data should pass
        assert validator.validate(valid_import) is True
        
        # Test with invalid data
        invalid_type = valid_import.copy()
        invalid_type["data_type"] = "unknown"
        with pytest.raises(ValidationError):
            validator.validate(invalid_type)
        
        missing_columns = valid_import.copy()
        missing_columns["columns"] = ["property_id"]  # Missing required columns
        with pytest.raises(ValidationError):
            validator.validate(missing_columns)