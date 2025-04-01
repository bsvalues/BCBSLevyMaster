"""
Utility functions for calculating the impact of pending legislative bills on property taxes.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
import logging

from app import db
from models import Property, TaxCode, TaxDistrict
from utils.levy_utils import round_to_4

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def calculate_bill_impact(bill_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate the impact of a proposed bill on property taxes.
    
    Args:
        bill_data: Dictionary containing bill data including:
            - bill_name: Name of the bill
            - bill_description: Description of the bill
            - rate_changes: Dict mapping tax codes to new rates or adjustments
            - exemption_changes: Dict with exemption changes (amount, eligibility)
            - limit_changes: Dict with changes to statutory limits
    
    Returns:
        Dictionary with impact analysis results
    """
    logger.debug(f"Calculating bill impact for: {bill_data.get('bill_name', 'Unnamed Bill')}")
    
    # Gather current tax data for comparison
    current_tax_codes = TaxCode.query.all()
    current_tax_data = {tc.code: {
        'current_rate': tc.levy_rate,
        'current_total_av': tc.total_assessed_value,
        'current_levy_amount': tc.levy_amount,
        'previous_rate': tc.previous_year_rate
    } for tc in current_tax_codes}
    
    # Process rate changes from the bill
    rate_changes = bill_data.get('rate_changes', {})
    impacted_tax_codes = {}
    
    for code, change in rate_changes.items():
        if code in current_tax_data:
            current = current_tax_data[code]
            
            # Calculate new rates based on bill provisions
            if isinstance(change, float) or isinstance(change, int):
                # Absolute new rate
                new_rate = float(change)
            elif isinstance(change, dict) and 'adjustment' in change:
                # Percentage adjustment
                adj = float(change['adjustment'])
                current_rate = current['current_rate'] or 0
                new_rate = current_rate * adj
            else:
                # No change
                new_rate = current['current_rate']
            
            # Calculate impact on levy amount
            current_rate = current['current_rate'] or 0
            current_total_av = current['current_total_av'] or 0
            
            # Initialize current_levy_amount first to avoid unbound variable error
            current_levy_amount = current['current_levy_amount']
            if current_levy_amount is None and current_rate and current_total_av:
                current_levy_amount = (current_total_av / 1000) * current_rate
            else:
                current_levy_amount = current_levy_amount or 0
            
            if new_rate and current_total_av:
                new_levy_amount = (current_total_av / 1000) * new_rate
                levy_change = new_levy_amount - current_levy_amount
                levy_change_pct = (levy_change / current_levy_amount * 100) if current_levy_amount else 0
            else:
                new_levy_amount = None
                levy_change = None
                levy_change_pct = None
            
            # Store impact data
            impacted_tax_codes[code] = {
                'current_rate': current_rate,
                'new_rate': new_rate,
                'rate_change': new_rate - current_rate if current_rate is not None and new_rate is not None else None,
                'rate_change_pct': ((new_rate - current_rate) / current_rate * 100) if current_rate and new_rate else None,
                'current_levy_amount': current_levy_amount,
                'new_levy_amount': new_levy_amount,
                'levy_change': levy_change,
                'levy_change_pct': levy_change_pct
            }
    
    # Process exemption changes from the bill
    exemption_changes = bill_data.get('exemption_changes', {})
    exemption_impact = {}
    
    if exemption_changes:
        # Calculate impact of exemption changes
        current_exemption = exemption_changes.get('current_exemption', 0)
        new_exemption = exemption_changes.get('new_exemption', current_exemption)
        
        exemption_impact = {
            'current_exemption': current_exemption,
            'new_exemption': new_exemption,
            'exemption_change': new_exemption - current_exemption,
            'exemption_change_pct': ((new_exemption - current_exemption) / current_exemption * 100) 
                                   if current_exemption else None
        }
    
    # Process changes to statutory limits
    limit_changes = bill_data.get('limit_changes', {})
    limit_impact = {}
    
    if limit_changes:
        current_max_rate = float(5.90)  # Current statutory max rate
        current_max_increase = float(1.01)  # Current 101% limit
        
        new_max_rate = limit_changes.get('max_rate', current_max_rate)
        new_max_increase = limit_changes.get('max_increase', current_max_increase)
        
        limit_impact = {
            'current_max_rate': current_max_rate,
            'new_max_rate': new_max_rate,
            'max_rate_change': new_max_rate - current_max_rate,
            'current_max_increase': current_max_increase,
            'new_max_increase': new_max_increase,
            'max_increase_change': new_max_increase - current_max_increase
        }
    
    # Calculate impact on a sample property
    property_impacts = calculate_property_impacts(bill_data, impacted_tax_codes)
    
    # Prepare summary statistics
    avg_rate_change = 0
    avg_rate_change_pct = 0
    count = 0
    
    for code, impact in impacted_tax_codes.items():
        if impact['rate_change'] is not None:
            avg_rate_change += impact['rate_change']
            count += 1
        if impact['rate_change_pct'] is not None:
            avg_rate_change_pct += impact['rate_change_pct']
    
    if count > 0:
        avg_rate_change /= count
        avg_rate_change_pct /= count
    
    summary = {
        'affected_tax_codes': len(impacted_tax_codes),
        'avg_rate_change': avg_rate_change,
        'avg_rate_change_pct': avg_rate_change_pct,
        'has_exemption_changes': bool(exemption_changes),
        'has_limit_changes': bool(limit_changes),
        'highest_impact_area': get_highest_impact_area(impacted_tax_codes),
        'bill_name': bill_data.get('bill_name', 'Unnamed Bill'),
        'bill_description': bill_data.get('bill_description', '')
    }
    
    return {
        'status': 'success',
        'impacted_tax_codes': impacted_tax_codes,
        'exemption_impact': exemption_impact,
        'limit_impact': limit_impact,
        'property_impacts': property_impacts,
        'summary': summary
    }


def calculate_property_impacts(bill_data: Dict[str, Any], impacted_tax_codes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate impact of bill on sample properties of different values.
    
    Args:
        bill_data: Dictionary with bill data
        impacted_tax_codes: Dictionary with impacts on tax codes
    
    Returns:
        List of property impact calculations
    """
    # Create sample property values
    sample_values = [100000, 250000, 500000, 750000, 1000000]
    exemption_changes = bill_data.get('exemption_changes', {})
    
    current_exemption = exemption_changes.get('current_exemption', 0)
    new_exemption = exemption_changes.get('new_exemption', current_exemption)
    
    property_impacts = []
    
    # Calculate for each tax code and sample value
    for code, impact in impacted_tax_codes.items():
        current_rate = impact['current_rate']
        new_rate = impact['new_rate']
        
        for value in sample_values:
            # Apply exemptions
            current_taxable_value = max(0, value - current_exemption)
            new_taxable_value = max(0, value - new_exemption)
            
            # Calculate taxes
            if current_rate is not None:
                current_tax = (current_taxable_value / 1000) * current_rate
            else:
                current_tax = None
                
            if new_rate is not None:
                new_tax = (new_taxable_value / 1000) * new_rate
            else:
                new_tax = None
            
            # Calculate changes
            if current_tax is not None and new_tax is not None:
                tax_change = new_tax - current_tax
                tax_change_pct = (tax_change / current_tax * 100) if current_tax else 0
            else:
                tax_change = None
                tax_change_pct = None
                
            property_impacts.append({
                'tax_code': code,
                'assessed_value': value,
                'current_exemption': current_exemption,
                'new_exemption': new_exemption,
                'current_taxable_value': current_taxable_value,
                'new_taxable_value': new_taxable_value,
                'current_tax': current_tax,
                'new_tax': new_tax,
                'tax_change': tax_change,
                'tax_change_pct': tax_change_pct
            })
    
    return property_impacts


def get_highest_impact_area(impacted_tax_codes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify the tax code with the highest impact from the bill.
    
    Args:
        impacted_tax_codes: Dictionary with impacts on tax codes
    
    Returns:
        Dictionary with information about the highest impact area
    """
    highest_impact = None
    highest_change_pct = -float('inf')
    
    for code, impact in impacted_tax_codes.items():
        if impact['rate_change_pct'] is not None and impact['rate_change_pct'] > highest_change_pct:
            highest_change_pct = impact['rate_change_pct']
            highest_impact = {
                'tax_code': code,
                'change_pct': impact['rate_change_pct'],
                'current_rate': impact['current_rate'],
                'new_rate': impact['new_rate']
            }
    
    return highest_impact or {}