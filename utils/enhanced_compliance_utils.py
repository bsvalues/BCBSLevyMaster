"""
Enhanced Compliance Utilities

This module provides enhanced functionality for statutory compliance checks and reporting.
It implements:
- Comprehensive compliance checks across all levy requirements
- Detailed compliance reporting with recommendations
- Compliance history tracking and comparison
- Statutory limit validation for multiple scenarios
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple

from sqlalchemy import func, desc, and_, or_

from app import db
from models import (
    TaxCode, TaxDistrict, TaxCodeHistoricalRate,
    ComplianceReport, Property
)

# Set up logger
logger = logging.getLogger(__name__)

# Constants for statutory limits
REGULAR_LEVY_LIMIT = 5.90  # Maximum regular levy rate per $1,000
ANNUAL_INCREASE_LIMIT = 0.01  # Maximum 1% annual increase
FILING_DEADLINE_DAYS = 30  # Days before filing deadline to start warnings
BANKED_CAPACITY_THRESHOLD = 0.10  # Threshold for banked capacity warnings (10%)

def generate_levy_rate_compliance_report(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate a detailed compliance report for levy rates.
    
    Args:
        year: The tax year to check (defaults to current year)
        
    Returns:
        Dictionary containing compliance results
    """
    if not year:
        year = datetime.now().year
        
    # Get all tax codes with their rates
    tax_codes = TaxCode.query.all()
    
    # Regular levy compliance (within maximum rate limit)
    regular_levy_compliance = []
    
    for code in tax_codes:
        # Get historical rate for previous year if available
        prev_year_rate = None
        prev_year_record = TaxCodeHistoricalRate.query.join(TaxCode).filter(
            TaxCode.id == code.id,
            TaxCodeHistoricalRate.year == year - 1
        ).first()
        
        if prev_year_record:
            prev_year_rate = prev_year_record.levy_rate
        elif code.previous_year_rate:
            prev_year_rate = code.previous_year_rate
            
        # Evaluate compliance
        regular_levy_compliant = code.levy_rate <= REGULAR_LEVY_LIMIT if code.levy_rate else True
        annual_increase_compliant = True
        issues = []
        
        if not regular_levy_compliant:
            issues.append(f"Exceeds maximum levy rate of {REGULAR_LEVY_LIMIT}")
            
        # Check annual increase if we have previous year data
        if prev_year_rate and code.levy_rate:
            if prev_year_rate > 0:
                percent_increase = (code.levy_rate - prev_year_rate) / prev_year_rate
                annual_increase_compliant = percent_increase <= ANNUAL_INCREASE_LIMIT
                
                if not annual_increase_compliant:
                    issues.append(f"Exceeds annual increase limit of {ANNUAL_INCREASE_LIMIT * 100}%")
                    
        # Build result for this tax code
        regular_levy_compliance.append({
            'code': code.code,
            'levy_rate': code.levy_rate,
            'previous_rate': prev_year_rate,
            'regular_levy_compliant': regular_levy_compliant,
            'annual_increase_compliant': annual_increase_compliant,
            'issues': issues
        })
    
    # Calculate overall compliance
    compliant_codes = [c for c in regular_levy_compliance 
                      if c['regular_levy_compliant'] and c['annual_increase_compliant']]
    
    if tax_codes:
        compliance_percentage = (len(compliant_codes) / len(tax_codes)) * 100
    else:
        compliance_percentage = 100.0
        
    # Return the complete levy rate compliance report
    return {
        'year': year,
        'overall_compliant': len(compliant_codes) == len(tax_codes),
        'compliance_percentage': compliance_percentage,
        'regular_levy_compliance': regular_levy_compliance
    }

def generate_filing_deadline_compliance_report() -> Dict[str, Any]:
    """
    Generate a compliance report for filing deadline requirements.
    
    Returns:
        Dictionary containing deadline compliance information
    """
    # Determine filing deadline (for example, July 15th of current year)
    today = datetime.now()
    filing_year = today.year
    
    # This uses July 15th as an example deadline - adjust as needed
    # for Washington State specific requirements
    deadline_date = datetime(filing_year, 7, 15)
    
    # If we've passed this year's deadline, look at next year
    if today > deadline_date:
        filing_year += 1
        deadline_date = datetime(filing_year, 7, 15)
        
    # Calculate days remaining
    days_remaining = (deadline_date - today).days
    
    # Determine status and warnings
    status = "On track"
    warnings = []
    
    if days_remaining <= 0:
        status = "Overdue"
        warnings.append("Filing deadline has passed!")
    elif days_remaining <= 10:
        status = "Critical"
        warnings.append(f"Only {days_remaining} days left until filing deadline!")
    elif days_remaining <= FILING_DEADLINE_DAYS:
        status = "Warning"
        warnings.append(f"{days_remaining} days left until filing deadline.")
        
    # Check data readiness
    total_tax_codes = TaxCode.query.count()
    codes_with_levy_rates = TaxCode.query.filter(TaxCode.levy_rate.isnot(None)).count()
    
    if codes_with_levy_rates < total_tax_codes:
        missing_count = total_tax_codes - codes_with_levy_rates
        warnings.append(f"{missing_count} tax codes are missing levy rate data.")
        
    # Check for data inconsistencies
    inconsistent_codes = TaxCode.query.filter(
        or_(
            and_(TaxCode.levy_amount.isnot(None), TaxCode.total_assessed_value.isnot(None),
                TaxCode.levy_rate.isnot(None),
                func.abs(TaxCode.levy_amount / TaxCode.total_assessed_value * 1000 - TaxCode.levy_rate) > 0.01),
            and_(TaxCode.levy_amount.is_(None), TaxCode.levy_rate.isnot(None)),
            and_(TaxCode.total_assessed_value.is_(None), TaxCode.levy_rate.isnot(None))
        )
    ).count()
    
    if inconsistent_codes > 0:
        warnings.append(f"{inconsistent_codes} tax codes have inconsistent levy data.")
    
    return {
        'deadline_date': deadline_date.strftime('%Y-%m-%d'),
        'days_remaining': days_remaining,
        'status': status,
        'warnings': warnings,
        'tax_codes_total': total_tax_codes,
        'tax_codes_ready': codes_with_levy_rates
    }

def generate_banked_capacity_report(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate a report on banked capacity for levy rates.
    
    Args:
        year: The tax year to check (defaults to current year)
        
    Returns:
        Dictionary containing banked capacity information
    """
    if not year:
        year = datetime.now().year
        
    # Get all tax codes
    tax_codes = TaxCode.query.all()
    
    # Track tax codes with banked capacity
    tax_codes_with_banked_capacity = []
    total_banked_capacity = 0.0
    
    for code in tax_codes:
        # Get historical rate for previous year if available
        prev_year_rate = None
        prev_year_record = TaxCodeHistoricalRate.query.join(TaxCode).filter(
            TaxCode.id == code.id,
            TaxCodeHistoricalRate.year == year - 1
        ).first()
        
        if prev_year_record:
            prev_year_rate = prev_year_record.levy_rate
        elif code.previous_year_rate:
            prev_year_rate = code.previous_year_rate
            
        # Calculate banked capacity if we have previous year rate
        if prev_year_rate and code.levy_rate:
            # Calculate maximum allowed increase (1% of previous year)
            max_allowed = prev_year_rate * (1 + ANNUAL_INCREASE_LIMIT)
            
            # If current rate is less than maximum allowed, we have banked capacity
            if code.levy_rate < max_allowed:
                banked_capacity = max_allowed - code.levy_rate
                
                # Calculate dollar value if we have assessed value
                dollar_value = None
                if code.total_assessed_value:
                    dollar_value = banked_capacity * code.total_assessed_value / 1000
                    total_banked_capacity += dollar_value
                
                tax_codes_with_banked_capacity.append({
                    'code': code.code,
                    'current_rate': code.levy_rate,
                    'max_allowed_rate': max_allowed,
                    'banked_capacity_rate': banked_capacity,
                    'total_assessed_value': code.total_assessed_value,
                    'banked_capacity_value': dollar_value
                })
    
    # Generate warnings based on banked capacity
    warnings = []
    if tax_codes_with_banked_capacity:
        warnings.append(f"There are {len(tax_codes_with_banked_capacity)} tax codes with banked capacity.")
        
        # Warning for significant banked capacity
        if total_banked_capacity > 0:
            warnings.append(f"Total potential banked capacity value: ${total_banked_capacity:,.2f}")
    
    return {
        'year': year,
        'tax_codes_with_banked_capacity': tax_codes_with_banked_capacity,
        'total_banked_capacity': total_banked_capacity,
        'warnings': warnings
    }

def generate_comprehensive_compliance_report(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate a comprehensive compliance report covering all aspects.
    
    Args:
        year: The tax year to check (defaults to current year)
        
    Returns:
        Dictionary containing the complete compliance report
    """
    if not year:
        year = datetime.now().year
        
    # Generate individual reports
    levy_rate_report = generate_levy_rate_compliance_report(year)
    filing_deadline_report = generate_filing_deadline_compliance_report()
    banked_capacity_report = generate_banked_capacity_report(year)
    
    # Determine critical issues
    critical_issues = []
    
    # Add levy rate issues
    if not levy_rate_report['overall_compliant']:
        non_compliant = [c for c in levy_rate_report['regular_levy_compliance'] 
                         if not c['regular_levy_compliant'] or not c['annual_increase_compliant']]
        
        for code in non_compliant:
            for issue in code['issues']:
                critical_issues.append(f"Tax code {code['code']}: {issue}")
    
    # Add filing deadline issues
    if filing_deadline_report['status'] in ['Overdue', 'Critical']:
        for warning in filing_deadline_report['warnings']:
            critical_issues.append(f"Filing deadline: {warning}")
    
    # Generate recommendations
    recommendations = []
    
    # Levy rate recommendations
    if not levy_rate_report['overall_compliant']:
        recommendations.append("Review non-compliant tax codes and adjust levy rates to meet statutory limits.")
        
    # Filing deadline recommendations
    if filing_deadline_report['status'] != 'On track':
        recommendations.append("Prioritize completion of levy calculations to meet filing deadline.")
        
    # Banked capacity recommendations
    if banked_capacity_report['tax_codes_with_banked_capacity']:
        recommendations.append("Consider utilizing banked capacity for future levy planning.")
    
    # Data quality recommendations
    if filing_deadline_report['tax_codes_total'] != filing_deadline_report['tax_codes_ready']:
        recommendations.append("Complete missing levy rate data for all tax codes.")
        
    # Overall report
    overall_compliant = (
        levy_rate_report['overall_compliant'] and 
        filing_deadline_report['status'] not in ['Overdue', 'Critical']
    )
    
    compliance_percentage = levy_rate_report['compliance_percentage']
    
    # Create report in database
    report_data = {
        'levy_rate_compliance': levy_rate_report,
        'filing_deadline_compliance': filing_deadline_report,
        'banked_capacity_compliance': banked_capacity_report,
        'recommendations': recommendations
    }
    
    # Save to database
    compliance_report = ComplianceReport(
        report_date=datetime.utcnow(),
        report_type='comprehensive',
        year=year,
        overall_compliant=overall_compliant,
        compliance_percentage=compliance_percentage,
        critical_issues=json.dumps(critical_issues) if critical_issues else None,
        report_data=json.dumps(report_data)
    )
    
    db.session.add(compliance_report)
    db.session.commit()
    
    # Return the complete report
    return {
        'report_id': compliance_report.id,
        'year': year,
        'overall_compliant': overall_compliant,
        'compliance_percentage': compliance_percentage,
        'critical_issues': critical_issues,
        'levy_rate_compliance': levy_rate_report,
        'filing_deadline_compliance': filing_deadline_report,
        'banked_capacity_compliance': banked_capacity_report,
        'recommendations': recommendations
    }

def get_compliance_history(years: int = 3) -> List[Dict[str, Any]]:
    """
    Get compliance history for the specified number of years.
    
    Args:
        years: Number of past years to include
        
    Returns:
        List of compliance report summaries
    """
    # Get current year
    current_year = datetime.now().year
    
    # Get years to include
    year_list = list(range(current_year - years + 1, current_year + 1))
    
    # Get compliance reports for these years
    reports = []
    
    for year in year_list:
        # Try to find existing report
        report = ComplianceReport.query.filter_by(
            report_type='comprehensive',
            year=year
        ).order_by(ComplianceReport.report_date.desc()).first()
        
        if report:
            reports.append({
                'report_id': report.id,
                'year': report.year,
                'report_date': report.report_date.strftime('%Y-%m-%d'),
                'overall_compliant': report.overall_compliant,
                'compliance_percentage': report.compliance_percentage,
                'critical_issues_count': len(report.get_critical_issues())
            })
    
    return reports

def apply_statutory_limits_to_scenario(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply statutory limits to a scenario and identify compliance issues.
    
    Args:
        scenario_data: Dictionary containing scenario data including levy rates
        
    Returns:
        Dictionary with updated rates and compliance information
    """
    # Start with a copy of the input data
    result = scenario_data.copy()
    result['compliance_issues'] = []
    
    # Apply regular levy limit
    for code, data in result.get('tax_codes', {}).items():
        levy_rate = data.get('levy_rate')
        if levy_rate and levy_rate > REGULAR_LEVY_LIMIT:
            result['tax_codes'][code]['original_rate'] = levy_rate
            result['tax_codes'][code]['levy_rate'] = REGULAR_LEVY_LIMIT
            result['compliance_issues'].append({
                'code': code,
                'issue': f"Reduced levy rate from {levy_rate} to {REGULAR_LEVY_LIMIT} (statutory maximum)"
            })
    
    # Apply annual increase limit if we have previous year data
    for code, data in result.get('tax_codes', {}).items():
        levy_rate = data.get('levy_rate')
        prev_rate = data.get('previous_year_rate')
        
        if levy_rate and prev_rate and prev_rate > 0:
            max_allowed = prev_rate * (1 + ANNUAL_INCREASE_LIMIT)
            
            if levy_rate > max_allowed:
                result['tax_codes'][code]['original_rate'] = levy_rate
                result['tax_codes'][code]['levy_rate'] = max_allowed
                result['compliance_issues'].append({
                    'code': code,
                    'issue': f"Reduced levy rate from {levy_rate} to {max_allowed} (maximum annual increase)"
                })
    
    # Calculate impact on total revenue
    if 'total_revenue' in result:
        original_revenue = result['total_revenue']
        
        # Recalculate with limited rates
        limited_revenue = 0
        for code, data in result.get('tax_codes', {}).items():
            levy_rate = data.get('levy_rate')
            assessed_value = data.get('assessed_value')
            
            if levy_rate and assessed_value:
                limited_revenue += levy_rate * assessed_value / 1000
        
        result['original_revenue'] = original_revenue
        result['total_revenue'] = limited_revenue
        
        if limited_revenue < original_revenue:
            result['revenue_impact'] = original_revenue - limited_revenue
            result['revenue_impact_percent'] = (
                (original_revenue - limited_revenue) / original_revenue * 100
                if original_revenue > 0 else 0
            )
    
    return result