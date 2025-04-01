from app import db
from models import TaxCode

def calculate_levy_rates(levy_amounts):
    """
    Calculate levy rates based on levy amounts and assessed values.
    
    Args:
        levy_amounts: Dict mapping tax_code to levy_amount
        
    Returns:
        Dict mapping tax_code to calculated levy_rate
    """
    levy_rates = {}
    
    # Get all tax codes with their total assessed values
    tax_codes = TaxCode.query.all()
    
    for tax_code in tax_codes:
        if tax_code.code in levy_amounts and tax_code.total_assessed_value:
            # Calculate levy rate per $1,000 of assessed value
            levy_amount = levy_amounts[tax_code.code]
            levy_rate = (levy_amount / tax_code.total_assessed_value) * 1000
            levy_rates[tax_code.code] = levy_rate
    
    return levy_rates

def apply_statutory_limits(levy_rates):
    """
    Apply statutory limits to levy rates:
    - 101% cap over previous year's rate
    - $5.90 per $1,000 maximum rate
    
    Args:
        levy_rates: Dict mapping tax_code to levy_rate
        
    Returns:
        Dict mapping tax_code to limited levy_rate
    """
    MAX_RATE = 5.90  # Maximum rate per $1,000
    MAX_INCREASE_PERCENT = 1.01  # 101% of previous rate
    
    limited_rates = {}
    
    # Get all tax codes with their previous year rates
    tax_codes = TaxCode.query.all()
    
    for tax_code in tax_codes:
        if tax_code.code in levy_rates:
            calculated_rate = levy_rates[tax_code.code]
            limited_rate = calculated_rate
            
            # Apply 101% cap if previous rate exists
            if tax_code.previous_year_rate:
                max_rate_101_cap = tax_code.previous_year_rate * MAX_INCREASE_PERCENT
                if calculated_rate > max_rate_101_cap:
                    limited_rate = max_rate_101_cap
            
            # Apply maximum rate cap
            if limited_rate > MAX_RATE:
                limited_rate = MAX_RATE
            
            limited_rates[tax_code.code] = limited_rate
    
    return limited_rates

def calculate_property_tax(property_obj):
    """
    Calculate tax for a specific property.
    
    Args:
        property_obj: Property object
        
    Returns:
        Calculated tax amount or None if rate is not available
    """
    # Get the tax code for this property
    tax_code = TaxCode.query.filter_by(code=property_obj.tax_code).first()
    
    if tax_code and tax_code.levy_rate:
        # Calculate tax: assessed value / 1000 * levy rate
        return (property_obj.assessed_value / 1000) * tax_code.levy_rate
    
    return None
