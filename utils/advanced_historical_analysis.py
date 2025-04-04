"""
Advanced historical data analysis utilities for the Levy Calculation System.

This module provides functions for analyzing historical tax rate data,
forecasting trends, detecting anomalies, and generating comparative reports.
"""

import statistics
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import joinedload

from app import db
from models import TaxCode, TaxDistrict, TaxCodeHistoricalRate

# Setup logging
logger = logging.getLogger(__name__)

def compute_basic_statistics(tax_code_identifier: str, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Compute basic statistical measures for historical levy rates of a tax code.
    
    Args:
        tax_code_identifier: The tax code to analyze (can be code or ID)
        years: Optional list of years to include in analysis, defaults to all years
        
    Returns:
        Dictionary with statistical measures and historical data
    """
    logger.info(f"Computing statistics for tax code {tax_code_identifier} over years {years or 'all'}")
    
    try:
        # Determine if tax_code_identifier is an ID or a code string
        try:
            tax_code_id = int(tax_code_identifier)
            tax_code_obj = TaxCode.query.get(tax_code_id)
        except (ValueError, TypeError):
            # It's a string tax code
            tax_code_obj = TaxCode.query.filter_by(tax_code=tax_code_identifier).first()
        
        if not tax_code_obj:
            return {
                'error': f"Tax code {tax_code_identifier} not found",
                'historical_data': []
            }
        
        # Query historical rates
        query = TaxCodeHistoricalRate.query.filter_by(tax_code_id=tax_code_obj.id)
        
        # Apply year filter if specified
        if years:
            query = query.filter(TaxCodeHistoricalRate.year.in_(years))
        
        # Order by year
        query = query.order_by(TaxCodeHistoricalRate.year)
        
        # Execute query
        historical_rates = query.all()
        
        if not historical_rates:
            return {
                'error': f"No historical data found for tax code {tax_code_identifier} in specified years",
                'historical_data': []
            }
        
        # Extract rate data
        rates = [rate.levy_rate for rate in historical_rates]
        years_data = [rate.year for rate in historical_rates]
        
        # Compute basic statistics
        stats = {
            'tax_code': tax_code_obj.tax_code,
            'tax_code_id': tax_code_obj.id,
            'years': years_data,
            'count': len(rates),
            'min': min(rates),
            'max': max(rates),
            'range': max(rates) - min(rates),
            'mean': statistics.mean(rates),
            'median': statistics.median(rates),
            'historical_data': [
                {
                    'year': rate.year,
                    'levy_rate': rate.levy_rate,
                    'levy_amount': rate.levy_amount,
                    'total_assessed_value': rate.total_assessed_value
                }
                for rate in historical_rates
            ]
        }
        
        # Add standard deviation if we have enough data points
        if len(rates) > 1:
            stats['stddev'] = statistics.stdev(rates)
            
            # Calculate coefficient of variation (relative standard deviation)
            if stats['mean'] > 0:
                stats['cv'] = (stats['stddev'] / stats['mean']) * 100  # As percentage
            else:
                stats['cv'] = None
            
            # Calculate year-over-year changes
            yoy_changes = []
            for i in range(1, len(rates)):
                previous = rates[i-1]
                current = rates[i]
                if previous > 0:
                    pct_change = ((current - previous) / previous) * 100
                    yoy_changes.append({
                        'from_year': years_data[i-1],
                        'to_year': years_data[i],
                        'change': current - previous,
                        'pct_change': pct_change
                    })
            
            stats['year_over_year_changes'] = yoy_changes
            
            if yoy_changes:
                # Average annual change
                avg_change = sum(c['change'] for c in yoy_changes) / len(yoy_changes)
                stats['avg_annual_change'] = avg_change
                
                # Average annual percent change
                avg_pct_change = sum(c['pct_change'] for c in yoy_changes) / len(yoy_changes)
                stats['avg_annual_pct_change'] = avg_pct_change
        
        return stats
        
    except Exception as e:
        logger.error(f"Error computing statistics: {str(e)}")
        return {
            'error': f"Error computing statistics: {str(e)}",
            'historical_data': []
        }


def compute_moving_average(tax_code_identifier: str, window_size: int = 3, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Compute moving average for historical levy rates.
    
    Args:
        tax_code_identifier: The tax code to analyze (can be code or ID)
        window_size: Size of the moving average window in years
        years: Optional list of years to include in analysis, defaults to all years
        
    Returns:
        Dictionary with moving average data
    """
    logger.info(f"Computing {window_size}-year moving average for tax code {tax_code_identifier}")
    
    try:
        # Get basic statistics (includes historical data)
        stats = compute_basic_statistics(tax_code_identifier, years)
        
        if 'error' in stats:
            return stats
        
        historical_data = stats['historical_data']
        
        if len(historical_data) < window_size:
            return {
                'error': f"Insufficient data for {window_size}-year moving average (need at least {window_size} years)",
                'historical_data': historical_data
            }
        
        # Compute moving averages
        moving_averages = []
        
        for i in range(len(historical_data) - window_size + 1):
            window = historical_data[i:i + window_size]
            avg_rate = sum(item['levy_rate'] for item in window) / window_size
            
            moving_averages.append({
                'start_year': window[0]['year'],
                'end_year': window[-1]['year'],
                'years': [item['year'] for item in window],
                'average_rate': avg_rate,
                'window_size': window_size
            })
        
        return {
            'tax_code': stats['tax_code'],
            'tax_code_id': stats['tax_code_id'],
            'window_size': window_size,
            'moving_averages': moving_averages,
            'historical_data': historical_data
        }
        
    except Exception as e:
        logger.error(f"Error computing moving average: {str(e)}")
        return {
            'error': f"Error computing moving average: {str(e)}",
            'historical_data': []
        }


def forecast_future_rates(tax_code_identifier: str, forecast_years: int = 3, 
                         method: str = 'linear', years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Forecast future levy rates based on historical data.
    
    Args:
        tax_code_identifier: The tax code to forecast (can be code or ID)
        forecast_years: Number of years to forecast
        method: Forecasting method ('linear', 'average', 'weighted')
        years: Optional list of years to include in analysis, defaults to all years
        
    Returns:
        Dictionary with forecasting results
    """
    logger.info(f"Forecasting {forecast_years} years for tax code {tax_code_identifier} using {method} method")
    
    try:
        # Get basic statistics (includes historical data)
        stats = compute_basic_statistics(tax_code_identifier, years)
        
        if 'error' in stats:
            return stats
        
        historical_data = stats['historical_data']
        
        if len(historical_data) < 2 and method == 'linear':
            return {
                'error': f"Linear forecasting requires at least 2 years of historical data",
                'historical_data': historical_data
            }
        
        # Simple validation
        if forecast_years <= 0:
            return {
                'error': "Forecast years must be positive",
                'historical_data': historical_data
            }
        
        if method not in ['linear', 'average', 'weighted']:
            return {
                'error': f"Unsupported forecasting method: {method}",
                'historical_data': historical_data
            }
        
        # Extract years and rates for forecasting
        years_data = [item['year'] for item in historical_data]
        rates = [item['levy_rate'] for item in historical_data]
        
        # Generate forecast based on selected method
        forecast_results = []
        
        # Start forecasting from the year after the last historical year
        last_year = max(years_data)
        
        if method == 'linear':
            # Perform linear regression if we have enough data points
            if len(years_data) >= 2:
                # Normalize years to avoid numerical instability
                base_year = min(years_data)
                x = np.array([year - base_year for year in years_data])
                y = np.array(rates)
                
                # Linear regression formula: y = mx + b
                n = len(x)
                m = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
                b = (np.sum(y) - m * np.sum(x)) / n
                
                # Generate forecasts
                for i in range(1, forecast_years + 1):
                    forecast_year = last_year + i
                    forecast_x = forecast_year - base_year
                    forecast_rate = m * forecast_x + b
                    
                    # Keep the forecast within reasonable bounds
                    forecast_rate = max(0.0, forecast_rate)  # No negative rates
                    
                    forecast_results.append({
                        'year': forecast_year,
                        'forecasted_rate': forecast_rate,
                        'method': 'linear regression'
                    })
            
        elif method == 'average':
            # Simple average of all historical rates
            avg_rate = sum(rates) / len(rates)
            
            for i in range(1, forecast_years + 1):
                forecast_year = last_year + i
                forecast_results.append({
                    'year': forecast_year,
                    'forecasted_rate': avg_rate,
                    'method': 'historical average'
                })
                
        elif method == 'weighted':
            # Weighted average with more recent years having higher weights
            total_weight = sum(range(1, len(rates) + 1))
            weighted_sum = sum(rates[i] * (i + 1) for i in range(len(rates))) / total_weight
            
            for i in range(1, forecast_years + 1):
                forecast_year = last_year + i
                forecast_results.append({
                    'year': forecast_year,
                    'forecasted_rate': weighted_sum,
                    'method': 'weighted average'
                })
        
        return {
            'tax_code': stats['tax_code'],
            'tax_code_id': stats['tax_code_id'],
            'forecast_method': method,
            'forecast_years': forecast_years,
            'forecasted_data': forecast_results,
            'historical_data': historical_data
        }
        
    except Exception as e:
        logger.error(f"Error forecasting rates: {str(e)}")
        return {
            'error': f"Error forecasting rates: {str(e)}",
            'historical_data': []
        }


def detect_levy_rate_anomalies(tax_code_identifier: str, threshold: float = 2.0, 
                             years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Detect anomalies in historical levy rates using statistical methods.
    
    Args:
        tax_code_identifier: The tax code to analyze (can be code or ID)
        threshold: Z-score threshold for anomaly detection
        years: Optional list of years to include in analysis, defaults to all years
        
    Returns:
        Dictionary with anomaly detection results
    """
    logger.info(f"Detecting anomalies for tax code {tax_code_identifier} with threshold {threshold}")
    
    try:
        # Get basic statistics (includes historical data)
        stats = compute_basic_statistics(tax_code_identifier, years)
        
        if 'error' in stats:
            return stats
        
        historical_data = stats['historical_data']
        
        if len(historical_data) < 3:
            return {
                'error': f"Anomaly detection requires at least 3 years of data",
                'all_rates': historical_data
            }
        
        # Extract rates for anomaly detection
        rates = [item['levy_rate'] for item in historical_data]
        years_data = [item['year'] for item in historical_data]
        
        # Compute z-scores for anomaly detection
        mean_rate = statistics.mean(rates)
        stddev = statistics.stdev(rates)
        
        anomalies = []
        normal_data = []
        
        for i, item in enumerate(historical_data):
            rate = item['levy_rate']
            year = item['year']
            
            # Handle edge case of zero standard deviation
            if stddev > 0:
                z_score = (rate - mean_rate) / stddev
            else:
                z_score = 0
            
            # Check for anomalies
            is_anomaly = abs(z_score) > threshold
            
            result = {
                'year': year,
                'levy_rate': rate,
                'z_score': z_score,
                'is_anomaly': is_anomaly
            }
            
            if is_anomaly:
                anomalies.append(result)
            else:
                normal_data.append(result)
        
        return {
            'tax_code': stats['tax_code'],
            'tax_code_id': stats['tax_code_id'],
            'threshold': threshold,
            'mean_rate': mean_rate,
            'stddev': stddev,
            'anomalies': anomalies,
            'normal_data': normal_data,
            'all_rates': historical_data
        }
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}")
        return {
            'error': f"Error detecting anomalies: {str(e)}",
            'all_rates': []
        }


def aggregate_by_district(district_id: int, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Aggregate historical levy data by tax district.
    
    Args:
        district_id: The tax district ID to analyze
        years: Optional list of years to include in analysis, defaults to all years
        
    Returns:
        Dictionary with aggregated district data
    """
    logger.info(f"Aggregating data for district ID {district_id} over years {years or 'all'}")
    
    try:
        # Get the district
        district = TaxDistrict.query.get(district_id)
        
        if not district:
            return {'error': f"Tax district with ID {district_id} not found"}
        
        # Get all tax codes for this district
        tax_codes = TaxCode.query.filter_by(district_id=district_id).all()
        
        if not tax_codes:
            return {'error': f"No tax codes found for district {district.district_code}"}
        
        # Build a list of tax code IDs
        tax_code_ids = [tc.id for tc in tax_codes]
        
        # Query historical rates for all tax codes in this district
        query = TaxCodeHistoricalRate.query.filter(TaxCodeHistoricalRate.tax_code_id.in_(tax_code_ids))
        
        # Apply year filter if specified
        if years:
            query = query.filter(TaxCodeHistoricalRate.year.in_(years))
        
        # Order by year and tax code ID
        query = query.order_by(TaxCodeHistoricalRate.year, TaxCodeHistoricalRate.tax_code_id)
        
        # Execute query
        historical_rates = query.all()
        
        if not historical_rates:
            return {
                'error': f"No historical rate data found for district {district.district_code} in specified years",
                'tax_codes': [tc.tax_code for tc in tax_codes]
            }
        
        # Group by year for district-level analysis
        years_data = sorted(set(rate.year for rate in historical_rates))
        
        district_yearly_data = {}
        for year in years_data:
            district_yearly_data[year] = {
                'year': year,
                'total_levy_amount': 0,
                'total_assessed_value': 0,
                'tax_code_count': 0,
                'tax_codes': []
            }
        
        # Aggregate data by tax code and year
        for rate in historical_rates:
            tax_code = next((tc for tc in tax_codes if tc.id == rate.tax_code_id), None)
            if not tax_code:
                continue
                
            year = rate.year
            
            # Add to district yearly totals
            if rate.levy_amount:
                district_yearly_data[year]['total_levy_amount'] += rate.levy_amount
            if rate.total_assessed_value:
                district_yearly_data[year]['total_assessed_value'] += rate.total_assessed_value
            
            district_yearly_data[year]['tax_code_count'] += 1
            district_yearly_data[year]['tax_codes'].append({
                'tax_code': tax_code.tax_code,
                'tax_code_id': tax_code.id,
                'levy_rate': rate.levy_rate,
                'levy_amount': rate.levy_amount,
                'total_assessed_value': rate.total_assessed_value
            })
        
        # Calculate effective rates for each year
        for year_data in district_yearly_data.values():
            if year_data['total_assessed_value'] > 0:
                year_data['effective_rate'] = year_data['total_levy_amount'] / year_data['total_assessed_value']
            else:
                year_data['effective_rate'] = None
        
        # Put yearly data in a list
        district_analysis = list(district_yearly_data.values())
        
        return {
            'district_id': district_id,
            'district_code': district.district_code,
            'district_name': district.district_name,
            'years': years_data,
            'tax_code_count': len(tax_codes),
            'yearly_analysis': district_analysis
        }
        
    except Exception as e:
        logger.error(f"Error aggregating district data: {str(e)}")
        return {'error': f"Error aggregating district data: {str(e)}"}


def generate_comparison_report(start_year: int, end_year: int, 
                          min_change_threshold: float = 0.01) -> Dict[str, Any]:
    """
    Generate a year-over-year comparison report for levy rates.
    
    Args:
        start_year: The starting year for comparison
        end_year: The ending year for comparison
        min_change_threshold: Minimum change threshold to include in report (as decimal)
        
    Returns:
        Dictionary with detailed comparison report
    """
    logger.info(f"Generating comparison report for {start_year} to {end_year}")
    
    try:
        # Validate inputs
        if start_year >= end_year:
            return {'error': f"Start year must be before end year"}
        
        # Get all tax codes with historical data in both years
        start_year_rates = TaxCodeHistoricalRate.query.filter_by(year=start_year).all()
        end_year_rates = TaxCodeHistoricalRate.query.filter_by(year=end_year).all()
        
        if not start_year_rates:
            return {'error': f"No data found for start year {start_year}"}
        
        if not end_year_rates:
            return {'error': f"No data found for end year {end_year}"}
        
        # Create dictionaries for quick lookup
        start_rates = {rate.tax_code_id: rate for rate in start_year_rates}
        end_rates = {rate.tax_code_id: rate for rate in end_year_rates}
        
        # Find tax codes present in both years
        common_tax_code_ids = set(start_rates.keys()).intersection(set(end_rates.keys()))
        
        if not common_tax_code_ids:
            return {'error': f"No common tax codes found between years {start_year} and {end_year}"}
        
        # Get tax code objects for these IDs
        tax_codes = TaxCode.query.filter(TaxCode.id.in_(common_tax_code_ids)).all()
        tax_code_lookup = {tc.id: tc for tc in tax_codes}
        
        # Generate comparison data
        comparison_data = []
        totals = {
            'start_year': {
                'year': start_year,
                'total_levy_amount': 0,
                'total_assessed_value': 0
            },
            'end_year': {
                'year': end_year,
                'total_levy_amount': 0,
                'total_assessed_value': 0
            },
            'increases': 0,
            'decreases': 0,
            'no_change': 0
        }
        
        for tax_code_id in common_tax_code_ids:
            start_rate = start_rates[tax_code_id]
            end_rate = end_rates[tax_code_id]
            tax_code = tax_code_lookup.get(tax_code_id)
            
            if not tax_code:
                continue
            
            # Calculate changes
            rate_change = end_rate.levy_rate - start_rate.levy_rate
            
            if start_rate.levy_rate > 0:
                pct_change = (rate_change / start_rate.levy_rate) * 100
            else:
                pct_change = 0 if rate_change == 0 else float('inf')
            
            # Only include significant changes
            if abs(rate_change) >= min_change_threshold:
                comparison_item = {
                    'tax_code': tax_code.tax_code,
                    'tax_code_id': tax_code_id,
                    'district_id': tax_code.district_id,
                    'district_code': tax_code.district.district_code if tax_code.district else 'Unknown',
                    'start_year': {
                        'year': start_year,
                        'levy_rate': start_rate.levy_rate,
                        'levy_amount': start_rate.levy_amount,
                        'assessed_value': start_rate.total_assessed_value
                    },
                    'end_year': {
                        'year': end_year,
                        'levy_rate': end_rate.levy_rate,
                        'levy_amount': end_rate.levy_amount,
                        'assessed_value': end_rate.total_assessed_value
                    },
                    'changes': {
                        'rate_change': rate_change,
                        'pct_change': pct_change
                    }
                }
                
                comparison_data.append(comparison_item)
                
                # Update counters
                if rate_change > 0:
                    totals['increases'] += 1
                elif rate_change < 0:
                    totals['decreases'] += 1
                else:
                    totals['no_change'] += 1
            
            # Update totals
            if start_rate.levy_amount:
                totals['start_year']['total_levy_amount'] += start_rate.levy_amount
            if start_rate.total_assessed_value:
                totals['start_year']['total_assessed_value'] += start_rate.total_assessed_value
            
            if end_rate.levy_amount:
                totals['end_year']['total_levy_amount'] += end_rate.levy_amount
            if end_rate.total_assessed_value:
                totals['end_year']['total_assessed_value'] += end_rate.total_assessed_value
        
        # Calculate overall changes
        levy_change = totals['end_year']['total_levy_amount'] - totals['start_year']['total_levy_amount']
        if totals['start_year']['total_levy_amount'] > 0:
            levy_pct_change = (levy_change / totals['start_year']['total_levy_amount']) * 100
        else:
            levy_pct_change = 0 if levy_change == 0 else float('inf')
        
        # Calculate effective rates
        if totals['start_year']['total_assessed_value'] > 0:
            totals['start_year']['effective_rate'] = totals['start_year']['total_levy_amount'] / totals['start_year']['total_assessed_value']
        else:
            totals['start_year']['effective_rate'] = None
            
        if totals['end_year']['total_assessed_value'] > 0:
            totals['end_year']['effective_rate'] = totals['end_year']['total_levy_amount'] / totals['end_year']['total_assessed_value']
        else:
            totals['end_year']['effective_rate'] = None
        
        # Overall effective rate change
        if totals['start_year']['effective_rate'] is not None and totals['end_year']['effective_rate'] is not None:
            totals['effective_rate_change'] = totals['end_year']['effective_rate'] - totals['start_year']['effective_rate']
            
            if totals['start_year']['effective_rate'] > 0:
                totals['effective_rate_pct_change'] = (totals['effective_rate_change'] / totals['start_year']['effective_rate']) * 100
            else:
                totals['effective_rate_pct_change'] = 0 if totals['effective_rate_change'] == 0 else float('inf')
        
        return {
            'start_year': start_year,
            'end_year': end_year,
            'year_difference': end_year - start_year,
            'min_change_threshold': min_change_threshold,
            'tax_codes_analyzed': len(common_tax_code_ids),
            'significant_changes': len(comparison_data),
            'comparison_data': comparison_data,
            'totals': totals,
            'overall_changes': {
                'levy_change': levy_change,
                'levy_pct_change': levy_pct_change
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating comparison report: {str(e)}")
        return {'error': f"Error generating comparison report: {str(e)}"}