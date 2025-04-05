"""
District Analysis Utilities for the Levy Calculation System.

This module provides utility functions to support district analysis,
specifically for the AI-enhanced district analysis feature which allows
for comprehensive, trend, and compliance analysis of tax districts.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy import func
from app import db
from models import TaxDistrict, TaxCode, TaxCodeHistoricalRate, Property

# Configure logging
logger = logging.getLogger(__name__)

def get_district_details(district_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a tax district.
    
    Args:
        district_id: The ID of the tax district
        
    Returns:
        Dictionary containing district details
    """
    try:
        # Query the district
        district = TaxDistrict.query.get(district_id)
        
        if not district:
            return {
                "error": f"Tax district with ID {district_id} not found",
                "success": False
            }
        
        # Format the district data
        district_data = {
            "id": district.id,
            "name": district.district_name,
            "code": district.district_code,
            "type": district.district_type,
            "county": district.county,
            "state": district.state,
            "year": district.year,
            "statutory_limit": district.statutory_limit,
            "description": district.description,
            "contact": {
                "name": district.contact_name,
                "email": district.contact_email,
                "phone": district.contact_phone
            },
            "is_active": district.is_active,
            "created_at": district.created_at.isoformat() if district.created_at else None,
            "updated_at": district.updated_at.isoformat() if district.updated_at else None
        }
        
        return district_data
        
    except Exception as e:
        logger.error(f"Error in get_district_details: {str(e)}")
        return {
            "error": str(e),
            "success": False
        }

def get_district_tax_codes(district_id: str) -> List[Dict[str, Any]]:
    """
    Get all tax codes associated with a tax district.
    
    Args:
        district_id: The ID of the tax district
        
    Returns:
        List of tax code dictionaries
    """
    try:
        # Query tax codes for the district
        tax_codes = TaxCode.query.filter_by(tax_district_id=district_id).all()
        
        # Format the tax code data
        tax_code_data = []
        for code in tax_codes:
            tax_code_data.append({
                "id": code.id,
                "tax_code": code.tax_code,
                "description": code.description,
                "total_assessed_value": code.total_assessed_value,
                "total_levy_amount": code.total_levy_amount,
                "effective_tax_rate": code.effective_tax_rate,
                "year": code.year
            })
        
        return tax_code_data
        
    except Exception as e:
        logger.error(f"Error in get_district_tax_codes: {str(e)}")
        return []

def get_district_historical_rates(district_id: str, years: int = 3) -> List[Dict[str, Any]]:
    """
    Get historical tax rates for all tax codes in a district.
    
    Args:
        district_id: The ID of the tax district
        years: Number of years of historical data to retrieve
        
    Returns:
        List of historical rate dictionaries
    """
    try:
        # Get tax codes for this district
        tax_codes = TaxCode.query.filter_by(tax_district_id=district_id).all()
        
        if not tax_codes:
            return []
        
        # Create a list of tax code IDs
        tax_code_ids = [tc.id for tc in tax_codes]
        
        # Get the current year
        current_year = datetime.now().year
        
        # Query historical rates
        historical_rates = TaxCodeHistoricalRate.query.filter(
            TaxCodeHistoricalRate.tax_code_id.in_(tax_code_ids),
            TaxCodeHistoricalRate.year > (current_year - years - 1),
            TaxCodeHistoricalRate.year <= current_year
        ).order_by(
            TaxCodeHistoricalRate.tax_code_id,
            TaxCodeHistoricalRate.year.desc()
        ).all()
        
        # Format the historical rate data
        historical_data = []
        for rate in historical_rates:
            tax_code = next((tc for tc in tax_codes if tc.id == rate.tax_code_id), None)
            if tax_code:
                historical_data.append({
                    "id": rate.id,
                    "tax_code_id": rate.tax_code_id,
                    "tax_code": tax_code.tax_code,
                    "year": rate.year,
                    "levy_rate": rate.levy_rate,
                    "levy_amount": rate.levy_amount,
                    "total_assessed_value": rate.total_assessed_value
                })
        
        return historical_data
        
    except Exception as e:
        logger.error(f"Error in get_district_historical_rates: {str(e)}")
        return []

def calculate_comprehensive_statistics(tax_codes: List[Dict[str, Any]], historical_rates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics for a district based on tax codes and historical rates.
    
    Args:
        tax_codes: List of tax code dictionaries
        historical_rates: List of historical rate dictionaries
        
    Returns:
        Dictionary containing comprehensive statistics
    """
    try:
        # Initialize statistics
        stats = {
            "total_tax_codes": len(tax_codes),
            "average_assessed_value": 0,
            "total_assessed_value": 0,
            "average_levy_rate": 0,
            "historical_trend": {},
            "year_over_year_changes": {},
            "highest_rate_code": None,
            "lowest_rate_code": None,
            "highest_value_code": None,
            "statistical_metrics": {}
        }
        
        # Calculate aggregate statistics for tax codes
        if tax_codes:
            assessed_values = [tc.get("total_assessed_value", 0) for tc in tax_codes if tc.get("total_assessed_value")]
            if assessed_values:
                stats["total_assessed_value"] = sum(assessed_values)
                stats["average_assessed_value"] = stats["total_assessed_value"] / len(assessed_values)
            
            # Find highest and lowest values
            if assessed_values:
                max_value_idx = np.argmax(assessed_values)
                stats["highest_value_code"] = tax_codes[max_value_idx]["tax_code"]
        
        # Process historical rates
        if historical_rates:
            # Group by year
            years_data = {}
            for rate in historical_rates:
                year = rate.get("year")
                if year not in years_data:
                    years_data[year] = []
                years_data[year].append(rate)
            
            # Calculate yearly averages
            yearly_avg_rates = {}
            for year, rates in years_data.items():
                rate_values = [r.get("levy_rate", 0) for r in rates if r.get("levy_rate")]
                if rate_values:
                    yearly_avg_rates[year] = sum(rate_values) / len(rate_values)
            
            # Sort years and calculate trends
            sorted_years = sorted(yearly_avg_rates.keys())
            stats["historical_trend"] = {year: yearly_avg_rates[year] for year in sorted_years}
            
            # Calculate year-over-year changes
            for i in range(1, len(sorted_years)):
                current_year = sorted_years[i]
                prev_year = sorted_years[i-1]
                if yearly_avg_rates[prev_year] > 0:
                    pct_change = (yearly_avg_rates[current_year] - yearly_avg_rates[prev_year]) / yearly_avg_rates[prev_year] * 100
                    stats["year_over_year_changes"][current_year] = pct_change
            
            # Calculate overall average levy rate
            all_rates = [r.get("levy_rate", 0) for r in historical_rates if r.get("levy_rate")]
            if all_rates:
                stats["average_levy_rate"] = sum(all_rates) / len(all_rates)
                
                # Find highest and lowest rates
                max_rate_idx = np.argmax(all_rates)
                min_rate_idx = np.argmin(all_rates)
                stats["highest_rate_code"] = historical_rates[max_rate_idx]["tax_code"]
                stats["lowest_rate_code"] = historical_rates[min_rate_idx]["tax_code"]
                
                # Calculate statistical metrics
                stats["statistical_metrics"] = {
                    "mean": np.mean(all_rates),
                    "median": np.median(all_rates),
                    "std_dev": np.std(all_rates),
                    "min": np.min(all_rates),
                    "max": np.max(all_rates),
                    "range": np.max(all_rates) - np.min(all_rates),
                    "percentile_25": np.percentile(all_rates, 25),
                    "percentile_75": np.percentile(all_rates, 75)
                }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in calculate_comprehensive_statistics: {str(e)}")
        return {
            "error": str(e),
            "success": False
        }

def calculate_trend_statistics(tax_codes: List[Dict[str, Any]], historical_rates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate trend-focused statistics for a district.
    
    Args:
        tax_codes: List of tax code dictionaries
        historical_rates: List of historical rate dictionaries
        
    Returns:
        Dictionary containing trend statistics
    """
    try:
        # Initialize statistics
        stats = {
            "yearly_trends": {},
            "growth_rates": {},
            "acceleration": {},
            "seasonal_patterns": {},
            "correlation_metrics": {},
            "forecasting_indicators": {}
        }
        
        # Process historical rates
        if historical_rates:
            # Group by year and tax code
            year_code_data = {}
            for rate in historical_rates:
                year = rate.get("year")
                tax_code = rate.get("tax_code")
                if year not in year_code_data:
                    year_code_data[year] = {}
                if tax_code not in year_code_data[year]:
                    year_code_data[year][tax_code] = rate
            
            # Calculate yearly average rates and assessed values
            yearly_avg_rates = {}
            yearly_avg_values = {}
            yearly_total_values = {}
            sorted_years = sorted(year_code_data.keys())
            
            for year in sorted_years:
                rates = [rate.get("levy_rate", 0) for code, rate in year_code_data[year].items() if rate.get("levy_rate")]
                values = [rate.get("total_assessed_value", 0) for code, rate in year_code_data[year].items() if rate.get("total_assessed_value")]
                
                if rates:
                    yearly_avg_rates[year] = sum(rates) / len(rates)
                if values:
                    yearly_avg_values[year] = sum(values) / len(values)
                    yearly_total_values[year] = sum(values)
            
            # Set yearly trends
            stats["yearly_trends"] = {
                "average_rates": {year: yearly_avg_rates.get(year, 0) for year in sorted_years},
                "average_values": {year: yearly_avg_values.get(year, 0) for year in sorted_years},
                "total_values": {year: yearly_total_values.get(year, 0) for year in sorted_years}
            }
            
            # Calculate growth rates (year over year)
            growth_rates_rates = {}
            growth_rates_values = {}
            
            for i in range(1, len(sorted_years)):
                current_year = sorted_years[i]
                prev_year = sorted_years[i-1]
                
                # Rate growth
                if prev_year in yearly_avg_rates and yearly_avg_rates[prev_year] > 0:
                    rate_growth = (yearly_avg_rates.get(current_year, 0) - yearly_avg_rates[prev_year]) / yearly_avg_rates[prev_year] * 100
                    growth_rates_rates[current_year] = rate_growth
                
                # Value growth
                if prev_year in yearly_total_values and yearly_total_values[prev_year] > 0:
                    value_growth = (yearly_total_values.get(current_year, 0) - yearly_total_values[prev_year]) / yearly_total_values[prev_year] * 100
                    growth_rates_values[current_year] = value_growth
            
            stats["growth_rates"] = {
                "rates": growth_rates_rates,
                "values": growth_rates_values
            }
            
            # Calculate acceleration (change in growth rate)
            acceleration_rates = {}
            acceleration_values = {}
            
            for i in range(1, len(sorted_years) - 1):
                current_year = sorted_years[i+1]
                prev_year = sorted_years[i]
                
                if current_year in growth_rates_rates and prev_year in growth_rates_rates:
                    rate_acceleration = growth_rates_rates[current_year] - growth_rates_rates[prev_year]
                    acceleration_rates[current_year] = rate_acceleration
                
                if current_year in growth_rates_values and prev_year in growth_rates_values:
                    value_acceleration = growth_rates_values[current_year] - growth_rates_values[prev_year]
                    acceleration_values[current_year] = value_acceleration
            
            stats["acceleration"] = {
                "rates": acceleration_rates,
                "values": acceleration_values
            }
            
            # Calculate correlation between rates and values
            if len(sorted_years) >= 3:
                rate_values = [yearly_avg_rates.get(year, 0) for year in sorted_years]
                assessed_values = [yearly_total_values.get(year, 0) for year in sorted_years]
                
                if rate_values and assessed_values and len(rate_values) == len(assessed_values):
                    # Calculate correlation coefficient if we have enough data
                    try:
                        correlation = np.corrcoef(rate_values, assessed_values)[0, 1]
                        stats["correlation_metrics"]["rate_value_correlation"] = correlation
                    except:
                        stats["correlation_metrics"]["rate_value_correlation"] = None
            
            # Add forecasting indicators
            if len(sorted_years) >= 3:
                # Linear regression coefficients for rate trend
                try:
                    years_array = np.array(sorted_years)
                    rates_array = np.array([yearly_avg_rates.get(year, 0) for year in sorted_years])
                    
                    slope, intercept = np.polyfit(years_array, rates_array, 1)
                    stats["forecasting_indicators"]["rate_trend_slope"] = slope
                    stats["forecasting_indicators"]["rate_trend_intercept"] = intercept
                    
                    # Predict next year
                    next_year = max(sorted_years) + 1
                    predicted_rate = slope * next_year + intercept
                    stats["forecasting_indicators"]["predicted_next_year_rate"] = predicted_rate
                except:
                    pass
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in calculate_trend_statistics: {str(e)}")
        return {
            "error": str(e),
            "success": False
        }

def calculate_compliance_statistics(tax_codes: List[Dict[str, Any]], historical_rates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate compliance-focused statistics for a district.
    
    Args:
        tax_codes: List of tax code dictionaries
        historical_rates: List of historical rate dictionaries
        
    Returns:
        Dictionary containing compliance statistics
    """
    try:
        # Get district data from the first tax code (they all belong to the same district)
        district_id = None
        if tax_codes and len(tax_codes) > 0:
            first_code = tax_codes[0]
            district_id = first_code.get("tax_district_id")
        
        if not district_id:
            return {
                "error": "No district information found",
                "success": False
            }
        
        # Get district details to check statutory limits
        district = TaxDistrict.query.get(district_id)
        statutory_limit = district.statutory_limit if district and district.statutory_limit else None
        
        # Initialize statistics
        stats = {
            "statutory_limit": statutory_limit,
            "compliance_status": "Unknown",
            "over_limit_codes": [],
            "historical_compliance": {},
            "compliance_risk_metrics": {},
            "recommendations": []
        }
        
        # Check compliance against statutory limit
        if statutory_limit is not None:
            # Check current tax codes
            over_limit_codes = []
            for tc in tax_codes:
                if tc.get("effective_tax_rate", 0) > statutory_limit:
                    over_limit_codes.append({
                        "tax_code": tc.get("tax_code"),
                        "effective_rate": tc.get("effective_tax_rate"),
                        "excess_amount": tc.get("effective_tax_rate") - statutory_limit
                    })
            
            stats["over_limit_codes"] = over_limit_codes
            
            if over_limit_codes:
                stats["compliance_status"] = "Non-Compliant"
                stats["recommendations"].append("Review tax codes that exceed statutory limits")
            else:
                stats["compliance_status"] = "Compliant"
        
        # Analyze historical compliance
        if historical_rates and statutory_limit is not None:
            # Group by year
            yearly_compliance = {}
            for rate in historical_rates:
                year = rate.get("year")
                if year not in yearly_compliance:
                    yearly_compliance[year] = {
                        "compliant_codes": 0,
                        "non_compliant_codes": 0,
                        "total_codes": 0,
                        "compliance_rate": 0
                    }
                
                yearly_compliance[year]["total_codes"] += 1
                
                if rate.get("levy_rate", 0) > statutory_limit:
                    yearly_compliance[year]["non_compliant_codes"] += 1
                else:
                    yearly_compliance[year]["compliant_codes"] += 1
            
            # Calculate compliance rates
            for year, data in yearly_compliance.items():
                if data["total_codes"] > 0:
                    data["compliance_rate"] = (data["compliant_codes"] / data["total_codes"]) * 100
            
            stats["historical_compliance"] = yearly_compliance
            
            # Calculate compliance risk metrics
            recent_years = sorted(yearly_compliance.keys(), reverse=True)[:3]  # Last 3 years
            if recent_years:
                # Average compliance rate for recent years
                recent_rates = [yearly_compliance[year]["compliance_rate"] for year in recent_years]
                avg_compliance_rate = sum(recent_rates) / len(recent_rates)
                
                # Compliance trend (improving or deteriorating)
                compliance_trend = "Stable"
                if len(recent_years) >= 2:
                    most_recent = recent_years[0]
                    previous = recent_years[1]
                    if yearly_compliance[most_recent]["compliance_rate"] > yearly_compliance[previous]["compliance_rate"]:
                        compliance_trend = "Improving"
                    elif yearly_compliance[most_recent]["compliance_rate"] < yearly_compliance[previous]["compliance_rate"]:
                        compliance_trend = "Deteriorating"
                
                stats["compliance_risk_metrics"] = {
                    "average_compliance_rate": avg_compliance_rate,
                    "compliance_trend": compliance_trend,
                    "risk_level": "Low" if avg_compliance_rate >= 90 else ("Medium" if avg_compliance_rate >= 75 else "High")
                }
                
                # Generate recommendations based on compliance metrics
                if stats["compliance_risk_metrics"]["risk_level"] == "High":
                    stats["recommendations"].append("Conduct comprehensive compliance audit")
                    stats["recommendations"].append("Implement stricter compliance monitoring")
                elif stats["compliance_risk_metrics"]["risk_level"] == "Medium":
                    stats["recommendations"].append("Regular compliance reviews recommended")
                
                if compliance_trend == "Deteriorating":
                    stats["recommendations"].append("Investigate causes of declining compliance")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in calculate_compliance_statistics: {str(e)}")
        return {
            "error": str(e),
            "success": False
        }

# Register these functions with the MCP registry if available
try:
    from utils.mcp_core import registry
    
    if registry:
        registry.register_function(
            func=get_district_details,
            name="get_district_details",
            description="Get detailed information about a tax district",
            parameter_schema={
                "type": "object",
                "properties": {
                    "district_id": {
                        "type": "string",
                        "description": "The ID of the tax district"
                    }
                },
                "required": ["district_id"]
            }
        )
        
        registry.register_function(
            func=get_district_tax_codes,
            name="get_district_tax_codes",
            description="Get all tax codes associated with a tax district",
            parameter_schema={
                "type": "object",
                "properties": {
                    "district_id": {
                        "type": "string",
                        "description": "The ID of the tax district"
                    }
                },
                "required": ["district_id"]
            }
        )
        
        registry.register_function(
            func=get_district_historical_rates,
            name="get_district_historical_rates",
            description="Get historical tax rates for all tax codes in a district",
            parameter_schema={
                "type": "object",
                "properties": {
                    "district_id": {
                        "type": "string",
                        "description": "The ID of the tax district"
                    },
                    "years": {
                        "type": "integer",
                        "description": "Number of years of historical data to retrieve",
                        "default": 3
                    }
                },
                "required": ["district_id"]
            }
        )
        
        registry.register_function(
            func=calculate_comprehensive_statistics,
            name="calculate_comprehensive_statistics",
            description="Calculate comprehensive statistics for a district",
            parameter_schema={
                "type": "object",
                "properties": {
                    "tax_codes": {
                        "type": "array",
                        "description": "List of tax code dictionaries"
                    },
                    "historical_rates": {
                        "type": "array",
                        "description": "List of historical rate dictionaries"
                    }
                },
                "required": ["tax_codes", "historical_rates"]
            }
        )
        
        registry.register_function(
            func=calculate_trend_statistics,
            name="calculate_trend_statistics",
            description="Calculate trend-focused statistics for a district",
            parameter_schema={
                "type": "object",
                "properties": {
                    "tax_codes": {
                        "type": "array",
                        "description": "List of tax code dictionaries"
                    },
                    "historical_rates": {
                        "type": "array",
                        "description": "List of historical rate dictionaries"
                    }
                },
                "required": ["tax_codes", "historical_rates"]
            }
        )
        
        registry.register_function(
            func=calculate_compliance_statistics,
            name="calculate_compliance_statistics",
            description="Calculate compliance-focused statistics for a district",
            parameter_schema={
                "type": "object",
                "properties": {
                    "tax_codes": {
                        "type": "array",
                        "description": "List of tax code dictionaries"
                    },
                    "historical_rates": {
                        "type": "array",
                        "description": "List of historical rate dictionaries"
                    }
                },
                "required": ["tax_codes", "historical_rates"]
            }
        )
        
        logger.info("District analysis functions registered with MCP registry")
except ImportError:
    logger.warning("MCP registry not available, district analysis functions not registered")
except Exception as e:
    logger.error(f"Error registering district analysis functions: {str(e)}")