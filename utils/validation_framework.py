"""
Data Validation Framework

This module provides a flexible framework for validating data across the application.
It allows for:
- Defining validation rules
- Applying rules to data models
- Validating data during import and processing
- Providing clear error messages
- Creating custom validation scenarios
"""

import re
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

# Set up logging
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised when data validation fails."""
    pass


class ValidationRule:
    """Base class for all validation rules."""
    
    def validate(self, value: Any) -> bool:
        """
        Validate the given value. Default implementation always passes.
        Override in subclasses for custom validation logic.
        
        Args:
            value: The value to validate
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        # Default: always passes validation
        return True


class RequiredRule(ValidationRule):
    """Rule that validates a value is not None."""
    
    def validate(self, value: Any) -> bool:
        """Validate that value is not None."""
        if value is None:
            raise ValidationError("Value is required")
        return True


class IntegerRule(ValidationRule):
    """Rule that validates a value is an integer."""
    
    def validate(self, value: Any) -> bool:
        """Validate that value is an integer."""
        if value is None:
            return True
        
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError("Value must be an integer")
        return True


class FloatRule(ValidationRule):
    """Rule that validates a value is a float or integer."""
    
    def validate(self, value: Any) -> bool:
        """Validate that value is a number."""
        if value is None:
            return True
        
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError("Value must be a number")
        return True


class StringRule(ValidationRule):
    """Rule that validates a value is a string."""
    
    def validate(self, value: Any) -> bool:
        """Validate that value is a string."""
        if value is None:
            return True
        
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")
        return True


class RegexRule(ValidationRule):
    """Rule that validates a string matches a regex pattern."""
    
    def __init__(self, pattern: str):
        """
        Initialize with regex pattern.
        
        Args:
            pattern: The regex pattern to match against
        """
        self.pattern = pattern
        self.regex = re.compile(pattern)
    
    def validate(self, value: Any) -> bool:
        """Validate that value matches the pattern."""
        if value is None:
            return True
        
        if not isinstance(value, str):
            raise ValidationError(f"Value must be a string to match pattern {self.pattern}")
        
        if not self.regex.match(value):
            raise ValidationError(f"Value must match pattern {self.pattern}")
        
        return True


class RangeRule(ValidationRule):
    """Rule that validates a value is within a specified range."""
    
    def __init__(
        self, 
        min_value: Optional[Union[int, float]] = None, 
        max_value: Optional[Union[int, float]] = None,
        include_min: bool = True,
        include_max: bool = True
    ):
        """
        Initialize with range parameters.
        
        Args:
            min_value: Minimum allowed value (or None for no minimum)
            max_value: Maximum allowed value (or None for no maximum)
            include_min: Whether the minimum value is included in the range
            include_max: Whether the maximum value is included in the range
        """
        self.min_value = min_value
        self.max_value = max_value
        self.include_min = include_min
        self.include_max = include_max
    
    def validate(self, value: Any) -> bool:
        """Validate that value is within the range."""
        if value is None:
            return True
        
        if not isinstance(value, (int, float)):
            raise ValidationError("Value must be a number for range validation")
        
        if self.min_value is not None:
            if self.include_min:
                if value < self.min_value:
                    raise ValidationError(f"Value must be greater than or equal to {self.min_value}")
            else:
                if value <= self.min_value:
                    raise ValidationError(f"Value must be greater than {self.min_value}")
        
        if self.max_value is not None:
            if self.include_max:
                if value > self.max_value:
                    raise ValidationError(f"Value must be less than or equal to {self.max_value}")
            else:
                if value >= self.max_value:
                    raise ValidationError(f"Value must be less than {self.max_value}")
        
        return True


class DateRule(ValidationRule):
    """Rule that validates a date is within a specified range."""
    
    def __init__(
        self, 
        min_date: Optional[date] = None, 
        max_date: Optional[date] = None
    ):
        """
        Initialize with date range parameters.
        
        Args:
            min_date: Minimum allowed date (or None for no minimum)
            max_date: Maximum allowed date (or None for no maximum)
        """
        self.min_date = min_date
        self.max_date = max_date
    
    def validate(self, value: Any) -> bool:
        """Validate that date is within the range."""
        if value is None:
            return True
        
        if not isinstance(value, date):
            raise ValidationError("Value must be a date for date validation")
        
        if self.min_date is not None and value < self.min_date:
            raise ValidationError(f"Date must be on or after {self.min_date.isoformat()}")
        
        if self.max_date is not None and value > self.max_date:
            raise ValidationError(f"Date must be on or before {self.max_date.isoformat()}")
        
        return True


class UniqueRule(ValidationRule):
    """Rule that validates a value is unique within a collection."""
    
    def __init__(self, collection_getter: Callable[[], List[Any]], field_getter: Callable[[Any], Any]):
        """
        Initialize with collection and field accessors.
        
        Args:
            collection_getter: Function that returns the collection to check against
            field_getter: Function that extracts the field value from items in the collection
        """
        self.collection_getter = collection_getter
        self.field_getter = field_getter
    
    def validate(self, value: Any) -> bool:
        """Validate that value is unique in the collection."""
        if value is None:
            return True
        
        collection = self.collection_getter()
        values = [self.field_getter(item) for item in collection]
        
        if value in values:
            raise ValidationError(f"Value '{value}' already exists and must be unique")
        
        return True


class CustomValidationRule(ValidationRule):
    """
    Custom rule that uses a function for validation.
    
    This allows defining one-off validation rules without creating new classes.
    """
    
    def __init__(self, validation_func: Callable[[Any], bool], error_message: str):
        """
        Initialize with a validation function and error message.
        
        Args:
            validation_func: Function that takes a value and returns True if valid
            error_message: Error message to use if validation fails
        """
        self.validation_func = validation_func
        self.error_message = error_message
    
    def validate(self, value: Any) -> bool:
        """Validate using the provided function."""
        if value is None:
            return True
        
        if not self.validation_func(value):
            raise ValidationError(self.error_message)
        
        return True


class Validator:
    """
    Main validator class that combines rules for complex validation.
    
    This class allows defining validation rules for different fields
    and validates data objects against those rules.
    """
    
    def __init__(self, rules_map: Dict[str, List[ValidationRule]]):
        """
        Initialize with a mapping of fields to validation rules.
        
        Args:
            rules_map: Dictionary mapping field names to lists of validation rules
        """
        self.rules_map = rules_map
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate a data object against the rules.
        
        Args:
            data: Dictionary containing the data to validate
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        # Check all fields with rules
        for field, rules in self.rules_map.items():
            # Get the value (None if not present)
            value = data.get(field)
            
            # Apply each rule
            for rule in rules:
                try:
                    rule.validate(value)
                except ValidationError as e:
                    raise ValidationError(f"Validation failed for field '{field}': {str(e)}")
        
        return True
    
    def validate_collection(self, collection: List[Dict[str, Any]], strict: bool = True) -> Union[bool, List[Dict[str, Any]]]:
        """
        Validate a collection of data objects.
        
        Args:
            collection: List of data objects to validate
            strict: If True, raises an exception on the first error
                   If False, collects all errors and returns them
            
        Returns:
            bool: True if validation passes (strict=True)
            List: List of errors if strict=False
            
        Raises:
            ValidationError: If validation fails and strict=True
        """
        errors = []
        
        for i, item in enumerate(collection):
            try:
                self.validate(item)
            except ValidationError as e:
                if strict:
                    raise ValidationError(f"Validation failed for item #{i}: {str(e)}")
                else:
                    errors.append({
                        'index': i,
                        'item': item,
                        'error': e
                    })
        
        if strict:
            return True
        else:
            return errors


# Utility functions to create specific validators for our data models

def create_tax_code_validator() -> Validator:
    """
    Create a validator for tax code data.
    
    Returns:
        Validator: A configured validator for tax code data
    """
    # Create the basic validator with field-specific rules
    validator = Validator({
        "code": [
            RequiredRule(),
            StringRule(),
            RegexRule(r"^\d{5,6}$")
        ],
        "levy_rate": [
            RequiredRule(),
            FloatRule(),
            RangeRule(0.0, 1.0)  # Levy rates are typically between 0 and 1 (0-100%)
        ],
        "levy_amount": [
            FloatRule(),
            RangeRule(0.0, None)  # Must be positive if present
        ],
        "total_assessed_value": [
            FloatRule(),
            RangeRule(0.0, None)  # Must be positive if present
        ]
    })
    
    # Add a custom validation method to check levy consistency
    original_validate = validator.validate
    
    def validate_with_consistency(data: Dict[str, Any]) -> bool:
        # First apply all the standard field validations
        result = original_validate(data)
        
        # Then check consistency
        if not levy_consistency_validator(data):
            raise ValidationError("Levy amount is inconsistent with levy rate and total assessed value")
        
        return result
    
    # Replace the validator's validate method with our enhanced version
    validator.validate = validate_with_consistency
    
    return validator


def create_property_validator() -> Validator:
    """
    Create a validator for property data.
    
    Returns:
        Validator: A configured validator for property data
    """
    return Validator({
        "property_id": [
            RequiredRule(),
            StringRule(),
            RegexRule(r"^R\d{8}$")  # Example format: R12345678
        ],
        "assessed_value": [
            RequiredRule(),
            FloatRule(),
            RangeRule(0.0, None)  # Must be positive
        ],
        "tax_code": [
            RequiredRule(),
            StringRule(),
            RegexRule(r"^\d{5,6}$")
        ]
    })


def create_tax_district_validator() -> Validator:
    """
    Create a validator for tax district data.
    
    Returns:
        Validator: A configured validator for tax district data
    """
    return Validator({
        "tax_district_id": [
            RequiredRule(),
            IntegerRule(),
            RangeRule(1, None)  # Must be positive
        ],
        "year": [
            RequiredRule(),
            IntegerRule(),
            RangeRule(2000, 2100)  # Reasonable year range
        ],
        "levy_code": [
            RequiredRule(),
            StringRule(),
            RegexRule(r"^\d{5,6}$")
        ],
        "linked_levy_code": [
            RequiredRule(),
            StringRule(),
            RegexRule(r"^\d{5,6}$")
        ]
    })


def create_import_validator() -> Validator:
    """
    Create a validator for import metadata.
    
    Returns:
        Validator: A configured validator for import metadata
    """
    # Create the basic validator with field-specific rules
    validator = Validator({
        "filename": [
            RequiredRule(),
            StringRule()
        ],
        "row_count": [
            RequiredRule(),
            IntegerRule(),
            RangeRule(0, None)
        ],
        "columns": [
            RequiredRule()
        ],
        "data_type": [
            RequiredRule(),
            StringRule(),
            # Validate against known import types using a custom rule
            CustomValidationRule(
                lambda value: value in ["property", "tax_code", "tax_district"],
                "Data type must be one of: property, tax_code, tax_district"
            )
        ]
    })
    
    # Add a custom validation method to check required columns
    original_validate = validator.validate
    
    def validate_with_columns_check(data: Dict[str, Any]) -> bool:
        # First apply all the standard field validations
        result = original_validate(data)
        
        # Then check required columns based on data_type
        data_type = data.get('data_type')
        columns = data.get('columns', [])
        
        required_columns = {
            "property": ["property_id", "assessed_value", "tax_code"],
            "tax_code": ["code", "levy_rate"],
            "tax_district": ["tax_district_id", "year", "levy_code"]
        }
        
        if data_type in required_columns:
            missing = [col for col in required_columns[data_type] if col not in columns]
            if missing:
                raise ValidationError(f"Missing required columns for {data_type} import: {', '.join(missing)}")
        
        return result
    
    # Replace the validator's validate method with our enhanced version
    validator.validate = validate_with_columns_check
    
    return validator


# Function to create rules that validate relationships between fields
def create_field_relationship_validator(
    fields: List[str],
    validation_func: Callable[[Dict[str, Any]], bool],
    error_message: str
) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a validator function that checks relationships between fields.
    
    Args:
        fields: List of field names involved in the relationship
        validation_func: Function that takes a data object and returns True if valid
        error_message: Error message to use if validation fails
        
    Returns:
        Callable: A function that validates the relationship
    """
    def validator(data: Dict[str, Any]) -> bool:
        if not validation_func(data):
            field_values = {field: data.get(field) for field in fields}
            raise ValidationError(f"{error_message} (fields: {field_values})")
        return True
    
    return validator


# Example of a levy consistency validator that ensures levy_amount is approximately
# equal to levy_rate * total_assessed_value (within a tolerance)
def levy_consistency_validator(data: Dict[str, Any]) -> bool:
    """
    Validate that levy_amount is consistent with levy_rate and total_assessed_value.
    
    Args:
        data: Dictionary containing levy data
        
    Returns:
        bool: True if the values are consistent
    """
    levy_rate = data.get('levy_rate')
    levy_amount = data.get('levy_amount')
    total_assessed_value = data.get('total_assessed_value')
    
    # If any values are missing, we can't validate consistency
    if None in [levy_rate, levy_amount, total_assessed_value]:
        return True
    
    # Calculate expected levy amount
    expected_amount = levy_rate * total_assessed_value
    
    # Allow for some tolerance (e.g., 5%)
    tolerance = expected_amount * 0.05
    
    # Check if the actual amount is within tolerance
    return abs(levy_amount - expected_amount) <= tolerance