"""
AI-enhanced forecasting utilities.

This module provides AI-powered enhancements for the forecasting system:
- AI-based model selection
- Natural language explanations of forecasts
- Anomaly detection in historical data
- AI-generated recommendations based on forecasts
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import json
import statsmodels.api as sm
from statsmodels.tsa.stattools import acf, pacf, adfuller
from scipy import stats
from anthropic import Anthropic

from utils.forecasting_utils import (
    ForecastModel,
    LinearTrendModel,
    ExponentialSmoothingModel,
    ARIMAModel,
    create_forecast_model
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Anthropic client
anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
if anthropic_key:
    client = Anthropic(api_key=anthropic_key)
else:
    logger.warning("ANTHROPIC_API_KEY not found. AI-enhanced features will be limited.")
    client = None


def ai_forecast_model_selector(data: Dict[str, List]) -> ForecastModel:
    """
    Use AI and statistical analysis to select the most appropriate forecasting model.
    
    Args:
        data: Dictionary containing historical years and rates
        
    Returns:
        The selected forecast model
    """
    try:
        # Default to linear model if statistical analysis fails
        model_type = "linear"
        scenario = "baseline"
        
        if len(data['years']) < 3:
            logger.warning("Insufficient data for model selection, defaulting to linear model")
            return create_forecast_model(model_type, data, scenario)
        
        # Convert to pandas Series for analysis
        series = pd.Series(data['rates'], index=data['years'])
        
        # Test for stationarity (Augmented Dickey-Fuller test)
        adf_result = adfuller(series)
        is_stationary = adf_result[1] < 0.05  # p-value < 0.05 means stationary
        
        # Calculate auto-correlation and partial auto-correlation
        acf_values = acf(series, nlags=min(5, len(series) - 1))
        pacf_values = pacf(series, nlags=min(5, len(series) - 1))
        
        # Check for seasonality
        has_seasonality = False
        if len(series) >= 8:  # Need enough data to detect seasonality
            # Simple test: check if any autocorrelation value (excluding lag 0) is significant
            acf_abs = np.abs(acf_values[1:])
            has_seasonality = any(acf_abs > 1.96 / np.sqrt(len(series)))
        
        # Determine best model based on analysis
        if has_seasonality and len(series) >= 10:
            model_type = "arima"
        elif has_seasonality and len(series) >= 6:
            model_type = "exponential"
        elif not is_stationary and len(series) >= 7:
            model_type = "arima"
        else:
            # Test for linearity
            years_array = np.array(data['years'])
            rates_array = np.array(data['rates'])
            slope, intercept, r_value, p_value, std_err = stats.linregress(years_array, rates_array)
            
            r_squared = r_value**2
            is_linear = r_squared > 0.7 and p_value < 0.05
            
            if is_linear:
                model_type = "linear"
            elif len(series) >= 5:
                model_type = "exponential"
            else:
                model_type = "linear"  # Default to linear for small datasets
        
        # Use Claude if available to potentially refine the selection
        if client:
            try:
                # Prepare data for Claude
                data_stats = {
                    "sample_size": len(data['years']),
                    "is_stationary": is_stationary,
                    "has_seasonality": has_seasonality,
                    "r_squared": r_squared if 'r_squared' in locals() else None,
                    "adf_p_value": adf_result[1],
                    "current_selection": model_type
                }
                
                # Ask Claude for recommendation
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=150,
                    temperature=0,
                    system="You are a time-series forecasting expert helping to select the best model for property tax levy rate forecasting. Only respond with a single model type from these options: 'linear', 'exponential', or 'arima'. Nothing else.",
                    messages=[
                        {
                            "role": "user", 
                            "content": f"Based on these time series statistics, what is the most appropriate forecasting model to use? {json.dumps(data_stats)}"
                        }
                    ]
                )
                
                # Parse Claude's recommendation
                claude_recommendation = response.content[0].text.strip().lower()
                if claude_recommendation in ["linear", "exponential", "arima"]:
                    # If Claude and statistical analysis agree, use that model
                    # If they disagree, we'll still use Claude's recommendation as it may have detected patterns
                    # our simple tests missed
                    logger.info(f"Statistical analysis recommended '{model_type}', Claude recommended '{claude_recommendation}'")
                    model_type = claude_recommendation
            except Exception as e:
                logger.warning(f"Error using Claude for model selection: {str(e)}")
                # Continue with statistical selection
        
        # Create and return the selected model
        return create_forecast_model(model_type, data, scenario)
    
    except Exception as e:
        logger.error(f"Error in AI model selection: {str(e)}")
        # Fall back to linear model on error
        return create_forecast_model("linear", data, "baseline")


def generate_forecast_explanation(forecast_data: Dict[str, Any]) -> str:
    """
    Generate a natural language explanation of forecast results.
    
    Args:
        forecast_data: Dictionary containing forecast results
        
    Returns:
        A natural language explanation of the forecast
    """
    try:
        # Default explanation if AI fails
        default_explanation = (
            f"Forecast for tax code {forecast_data['tax_code']} shows "
            f"projected rates from {forecast_data['forecast']['years'][0]} to {forecast_data['forecast']['years'][-1]}. "
            f"The forecast was generated using a {forecast_data['forecast']['model_type']} model "
            f"with a {forecast_data['forecast']['scenario']} scenario."
        )
        
        # Use Claude if available
        if client:
            try:
                # Format data for better readability
                formatted_forecast = {
                    "tax_code": forecast_data['tax_code'],
                    "model_type": forecast_data['forecast']['model_type'],
                    "scenario": forecast_data['forecast']['scenario'],
                    "historical_years": forecast_data['historical_data']['years'],
                    "historical_rates": [round(r, 4) for r in forecast_data['historical_data']['rates']],
                    "forecast_years": forecast_data['forecast']['years'],
                    "forecast_rates": [round(r, 4) for r in forecast_data['forecast']['predicted_rates']],
                    "confidence_intervals": [[round(ci[0], 4), round(ci[1], 4)] for ci in forecast_data['forecast']['confidence_intervals']],
                    "metrics": {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in forecast_data['metrics'].items()}
                }
                
                # Calculate some additional insights
                hist_rates = forecast_data['historical_data']['rates']
                forecast_rates = forecast_data['forecast']['predicted_rates']
                
                avg_hist_rate = sum(hist_rates) / len(hist_rates)
                avg_forecast_rate = sum(forecast_rates) / len(forecast_rates)
                percent_change = ((avg_forecast_rate - avg_hist_rate) / avg_hist_rate) * 100
                
                trend_direction = "increasing" if percent_change > 0 else "decreasing" if percent_change < 0 else "stable"
                
                # Evaluate forecast confidence
                r_squared = forecast_data['metrics'].get('r_squared', 0)
                mape = forecast_data['metrics'].get('mape', 100)
                
                confidence_level = "high" if r_squared > 0.8 and mape < 5 else \
                                "moderate" if r_squared > 0.6 and mape < 10 else "low"
                
                # Add insights to formatted data
                formatted_forecast["insights"] = {
                    "avg_historical_rate": round(avg_hist_rate, 4),
                    "avg_forecast_rate": round(avg_forecast_rate, 4),
                    "percent_change": round(percent_change, 2),
                    "trend_direction": trend_direction,
                    "confidence_level": confidence_level
                }
                
                # Ask Claude to generate an explanation
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    temperature=0.2,
                    system="You are a property tax expert providing clear, concise explanations of tax levy rate forecasts to county assessors. Use plain language but include relevant technical details and metrics where appropriate.",
                    messages=[
                        {
                            "role": "user", 
                            "content": f"Please explain this tax levy rate forecast in a clear, professional paragraph. Focus on the trend, confidence level, and what it means for planning purposes: {json.dumps(formatted_forecast)}"
                        }
                    ]
                )
                
                explanation = response.content[0].text.strip()
                
                if explanation and len(explanation) > 100:
                    return explanation
                else:
                    logger.warning("Claude returned unusable explanation, using default")
                    return default_explanation
            
            except Exception as e:
                logger.warning(f"Error generating forecast explanation: {str(e)}")
                return default_explanation
        else:
            return default_explanation
    
    except Exception as e:
        logger.error(f"Error in forecast explanation generation: {str(e)}")
        return "Unable to generate forecast explanation due to an error."


def detect_anomalies(data: Dict[str, List]) -> List[Dict[str, Any]]:
    """
    Detect anomalies in historical tax rate data.
    
    Args:
        data: Dictionary containing historical years and rates
        
    Returns:
        List of detected anomalies with explanations
    """
    if len(data['years']) < 3:
        logger.warning("Insufficient data for anomaly detection")
        return []
    
    try:
        anomalies = []
        years = data['years']
        rates = data['rates']
        
        # Method 1: Z-score based detection
        z_scores = stats.zscore(rates)
        for i, z in enumerate(z_scores):
            if abs(z) > 2.5:  # Threshold for anomaly
                severity = "high" if abs(z) > 3.5 else "medium" if abs(z) > 3.0 else "low"
                
                explanation = f"The levy rate for {years[i]} is {abs(z):.2f} standard deviations from the mean, " \
                             f"which is unusual compared to other years."
                
                anomalies.append({
                    'year': years[i],
                    'rate': rates[i],
                    'z_score': float(z),
                    'severity': severity,
                    'explanation': explanation,
                    'detection_method': 'z_score'
                })
        
        # Method 2: Regression-based detection
        if len(years) >= 5:
            try:
                # Fit linear trend
                x = np.array(years).reshape(-1, 1)
                model = sm.OLS(rates, sm.add_constant(x)).fit()
                predictions = model.predict()
                residuals = rates - predictions
                
                # Find mean and standard deviation of residuals
                residual_mean = np.mean(residuals)
                residual_std = np.std(residuals)
                
                # Identify points with large residuals
                for i, residual in enumerate(residuals):
                    if abs(residual - residual_mean) > 2.5 * residual_std:
                        # Check if not already detected by z-score method
                        if not any(a['year'] == years[i] and a['detection_method'] == 'z_score' for a in anomalies):
                            severity = "high" if abs(residual - residual_mean) > 3.5 * residual_std else \
                                      "medium" if abs(residual - residual_mean) > 3.0 * residual_std else "low"
                            
                            explanation = f"The levy rate for {years[i]} deviates significantly from the expected trend, " \
                                         f"suggesting an unusual change in tax policy or assessment for that year."
                            
                            anomalies.append({
                                'year': years[i],
                                'rate': rates[i],
                                'deviation': float(residual),
                                'severity': severity,
                                'explanation': explanation,
                                'detection_method': 'trend_deviation'
                            })
            except Exception as e:
                logger.warning(f"Error in regression-based anomaly detection: {str(e)}")
        
        # Use Claude to analyze anomalies if available and if anomalies were found
        if client and anomalies:
            try:
                # Format data for Claude
                formatted_data = {
                    "years": years,
                    "rates": [round(r, 4) for r in rates],
                    "detected_anomalies": anomalies
                }
                
                # Ask Claude to analyze and explain the anomalies
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=800,
                    temperature=0.2,
                    system="You are a property tax expert analyzing anomalies in historical tax levy rates. Provide concise, insightful explanations of detected anomalies, focusing on potential causes like policy changes, economic conditions, or assessment issues.",
                    messages=[
                        {
                            "role": "user", 
                            "content": f"Please analyze these detected anomalies in historical levy rates and provide improved explanations for each one: {json.dumps(formatted_data)}"
                        }
                    ]
                )
                
                ai_analysis = response.content[0].text.strip()
                
                # Try to parse Claude's analysis and update explanations
                # This is a simple approach - in production we would want more structured output
                if "year" in ai_analysis and len(ai_analysis) > 100:
                    for anomaly in anomalies:
                        year_str = str(anomaly['year'])
                        if year_str in ai_analysis:
                            # Find paragraph containing this year
                            paragraphs = ai_analysis.split('\n\n')
                            for para in paragraphs:
                                if year_str in para:
                                    # Use this as the explanation, limited to 300 chars for conciseness
                                    anomaly['explanation'] = para[:300].strip()
                                    if 'ai_enhanced' not in anomaly:
                                        anomaly['ai_enhanced'] = True
                                    break
            
            except Exception as e:
                logger.warning(f"Error using Claude to enhance anomaly explanations: {str(e)}")
        
        return anomalies
    
    except Exception as e:
        logger.error(f"Error in anomaly detection: {str(e)}")
        return []


def generate_forecast_recommendations(forecast_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate AI-powered recommendations based on forecast results.
    
    Args:
        forecast_data: Dictionary containing forecast results
        
    Returns:
        List of recommendations with title, description, and priority
    """
    # Default recommendations if AI fails
    default_recommendations = [
        {
            'title': 'Review Forecast Assumptions',
            'description': 'Review the assumptions used in this forecast to ensure they align with current economic conditions and policy decisions.',
            'priority': 'medium'
        }
    ]
    
    try:
        # Calculate some insights from the forecast data
        hist_rates = forecast_data['historical_data']['rates']
        hist_years = forecast_data['historical_data']['years']
        forecast_rates = forecast_data['forecast']['predicted_rates']
        forecast_years = forecast_data['forecast']['years']
        
        # Check for trend direction
        if len(forecast_rates) > 1:
            trend = forecast_rates[-1] - forecast_rates[0]
            trend_percent = (trend / forecast_rates[0]) * 100 if forecast_rates[0] > 0 else 0
        else:
            trend = 0
            trend_percent = 0
        
        # Get metrics
        metrics = forecast_data.get('metrics', {})
        r_squared = metrics.get('r_squared', 0)
        mape = metrics.get('mape', 0)
        
        # Get scenario
        scenario = forecast_data['forecast'].get('scenario', 'baseline')
        
        # Generate recommendations based on insights without Claude
        recommendations = []
        
        # Recommendation based on trend
        if abs(trend_percent) > 10:
            if trend > 0:
                recommendations.append({
                    'title': 'Plan for Increasing Rates',
                    'description': f'Levy rates are projected to increase by {trend_percent:.1f}% over the forecast period. Consider strategies to communicate and manage this increase.',
                    'priority': 'high' if trend_percent > 15 else 'medium'
                })
            else:
                recommendations.append({
                    'title': 'Address Projected Rate Decrease',
                    'description': f'Levy rates are projected to decrease by {abs(trend_percent):.1f}% over the forecast period. Evaluate impact on revenue and services.',
                    'priority': 'high' if abs(trend_percent) > 15 else 'medium'
                })
        
        # Recommendation based on forecast confidence
        if r_squared < 0.7 or mape > 5:
            recommendations.append({
                'title': 'Consider Alternative Scenarios',
                'description': 'This forecast has moderate to low confidence. Consider multiple scenarios for planning purposes.',
                'priority': 'medium' if r_squared > 0.5 else 'high'
            })
        
        # Use Claude if available to generate more nuanced recommendations
        if client:
            try:
                # Format data for Claude
                formatted_data = {
                    "tax_code": forecast_data['tax_code'],
                    "model_type": forecast_data['forecast']['model_type'],
                    "scenario": scenario,
                    "historical_years": hist_years,
                    "historical_rates": [round(r, 4) for r in hist_rates],
                    "forecast_years": forecast_years,
                    "forecast_rates": [round(r, 4) for r in forecast_rates],
                    "trend_percent": round(trend_percent, 2),
                    "metrics": {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in metrics.items()}
                }
                
                # Ask Claude to generate recommendations
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    temperature=0.3,
                    system="""You are a property tax expert providing strategic recommendations based on levy rate forecasts. 
                    Format your response as a JSON list of recommendation objects.
                    Each recommendation should have:
                    1. title: A short, action-oriented title
                    2. description: A detailed explanation (1-2 sentences)
                    3. priority: 'low', 'medium', or 'high'
                    
                    Example format:
                    [
                        {
                            "title": "Review High Growth Areas",
                            "description": "The projected 12% increase suggests significant growth. Identify high-growth neighborhoods to ensure equitable assessment.",
                            "priority": "high"
                        },
                        {
                            "title": "Update Communication Strategy",
                            "description": "Prepare materials explaining the projected rate changes to property owners.",
                            "priority": "medium"
                        }
                    ]
                    
                    Respond ONLY with the JSON array, nothing else.""",
                    messages=[
                        {
                            "role": "user", 
                            "content": f"Based on this tax levy rate forecast, what are your top 3-5 strategic recommendations? {json.dumps(formatted_data)}"
                        }
                    ]
                )
                
                # Parse Claude's response
                ai_recommendations = response.content[0].text.strip()
                
                # Try to parse the JSON
                try:
                    # Find JSON array in the response
                    import re
                    json_match = re.search(r'\[.*\]', ai_recommendations, re.DOTALL)
                    if json_match:
                        ai_recommendations = json_match.group(0)
                    
                    parsed_recs = json.loads(ai_recommendations)
                    
                    # Validate structure
                    valid_recs = []
                    for rec in parsed_recs:
                        if ('title' in rec and 'description' in rec and 'priority' in rec and
                            rec['priority'] in ['low', 'medium', 'high']):
                            valid_recs.append(rec)
                    
                    if valid_recs:
                        return valid_recs
                except Exception as e:
                    logger.warning(f"Error parsing AI recommendations: {str(e)}")
            
            except Exception as e:
                logger.warning(f"Error generating AI recommendations: {str(e)}")
        
        # Return generated recommendations or default ones if none were generated
        return recommendations if recommendations else default_recommendations
    
    except Exception as e:
        logger.error(f"Error in recommendation generation: {str(e)}")
        return default_recommendations