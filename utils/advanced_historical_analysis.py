"""
Advanced historical data analysis and forecasting tools.

This module provides enhanced analytical capabilities for multi-year levy data:
1. Statistical analysis (mean, median, variance, etc.)
2. Trend identification and forecasting
3. Year-over-year comparisons
4. Data aggregation by district and year
5. Anomaly detection in historical trends
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import statistics
from collections import defaultdict

import numpy as np
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import TaxCode, TaxCodeHistoricalRate, TaxDistrict

logger = logging.getLogger(__name__)

def compute_basic_statistics(tax_code: str, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Compute basic statistical measures for a tax code's levy rates across years.
    
    Args:
        tax_code: The tax code to analyze
        years: Optional list of specific years to analyze (if None, use all available years)
        
    Returns:
        Dictionary with statistical measures
    """
    try:
        # Get the tax code record
        tax_code_record = TaxCode.query.filter_by(code=tax_code).first()
        if not tax_code_record:
            return {
                'error': f'Tax code {tax_code} not found',
                'tax_code': tax_code
            }
        
        # Query for historical rates
        query = TaxCodeHistoricalRate.query.filter_by(tax_code_id=tax_code_record.id)
        
        # Apply years filter if provided
        if years:
            query = query.filter(TaxCodeHistoricalRate.year.in_(years))
        
        # Order by year
        historical_rates = query.order_by(TaxCodeHistoricalRate.year).all()
        
        if not historical_rates:
            return {
                'error': f'No historical data found for tax code {tax_code}',
                'tax_code': tax_code
            }
        
        # Extract rates and years
        rates = [rate.levy_rate for rate in historical_rates]
        years_available = [rate.year for rate in historical_rates]
        
        # Compute statistics
        mean_rate = statistics.mean(rates) if rates else None
        median_rate = statistics.median(rates) if rates else None
        min_rate = min(rates) if rates else None
        max_rate = max(rates) if rates else None
        range_value = max_rate - min_rate if (min_rate is not None and max_rate is not None) else None
        
        # Compute more advanced statistics if we have enough data
        if len(rates) > 1:
            variance = statistics.variance(rates)
            std_deviation = statistics.stdev(rates)
        else:
            variance = 0
            std_deviation = 0
        
        # Convert to dictionaries for JSON serialization
        historical_data = [
            {
                'year': rate.year,
                'levy_rate': rate.levy_rate,
                'levy_amount': rate.levy_amount,
                'total_assessed_value': rate.total_assessed_value
            }
            for rate in historical_rates
        ]
        
        return {
            'tax_code': tax_code,
            'years_analyzed': len(years_available),
            'years_available': years_available,
            'mean_rate': mean_rate,
            'median_rate': median_rate,
            'min_rate': min_rate,
            'max_rate': max_rate,
            'range': range_value,
            'variance': variance,
            'std_deviation': std_deviation,
            'historical_data': historical_data
        }
    
    except Exception as e:
        logger.error(f"Error computing statistics for tax code {tax_code}: {str(e)}")
        return {
            'error': f'Error computing statistics: {str(e)}',
            'tax_code': tax_code
        }

def compute_moving_average(tax_code: str, window_size: int = 3, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Compute moving average for levy rates.
    
    Args:
        tax_code: The tax code to analyze
        window_size: The size of the moving average window
        years: Optional list of specific years to analyze (if None, use all available years)
        
    Returns:
        Dictionary with moving average data
    """
    try:
        # Get basic statistics first (including historical data)
        stats_data = compute_basic_statistics(tax_code, years)
        
        if 'error' in stats_data:
            return stats_data
        
        historical_data = stats_data['historical_data']
        
        # Check if we have enough data for the window size
        if len(historical_data) < window_size:
            return {
                'error': f'Not enough historical data for a window size of {window_size}',
                'tax_code': tax_code,
                'historical_data': historical_data
            }
        
        # Sort by year to ensure proper order
        historical_data.sort(key=lambda x: x['year'])
        
        # Compute moving averages
        moving_averages = []
        for i in range(len(historical_data) - window_size + 1):
            window = historical_data[i:i+window_size]
            window_years = [item['year'] for item in window]
            window_rates = [item['levy_rate'] for item in window]
            
            moving_avg = statistics.mean(window_rates)
            
            moving_averages.append({
                'start_year': min(window_years),
                'end_year': max(window_years),
                'years': window_years,
                'moving_average': moving_avg
            })
        
        return {
            'tax_code': tax_code,
            'window_size': window_size,
            'years_analyzed': len(historical_data),
            'historical_data': historical_data,
            'moving_averages': moving_averages
        }
    
    except Exception as e:
        logger.error(f"Error computing moving average for tax code {tax_code}: {str(e)}")
        return {
            'error': f'Error computing moving average: {str(e)}',
            'tax_code': tax_code
        }

def forecast_future_rates(tax_code: str, forecast_years: int = 3, 
                         method: str = 'linear', years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Forecast future levy rates based on historical trends.
    
    Args:
        tax_code: The tax code to forecast
        forecast_years: Number of years to forecast
        method: Forecasting method ('linear', 'average', 'weighted')
        years: Optional list of specific years to use as base for forecasting
        
    Returns:
        Dictionary with forecasting results
    """
    try:
        # Get historical data first
        stats_data = compute_basic_statistics(tax_code, years)
        
        if 'error' in stats_data:
            return stats_data
        
        historical_data = stats_data['historical_data']
        
        # Need at least 2 years for linear regression, 1 for average
        min_years_required = 2 if method == 'linear' else 1
        if len(historical_data) < min_years_required:
            return {
                'error': f'Not enough historical data for forecasting (need at least {min_years_required} years)',
                'tax_code': tax_code,
                'method': method,
                'historical_data': historical_data
            }
        
        # Sort by year
        historical_data.sort(key=lambda x: x['year'])
        
        # Prepare arrays for forecasting
        hist_years = np.array([item['year'] for item in historical_data])
        hist_rates = np.array([item['levy_rate'] for item in historical_data])
        
        # Generate years to forecast
        max_historical_year = max(hist_years)
        forecast_year_values = [max_historical_year + i + 1 for i in range(forecast_years)]
        
        # Apply selected forecasting method
        forecasts = []
        
        if method == 'linear':
            # Linear regression using numpy polyfit (degree 1)
            slope, intercept = np.polyfit(hist_years, hist_rates, 1)
            
            for year in forecast_year_values:
                forecasted_rate = slope * year + intercept
                
                # Ensure rate is positive and reasonable
                forecasted_rate = max(0.0001, forecasted_rate)
                
                # Assess confidence based on historical data stability and trend
                confidence = calculate_forecast_confidence(historical_data, slope)
                
                forecasts.append({
                    'year': year, 
                    'forecasted_rate': forecasted_rate,
                    'confidence': confidence
                })
        
        elif method == 'average':
            # Simple average of all historical rates
            avg_rate = np.mean(hist_rates)
            
            for year in forecast_year_values:
                # Assess confidence (medium by default for average method)
                confidence = 'medium'
                
                forecasts.append({
                    'year': year, 
                    'forecasted_rate': avg_rate,
                    'confidence': confidence
                })
        
        elif method == 'weighted':
            # Weighted average giving more weight to recent years
            weights = np.arange(1, len(hist_rates) + 1)  # 1, 2, 3, ... (more weight to recent)
            weighted_avg = np.average(hist_rates, weights=weights)
            
            for i, year in enumerate(forecast_year_values):
                # For weighted average, reduce confidence as we get further into the future
                if i == 0:
                    confidence = 'medium-high'
                elif i == 1:
                    confidence = 'medium'
                else:
                    confidence = 'medium-low'
                    
                forecasts.append({
                    'year': year, 
                    'forecasted_rate': weighted_avg,
                    'confidence': confidence
                })
        
        return {
            'tax_code': tax_code,
            'method': method,
            'years_analyzed': len(historical_data),
            'historical_data': historical_data,
            'forecasts': forecasts
        }
    
    except Exception as e:
        logger.error(f"Error forecasting rates for tax code {tax_code}: {str(e)}")
        return {
            'error': f'Error forecasting rates: {str(e)}',
            'tax_code': tax_code,
            'method': method
        }

def calculate_forecast_confidence(historical_data: List[Dict[str, Any]], trend_slope: float) -> str:
    """
    Calculate confidence level for forecasts based on historical data stability.
    
    Args:
        historical_data: Historical rate data
        trend_slope: Slope of the trend line
        
    Returns:
        Confidence level as string ('low', 'medium', 'high')
    """
    # Extract rates for analysis
    rates = [item['levy_rate'] for item in historical_data]
    
    # Not enough data for high confidence
    if len(rates) < 3:
        return 'low'
    
    # Calculate coefficient of variation to measure stability
    mean_rate = statistics.mean(rates)
    
    # Avoid division by zero
    if mean_rate == 0:
        coefficient_of_variation = float('inf')
    else:
        std_dev = statistics.stdev(rates)
        coefficient_of_variation = std_dev / mean_rate
    
    # Analyze trend direction and magnitude
    trend_magnitude = abs(trend_slope)
    
    # Determine confidence
    if coefficient_of_variation < 0.05 and trend_magnitude < 0.001:
        return 'high'  # Very stable with minimal trend
    elif coefficient_of_variation < 0.10 and trend_magnitude < 0.005:
        return 'medium-high'  # Fairly stable with mild trend
    elif coefficient_of_variation < 0.20 and trend_magnitude < 0.01:
        return 'medium'  # Moderate stability
    elif coefficient_of_variation < 0.30:
        return 'medium-low'  # Less stable
    else:
        return 'low'  # Highly variable or extreme trend

def detect_levy_rate_anomalies(tax_code: str, threshold: float = 2.0, 
                            years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Detect anomalies in historical levy rates.
    
    Args:
        tax_code: The tax code to analyze
        threshold: Z-score threshold for anomaly detection (default: 2.0)
        years: Optional list of specific years to analyze
        
    Returns:
        Dictionary with anomaly detection results
    """
    try:
        # Get the tax code data
        stats_data = compute_basic_statistics(tax_code, years)
        
        if 'error' in stats_data:
            return stats_data
        
        historical_data = stats_data['historical_data']
        
        # Need at least 3 data points for meaningful anomaly detection
        if len(historical_data) < 3:
            return {
                'error': 'Not enough data for anomaly detection (need at least 3 years)',
                'tax_code': tax_code,
                'threshold': threshold
            }
        
        # Extract rates and years
        rates = np.array([item['levy_rate'] for item in historical_data])
        years_list = [item['year'] for item in historical_data]
        
        # Calculate mean and standard deviation
        mean_rate = np.mean(rates)
        std_dev = np.std(rates)
        
        # Detect anomalies using Z-score
        anomalies = []
        all_rates = []
        
        for i, item in enumerate(historical_data):
            rate = item['levy_rate']
            z_score = (rate - mean_rate) / std_dev if std_dev != 0 else 0
            
            # Determine direction of anomaly
            direction = 'above' if rate > mean_rate else 'below'
            
            # Calculate percent difference from mean
            if mean_rate == 0:
                percent_diff = float('inf') if rate > 0 else 0
            else:
                percent_diff = ((rate - mean_rate) / mean_rate) * 100
            
            rate_data = {
                'year': item['year'],
                'rate': rate
            }
            all_rates.append(rate_data)
            
            # Check if Z-score exceeds threshold
            if abs(z_score) >= threshold:
                anomalies.append({
                    'year': item['year'],
                    'rate': rate,
                    'z_score': z_score,
                    'direction': direction,
                    'percent_diff_from_mean': percent_diff
                })
        
        return {
            'tax_code': tax_code,
            'threshold': threshold,
            'years_analyzed': len(historical_data),
            'mean_rate': mean_rate,
            'std_deviation': std_dev,
            'anomalies': sorted(anomalies, key=lambda x: abs(x['z_score']), reverse=True),
            'all_rates': all_rates
        }
    
    except Exception as e:
        logger.error(f"Error detecting anomalies for tax code {tax_code}: {str(e)}")
        return {
            'error': f'Error detecting anomalies: {str(e)}',
            'tax_code': tax_code,
            'threshold': threshold
        }

def aggregate_by_district(district_id: int, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Aggregate historical levy data by tax district.
    
    Args:
        district_id: The tax district ID to analyze
        years: Optional list of specific years to analyze
        
    Returns:
        Dictionary with aggregated district data
    """
    try:
        # Query district relationships to get all levy codes
        district_query = TaxDistrict.query.filter_by(tax_district_id=district_id)
        
        if years:
            district_query = district_query.filter(TaxDistrict.year.in_(years))
        
        district_records = district_query.order_by(TaxDistrict.year, TaxDistrict.levy_code).all()
        
        if not district_records:
            return {
                'error': f'No data found for tax district {district_id}',
                'district_id': district_id
            }
        
        # Extract all levy codes for this district
        all_levy_codes = set()
        levy_codes_by_year = defaultdict(set)
        
        for record in district_records:
            all_levy_codes.add(record.levy_code)
            all_levy_codes.add(record.linked_levy_code)
            levy_codes_by_year[record.year].add(record.levy_code)
            levy_codes_by_year[record.year].add(record.linked_levy_code)
        
        # Get the years represented in the data
        all_years = sorted(levy_codes_by_year.keys())
        
        # Analyze each year
        aggregated_data = []
        
        for year in all_years:
            year_levy_codes = list(levy_codes_by_year[year])
            
            # Get tax code IDs for these levy codes
            tax_codes = TaxCode.query.filter(TaxCode.code.in_(year_levy_codes)).all()
            tax_code_map = {tc.code: tc.id for tc in tax_codes}
            
            # Get historical rates for this year
            historical_rates = []
            for levy_code in year_levy_codes:
                if levy_code in tax_code_map:
                    tax_code_id = tax_code_map[levy_code]
                    rate_record = TaxCodeHistoricalRate.query.filter_by(
                        tax_code_id=tax_code_id, 
                        year=year
                    ).first()
                    
                    if rate_record:
                        historical_rates.append({
                            'code': levy_code,
                            'rate': rate_record.levy_rate
                        })
            
            # Only include years with rate data
            if historical_rates:
                # Calculate statistics
                rates = [r['rate'] for r in historical_rates]
                average_rate = statistics.mean(rates) if rates else None
                median_rate = statistics.median(rates) if rates else None
                min_rate = min(rates) if rates else None
                max_rate = max(rates) if rates else None
                
                year_data = {
                    'year': year,
                    'num_levy_codes': len(year_levy_codes),
                    'levy_codes': sorted(year_levy_codes),
                    'average_rate': average_rate,
                    'median_rate': median_rate,
                    'min_rate': min_rate,
                    'max_rate': max_rate,
                    'rates': historical_rates
                }
                
                aggregated_data.append(year_data)
        
        return {
            'district_id': district_id,
            'levy_codes': sorted(list(all_levy_codes)),
            'years_analyzed': all_years,
            'aggregated_data': aggregated_data
        }
    
    except Exception as e:
        logger.error(f"Error aggregating data for district {district_id}: {str(e)}")
        return {
            'error': f'Error aggregating district data: {str(e)}',
            'district_id': district_id
        }

def generate_comparison_report(start_year: int, end_year: int, 
                              min_change_threshold: float = 0.01) -> Dict[str, Any]:
    """
    Generate a comprehensive year-over-year comparison report.
    
    Args:
        start_year: The starting year for comparison
        end_year: The ending year for comparison
        min_change_threshold: Minimum change threshold to include in report (as decimal)
        
    Returns:
        Dictionary with detailed comparison report
    """
    try:
        if start_year >= end_year:
            return {
                'error': 'Start year must be before end year',
                'start_year': start_year,
                'end_year': end_year
            }
        
        # Get tax codes that have data for both years
        start_year_rates = TaxCodeHistoricalRate.query.filter_by(year=start_year).all()
        end_year_rates = TaxCodeHistoricalRate.query.filter_by(year=end_year).all()
        
        if not start_year_rates:
            return {
                'error': f'No data found for start year {start_year}',
                'start_year': start_year,
                'end_year': end_year
            }
        
        if not end_year_rates:
            return {
                'error': f'No data found for end year {end_year}',
                'start_year': start_year,
                'end_year': end_year
            }
        
        # Create mappings for easy lookup
        start_year_map = {rate.tax_code_id: rate for rate in start_year_rates}
        end_year_map = {rate.tax_code_id: rate for rate in end_year_rates}
        
        # Find overlapping tax codes
        common_tax_code_ids = set(start_year_map.keys()) & set(end_year_map.keys())
        
        # Get tax code objects for all the common IDs
        tax_codes = TaxCode.query.filter(TaxCode.id.in_(common_tax_code_ids)).all()
        tax_code_map = {tc.id: tc for tc in tax_codes}
        
        # Analyze changes
        tax_code_changes = []
        
        for tax_code_id in common_tax_code_ids:
            start_rate = start_year_map[tax_code_id].levy_rate
            end_rate = end_year_map[tax_code_id].levy_rate
            
            rate_change = end_rate - start_rate
            
            # Calculate percent change safely
            if start_rate == 0:
                percent_change = float('inf') if end_rate > 0 else 0
            else:
                percent_change = (rate_change / start_rate) * 100
            
            # Determine direction
            if rate_change > 0:
                direction = 'increase'
            elif rate_change < 0:
                direction = 'decrease'
            else:
                direction = 'none'
            
            # Only include significant changes
            if abs(percent_change) >= min_change_threshold * 100 or direction == 'none':
                tax_code_changes.append({
                    'tax_code': tax_code_map[tax_code_id].code,
                    'start_rate': start_rate,
                    'end_rate': end_rate,
                    'rate_change': rate_change,
                    'percent_change': percent_change,
                    'direction': direction
                })
        
        # Sort by percent change (absolute value) descending
        tax_code_changes.sort(key=lambda x: abs(x['percent_change']), reverse=True)
        
        # Compute summary statistics
        total_tax_codes = len(common_tax_code_ids)
        increases = sum(1 for change in tax_code_changes if change['direction'] == 'increase')
        decreases = sum(1 for change in tax_code_changes if change['direction'] == 'decrease')
        no_change = sum(1 for change in tax_code_changes if change['direction'] == 'none')
        
        # Calculate averages
        all_changes = [change['rate_change'] for change in tax_code_changes]
        all_percent_changes = [change['percent_change'] for change in tax_code_changes 
                            if not np.isinf(change['percent_change'])]  # Exclude infinite values
        
        average_rate_change = statistics.mean(all_changes) if all_changes else 0
        average_percent_change = statistics.mean(all_percent_changes) if all_percent_changes else 0
        
        # Find max increase and decrease
        max_increase = None
        max_decrease = None
        
        for change in tax_code_changes:
            if change['direction'] == 'increase':
                if max_increase is None or change['percent_change'] > max_increase['percent_change']:
                    max_increase = change
            elif change['direction'] == 'decrease':
                if max_decrease is None or change['percent_change'] < max_decrease['percent_change']:
                    max_decrease = change
        
        # Create summary
        summary = {
            'total_tax_codes': total_tax_codes,
            'tax_codes_with_significant_change': len(tax_code_changes),
            'increases': increases,
            'decreases': decreases,
            'no_change': no_change,
            'average_rate_change': average_rate_change,
            'average_percent_change': average_percent_change,
            'max_increase': max_increase,
            'max_decrease': max_decrease
        }
        
        return {
            'start_year': start_year,
            'end_year': end_year,
            'min_change_threshold': min_change_threshold * 100,  # Convert back to percentage
            'summary': summary,
            'tax_code_changes': tax_code_changes
        }
    
    except Exception as e:
        logger.error(f"Error generating comparison report: {str(e)}")
        return {
            'error': f'Error generating comparison report: {str(e)}',
            'start_year': start_year,
            'end_year': end_year
        }