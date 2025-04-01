"""
Utility functions for levy calculations and property tax processing.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
import logging

from app import db
from models import Property, TaxCode, TaxDistrict
from utils.anthropic_utils import get_claude_service

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants for statutory limits
MAX_LEVY_RATE = Decimal('5.90')  # Maximum levy rate per $1,000 of assessed value
MAX_YEARLY_INCREASE = Decimal('1.01')  # Maximum 1% annual increase (101% of previous year)


def round_to_4(value: Optional[Union[float, Decimal]]) -> Optional[Decimal]:
    """
    Round a value to 4 decimal places.
    
    Args:
        value: The value to round
        
    Returns:
        The rounded value or None if input is None
    """
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def calculate_levy_rates(levy_amounts: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate levy rates based on levy amounts and assessed values.
    
    Args:
        levy_amounts: Dictionary mapping tax code to levy amount
        
    Returns:
        Dictionary mapping tax code to calculated levy rate
    """
    logger.debug(f"Calculating levy rates for amounts: {levy_amounts}")
    rates = {}
    
    for code, amount in levy_amounts.items():
        tax_code = TaxCode.query.filter_by(code=code).first()
        if tax_code and tax_code.total_assessed_value and amount:
            # Calculate rate per $1,000 of assessed value
            rate = float(amount) / (float(tax_code.total_assessed_value) / 1000)
            rates[code] = rate
            logger.debug(f"Calculated rate for {code}: {rate}")
        else:
            logger.warning(f"Cannot calculate rate for {code} - missing tax code or assessed value")
            
    return rates


def apply_statutory_limits(rates: Dict[str, float]) -> Dict[str, float]:
    """
    Apply statutory limits to levy rates.
    
    Args:
        rates: Dictionary mapping tax code to calculated levy rate
        
    Returns:
        Dictionary mapping tax code to limited levy rate
    """
    logger.debug(f"Applying statutory limits to rates: {rates}")
    limited_rates = {}
    
    for code, rate in rates.items():
        tax_code = TaxCode.query.filter_by(code=code).first()
        if not tax_code:
            limited_rates[code] = rate
            continue
            
        decimal_rate = Decimal(str(rate))
        limited_rate = decimal_rate
        limited = False
        
        # Apply 101% limit based on previous year rate
        if tax_code.previous_year_rate:
            previous_year_with_limit = Decimal(str(tax_code.previous_year_rate)) * MAX_YEARLY_INCREASE
            if decimal_rate > previous_year_with_limit:
                limited_rate = previous_year_with_limit
                limited = True
                logger.debug(f"Rate for {code} limited by 101% rule: {limited_rate}")
        
        # Apply maximum rate limit
        if limited_rate > MAX_LEVY_RATE:
            limited_rate = MAX_LEVY_RATE
            limited = True
            logger.debug(f"Rate for {code} capped at maximum: {limited_rate}")
            
        limited_rates[code] = float(limited_rate)
    
    return limited_rates


def calculate_property_tax(property_obj: Property) -> Optional[float]:
    """
    Calculate property tax based on assessed value and levy rate.
    
    Args:
        property_obj: Property object
        
    Returns:
        Calculated tax amount or None if rate is not available
    """
    logger.debug(f"Calculating tax for property: {property_obj.property_id}")
    tax_code = TaxCode.query.filter_by(code=property_obj.tax_code).first()
    
    if not tax_code or tax_code.levy_rate is None:
        logger.warning(f"Cannot calculate tax - no tax code or levy rate for {property_obj.property_id}")
        return None
        
    # Calculate tax: (assessed_value / 1000) * levy_rate
    tax_amount = (property_obj.assessed_value / 1000) * tax_code.levy_rate
    logger.debug(f"Tax for {property_obj.property_id}: {tax_amount}")
    
    return tax_amount


def update_tax_code_totals():
    """
    Update the total assessed value for each tax code from property data.
    
    Returns:
        Dictionary with results of the update
    """
    logger.debug("Updating tax code totals")
    results = {'updated': 0, 'skipped': 0}
    
    # Get all tax codes
    tax_codes = TaxCode.query.all()
    
    for tc in tax_codes:
        # Sum assessed values for all properties with this tax code
        properties = Property.query.filter_by(tax_code=tc.code).all()
        
        if properties:
            total_value = sum(p.assessed_value for p in properties)
            tc.total_assessed_value = total_value
            results['updated'] += 1
            logger.debug(f"Updated total for {tc.code}: {total_value}")
        else:
            results['skipped'] += 1
            
    db.session.commit()
    logger.debug(f"Tax code update results: {results}")
    
    return results


def calculate_historical_comparison() -> List[Dict[str, Any]]:
    """
    Calculate historical comparison between current and previous year rates.
    
    Returns:
        List of dictionaries with tax code, current rate, previous rate, 
        change percentage, and direction (increase/decrease/unchanged)
    """
    logger.debug("Calculating historical comparison")
    comparison = []
    
    # Get all tax codes with both current and previous rates
    tax_codes = TaxCode.query.filter(
        TaxCode.levy_rate.isnot(None),
        TaxCode.previous_year_rate.isnot(None)
    ).all()
    
    for tc in tax_codes:
        current = float(tc.levy_rate) if tc.levy_rate else 0
        previous = float(tc.previous_year_rate) if tc.previous_year_rate else 0
        
        if previous > 0:
            change_pct = ((current - previous) / previous) * 100
        else:
            change_pct = 0
            
        if current > previous:
            direction = 'increase'
        elif current < previous:
            direction = 'decrease'
        else:
            direction = 'unchanged'
            
        comparison.append({
            'code': tc.code,
            'current_rate': current,
            'previous_rate': previous,
            'change_pct': change_pct,
            'direction': direction
        })
        
    logger.debug(f"Historical comparison complete for {len(comparison)} tax codes")
    return comparison


def simulate_levy_scenarios(scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simulate the impact of different levy scenarios.
    
    Args:
        scenarios: List of scenario dictionaries, each with a name and 
                  adjustments mapping tax codes to multipliers
    
    Returns:
        List of scenario results with calculated rates and impacts
    """
    logger.debug(f"Simulating levy scenarios: {scenarios}")
    results = []
    
    # Get baseline data
    tax_codes = TaxCode.query.filter(TaxCode.levy_amount.isnot(None)).all()
    baseline_data = {tc.code: {
        'levy_amount': tc.levy_amount,
        'assessed_value': tc.total_assessed_value,
        'rate': tc.levy_rate,
        'previous_rate': tc.previous_year_rate
    } for tc in tax_codes}
    
    for scenario in scenarios:
        scenario_name = scenario.get('name', 'Scenario')
        adjustments = scenario.get('adjustments', {})
        
        scenario_result = {
            'name': scenario_name,
            'scenarios': {}
        }
        
        for code, data in baseline_data.items():
            # Get adjustment factor for this tax code, default to 1.0 (no change)
            adjustment = adjustments.get(code, 1.0)
            adjusted_amount = data['levy_amount'] * adjustment
            
            # Calculate new rate
            if data['assessed_value']:
                new_rate = adjusted_amount / (data['assessed_value'] / 1000)
            else:
                new_rate = None
                
            # Check if limited by statutory caps
            limited = False
            limited_rate = new_rate
            
            if new_rate is not None:
                # Apply 101% limit
                if data['previous_rate']:
                    max_increase = data['previous_rate'] * float(MAX_YEARLY_INCREASE)
                    if new_rate > max_increase:
                        limited_rate = max_increase
                        limited = True
                
                # Apply maximum cap
                if limited_rate is not None and limited_rate > float(MAX_LEVY_RATE):
                    limited_rate = float(MAX_LEVY_RATE)
                    limited = True
                    
            # Calculate tax impact
            if data['rate'] is not None and new_rate is not None and data['rate'] != 0:
                change_pct = ((new_rate - data['rate']) / data['rate']) * 100
            else:
                change_pct = 0
                
            # Store scenario data for this tax code
            scenario_result['scenarios'][code] = {
                'original_amount': data['levy_amount'],
                'adjusted_amount': adjusted_amount,
                'rate': new_rate,
                'limited': limited,
                'limited_rate': limited_rate if limited else new_rate,
                'change_pct': change_pct
            }
            
        results.append(scenario_result)
        
    logger.debug(f"Completed {len(results)} scenarios")
    return results


def get_levy_insights(levy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI-powered insights about levy calculations.
    
    Args:
        levy_data: Dictionary with levy calculation data
        
    Returns:
        Dictionary with AI analysis insights
    """
    logger.debug("Generating levy insights with Claude AI")
    
    # Try to get Claude service
    claude_service = get_claude_service()
    if not claude_service:
        logger.warning("Claude service unavailable - no API key")
        return {
            'status': 'error',
            'message': 'AI analysis not available - API key not configured'
        }
    
    try:
        # Generate insights with Claude AI
        insights = claude_service.generate_levy_insights(levy_data)
        logger.debug("Successfully generated levy insights")
        return {
            'status': 'success',
            'insights': insights
        }
    except Exception as e:
        logger.error(f"Error generating levy insights: {str(e)}")
        return {
            'status': 'error',
            'message': f'Error generating AI analysis: {str(e)}'
        }


def update_tax_codes_with_levy_rates(rates: Dict[str, float], amounts: Dict[str, float]):
    """
    Update tax codes with calculated levy rates and amounts.
    
    Args:
        rates: Dictionary mapping tax code to levy rate
        amounts: Dictionary mapping tax code to levy amount
        
    Returns:
        Number of tax codes updated
    """
    logger.debug(f"Updating tax codes with rates: {rates}")
    updated = 0
    
    for code, rate in rates.items():
        tax_code = TaxCode.query.filter_by(code=code).first()
        if tax_code:
            tax_code.levy_rate = rate
            if code in amounts:
                tax_code.levy_amount = amounts[code]
            updated += 1
            
    db.session.commit()
    logger.debug(f"Updated {updated} tax codes with new rates")
    
    return updated