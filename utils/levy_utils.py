"""Utility functions for levy calculations."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Union

def calculate_levy_rate(levy_amount: Union[float, Decimal], assessed_value: Union[float, Decimal]) -> float:
    """Calculate levy rate based on levy amount and assessed value.

    Args:
        levy_amount: Total levy amount to be collected
        assessed_value: Total assessed value of properties

    Returns:
        float: Calculated levy rate as percentage

    Raises:
        ValueError: If inputs are invalid (negative or zero assessed value)
    """
    if assessed_value <= 0:
        raise ValueError("Assessed value must be greater than zero")
    if levy_amount < 0:
        raise ValueError("Levy amount cannot be negative")

    # Convert to Decimal for precise calculation
    levy_dec = Decimal(str(levy_amount))
    value_dec = Decimal(str(assessed_value))

    # Calculate rate as percentage (multiply by 100)
    rate = (levy_dec / value_dec * 100).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    return float(rate)

def calculate_levy_rates(levy_amounts: Dict[str, Union[float, Decimal]]) -> Dict[str, float]:
    """Calculate levy rates for multiple tax codes.

    Args:
        levy_amounts: Dictionary mapping tax codes to levy amounts

    Returns:
        Dictionary mapping tax codes to calculated rates
    """
    from models import TaxCode

    rates = {}
    for code, amount in levy_amounts.items():
        tax_code = TaxCode.query.filter_by(code=code).first()
        if tax_code and tax_code.total_assessed_value:
            rates[code] = calculate_levy_rate(amount, tax_code.total_assessed_value)
    return rates

def apply_statutory_limits(rate: float, max_rate: float = 5.0) -> float:
    """Apply statutory rate limits.

    Args:
        rate: Calculated levy rate
        max_rate: Maximum allowed rate (default 5%)

    Returns:
        float: Rate after applying limits
    """
    return min(rate, max_rate)

import math
from datetime import datetime
from app2 import db
from models import TaxCode, TaxDistrict, TaxCodeHistoricalRate, ComplianceCheck

def calculate_levy_rates_old(tax_codes, levy_amounts):
    """
    Calculate levy rates based on assessed values and levy amounts.

    Args:
        tax_codes: List of TaxCode objects
        levy_amounts: Dictionary mapping tax code codes to levy amounts

    Returns:
        Dictionary mapping tax code codes to calculated levy rates
    """
    levy_rates = {}

    for tax_code in tax_codes:
        if tax_code.code not in levy_amounts:
            continue

        if not tax_code.total_assessed_value or tax_code.total_assessed_value <= 0:
            levy_rates[tax_code.code] = 0
            continue

        # Calculate levy rate per $1,000 of assessed value
        # Levy rate = (Levy amount / Total assessed value) * 1000
        levy_amount = levy_amounts[tax_code.code]
        levy_rate = (levy_amount / tax_code.total_assessed_value) * 1000

        # Round to 6 decimal places
        levy_rates[tax_code.code] = round(levy_rate, 6)

    return levy_rates

def update_tax_code_levy_data(levy_rates, levy_amounts, year=None):
    """
    Update tax code levy rates and amounts in the database.

    Args:
        levy_rates: Dictionary mapping tax code codes to levy rates
        levy_amounts: Dictionary mapping tax code codes to levy amounts
        year: Year to update (defaults to current year)

    Returns:
        Number of tax codes updated
    """
    if year is None:
        year = datetime.now().year

    count = 0

    try:
        for code, rate in levy_rates.items():
            tax_code = TaxCode.query.filter_by(code=code, year=year).first()
            if tax_code:
                tax_code.levy_rate = rate
                tax_code.levy_amount = levy_amounts.get(code, 0)
                tax_code.updated_at = datetime.utcnow()

                # Create or update historical record
                historical_rate = TaxCodeHistoricalRate.query.filter_by(
                    tax_code_id=tax_code.id,
                    year=year
                ).first()

                if historical_rate:
                    historical_rate.levy_rate = rate
                    historical_rate.levy_amount = levy_amounts.get(code, 0)
                    historical_rate.total_assessed_value = tax_code.total_assessed_value
                    historical_rate.updated_at = datetime.utcnow()
                else:
                    new_historical_rate = TaxCodeHistoricalRate(
                        tax_code_id=tax_code.id,
                        year=year,
                        levy_rate=rate,
                        levy_amount=levy_amounts.get(code, 0),
                        total_assessed_value=tax_code.total_assessed_value
                    )
                    db.session.add(new_historical_rate)

                count += 1

        # Commit the changes
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise e

    return count

def check_statutory_compliance(tax_code_id, year=None):
    """
    Check statutory compliance for a tax code.

    Args:
        tax_code_id: ID of the tax code to check
        year: Year to check (defaults to current year)

    Returns:
        List of ComplianceCheck objects
    """
    if year is None:
        year = datetime.now().year

    compliance_checks = []

    try:
        tax_code = TaxCode.query.get(tax_code_id)
        if not tax_code:
            return compliance_checks

        # 1. Check rate limit compliance
        districts = TaxDistrict.query.filter_by(levy_code=tax_code.code, year=year).all()
        for district in districts:
            if district.statutory_limit and tax_code.levy_rate > district.statutory_limit:
                check = ComplianceCheck(
                    tax_code_id=tax_code_id,
                    check_type='rate_limit',
                    is_compliant=False,
                    details=f"Rate {tax_code.levy_rate} exceeds limit {district.statutory_limit}",
                    year=year
                )
                db.session.add(check)
                compliance_checks.append(check)
            else:
                check = ComplianceCheck(
                    tax_code_id=tax_code_id,
                    check_type='rate_limit',
                    is_compliant=True,
                    details=f"Rate {tax_code.levy_rate} within limit {district.statutory_limit or 'N/A'}",
                    year=year
                )
                db.session.add(check)
                compliance_checks.append(check)

        # 2. Check increase limit compliance
        previous_year = year - 1
        historical_rate = TaxCodeHistoricalRate.query.filter_by(
            tax_code_id=tax_code_id,
            year=previous_year
        ).first()

        if historical_rate and historical_rate.levy_rate > 0:
            # Washington law typically restricts annual increases to 1% (1.01)
            max_allowed_increase = historical_rate.levy_rate * 1.01
            if tax_code.levy_rate > max_allowed_increase:
                check = ComplianceCheck(
                    tax_code_id=tax_code_id,
                    check_type='increase_limit',
                    is_compliant=False,
                    details=f"Increase from {historical_rate.levy_rate} to {tax_code.levy_rate} exceeds 1% limit",
                    year=year
                )
                db.session.add(check)
                compliance_checks.append(check)
            else:
                check = ComplianceCheck(
                    tax_code_id=tax_code_id,
                    check_type='increase_limit',
                    is_compliant=True,
                    details=f"Increase from {historical_rate.levy_rate} to {tax_code.levy_rate} within 1% limit",
                    year=year
                )
                db.session.add(check)
                compliance_checks.append(check)

        # Commit the changes
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise e

    return compliance_checks

def apply_levy_scenario(scenario_id, year=None):
    """
    Apply a levy scenario to calculate adjusted levy rates.

    Args:
        scenario_id: ID of the levy scenario to apply
        year: Base year for the scenario (defaults to current year)

    Returns:
        Dictionary with adjusted levy rates and amounts
    """
    from models import LevyScenario, LevyScenarioAdjustment

    if year is None:
        year = datetime.now().year

    result = {
        'original_rates': {},
        'adjusted_rates': {},
        'original_amounts': {},
        'adjusted_amounts': {}
    }

    try:
        # Get the scenario
        scenario = LevyScenario.query.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario with ID {scenario_id} not found")

        # Get all tax codes for the base year
        tax_codes = TaxCode.query.filter_by(year=scenario.base_year).all()

        # Store original rates and amounts
        for tax_code in tax_codes:
            result['original_rates'][tax_code.code] = tax_code.levy_rate
            result['original_amounts'][tax_code.code] = tax_code.levy_amount

            # Default adjusted values to original values
            result['adjusted_rates'][tax_code.code] = tax_code.levy_rate
            result['adjusted_amounts'][tax_code.code] = tax_code.levy_amount

        # Apply adjustments
        for adjustment in scenario.adjustments:
            tax_code = TaxCode.query.get(adjustment.tax_code_id)
            if not tax_code:
                continue

            original_amount = result['original_amounts'][tax_code.code]

            if adjustment.adjustment_type == 'percentage':
                # Apply percentage adjustment to levy amount
                adjusted_amount = original_amount * (1 + adjustment.adjustment_value / 100)
            elif adjustment.adjustment_type == 'fixed_amount':
                # Apply fixed amount adjustment
                adjusted_amount = original_amount + adjustment.adjustment_value
            else:
                # Unknown adjustment type, skip
                continue

            # Ensure amount is not negative
            adjusted_amount = max(0, adjusted_amount)

            # Update adjusted amount
            result['adjusted_amounts'][tax_code.code] = adjusted_amount

            # Recalculate adjusted rate if we have assessed value
            if tax_code.total_assessed_value and tax_code.total_assessed_value > 0:
                adjusted_rate = (adjusted_amount / tax_code.total_assessed_value) * 1000
                result['adjusted_rates'][tax_code.code] = round(adjusted_rate, 6)

    except Exception as e:
        raise e

    return result

def calculate_property_tax(assessed_value, levy_rate):
    """
    Calculate property tax amount based on assessed value and levy rate.

    Args:
        assessed_value: Assessed value of the property
        levy_rate: Levy rate per $1,000 of assessed value

    Returns:
        Calculated tax amount
    """
    return (assessed_value / 1000) * levy_rate

def get_historical_rates(tax_code_id=None, tax_code=None, years=None):
    """
    Get historical levy rates for a tax code.

    Args:
        tax_code_id: ID of the tax code (alternative to tax_code)
        tax_code: Code of the tax code (alternative to tax_code_id)
        years: List of years to retrieve (defaults to all available years)

    Returns:
        List of TaxCodeHistoricalRate objects sorted by year
    """
    try:
        query = TaxCodeHistoricalRate.query

        if tax_code_id:
            query = query.filter_by(tax_code_id=tax_code_id)
        elif tax_code:
            # Join with TaxCode to filter by code
            query = query.join(TaxCode).filter(TaxCode.code == tax_code)
        else:
            return []

        if years:
            query = query.filter(TaxCodeHistoricalRate.year.in_(years))

        # Sort by year
        query = query.order_by(TaxCodeHistoricalRate.year)

        return query.all()

    except Exception as e:
        raise e