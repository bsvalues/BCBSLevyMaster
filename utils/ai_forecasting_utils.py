"""
AI-enhanced forecasting utilities for the Levy Calculation Application.

This module provides functions that use Claude API to generate explanations
and recommendations for forecast results, as well as AI-enhanced model selection
and anomaly detection.
"""

import os
import numpy as np
import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import anthropic
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.seasonal import seasonal_decompose

from utils.forecasting_utils import (
    BaseForecast, 
    LinearRateForecast, 
    ExponentialRateForecast, 
    ARIMAForecast, 
    AIEnhancedForecast
)

# Configure logging
logger = logging.getLogger(__name__)

def generate_forecast_explanation(tax_code: str, 
                               historical_years: List[int],
                               historical_rates: List[float],
                               forecast_years: List[int],
                               forecast_rates: List[float],
                               best_model: str,
                               anomalies: List[Dict[str, Any]]) -> str:
    """
    Generate an AI-enhanced explanation of the forecast.
    
    Args:
        tax_code: The tax code being forecasted
        historical_years: List of historical years
        historical_rates: List of historical rates
        forecast_years: List of years in the forecast
        forecast_rates: List of forecasted rates
        best_model: Name of the best performing model
        anomalies: List of detected anomalies
        
    Returns:
        Explanation string
    """
    # Check if Claude API is available
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_key:
        logger.warning("ANTHROPIC_API_KEY environment variable not set")
        return "AI-enhanced explanation not available (API key not configured)."
    
    client = anthropic.Anthropic(api_key=anthropic_key)
    
    # Format historical data
    historical_data = "\n".join([f"Year {year}: Rate {rate:.4f}" 
                              for year, rate in zip(historical_years, historical_rates)])
    
    # Format forecast data
    forecast_data = "\n".join([f"Year {year}: Rate {rate:.4f}" 
                            for year, rate in zip(forecast_years, forecast_rates)])
    
    # Format anomalies
    anomalies_text = ""
    if anomalies:
        anomalies_text = "Detected anomalies:\n"
        for anomaly in anomalies:
            anomalies_text += f"- Year {anomaly['year']}: Rate {anomaly['rate']:.4f} "
            anomalies_text += f"(Severity: {anomaly['severity']:.2f}) - {anomaly['description']}\n"
    else:
        anomalies_text = "No anomalies detected in the historical data."
    
    # Create prompt for Claude
    prompt = f"""
    <context>
    You are an expert property tax analyst tasked with explaining a tax levy rate forecast for tax code {tax_code}.
    
    Historical tax levy rates:
    {historical_data}
    
    Forecast tax levy rates (using {best_model} model):
    {forecast_data}
    
    {anomalies_text}
    
    Please provide a clear, concise explanation of the forecast that:
    1. Interprets the historical trend
    2. Explains why the {best_model} model was the best choice
    3. Discusses any anomalies and their potential impact
    4. Identifies economic or policy factors that might be influencing the rates
    5. Evaluates whether the forecast seems reasonable
    
    Provide your explanation in 3-5 paragraphs of professional but accessible language.
    </context>
    """
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # The newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            max_tokens=1000,
            temperature=0.3,
            system="You are a property tax and economic forecasting expert speaking to an audience of county assessors and public finance administrators. Be clear, precise, and focus on actionable insights.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract explanation from Claude's response
        explanation = response.content[0].text.strip()
        return explanation
    
    except Exception as e:
        logger.error(f"Error generating forecast explanation: {str(e)}")
        return f"An error occurred while generating the explanation: {str(e)}"


def ai_forecast_model_selector(data: Dict[str, Any]) -> BaseForecast:
    """
    Intelligently select the best forecasting model based on data characteristics.
    
    Args:
        data: Dictionary containing historical data with 'years' and 'rates' keys
        
    Returns:
        The selected forecasting model instance
    """
    # Extract data
    years = np.array(data['years'])
    rates = np.array(data['rates'])
    
    if len(years) < 3:
        logger.warning("Insufficient data for advanced model selection, defaulting to linear model")
        return LinearRateForecast(years, rates)
    
    # Analyze data characteristics
    characteristics = analyze_time_series(years, rates)
    
    # Use Claude to analyze data characteristics if available
    ai_model_recommendation = get_ai_model_recommendation(characteristics, data)
    
    if ai_model_recommendation:
        model_type = ai_model_recommendation
    else:
        # Fallback to rule-based selection
        model_type = rule_based_model_selection(characteristics)
    
    # Create the selected model
    if model_type == "exponential":
        return ExponentialRateForecast(years, rates)
    elif model_type == "arima":
        return ARIMAForecast(years, rates)
    else:  # Default to linear
        return LinearRateForecast(years, rates)


def analyze_time_series(years: np.ndarray, rates: np.ndarray) -> Dict[str, Any]:
    """
    Analyze time series data to extract key characteristics.
    
    Args:
        years: Array of years
        rates: Array of rates
        
    Returns:
        Dictionary of data characteristics
    """
    characteristics = {}
    
    # Check for sufficient data
    if len(years) < 3:
        return {'insufficient_data': True}
    
    # Basic statistics
    characteristics['mean'] = float(np.mean(rates))
    characteristics['std_dev'] = float(np.std(rates))
    characteristics['min'] = float(np.min(rates))
    characteristics['max'] = float(np.max(rates))
    characteristics['range'] = float(np.max(rates) - np.min(rates))
    
    # Calculate variance and coefficient of variation
    characteristics['variance'] = float(np.var(rates))
    if characteristics['mean'] > 0:
        characteristics['cv'] = characteristics['std_dev'] / characteristics['mean']
    else:
        characteristics['cv'] = 0
    
    # Calculate trend
    try:
        X = years.reshape(-1, 1)
        model = LinearRegression().fit(X, rates)
        characteristics['linear_trend_slope'] = float(model.coef_[0])
        characteristics['linear_r2'] = float(model.score(X, rates))
    except Exception as e:
        logger.warning(f"Error calculating trend: {str(e)}")
        characteristics['linear_trend_slope'] = 0
        characteristics['linear_r2'] = 0
    
    # Test for stationarity (Augmented Dickey-Fuller test)
    try:
        adf_result = adfuller(rates)
        characteristics['adf_statistic'] = float(adf_result[0])
        characteristics['adf_pvalue'] = float(adf_result[1])
        characteristics['is_stationary'] = adf_result[1] < 0.05
    except Exception as e:
        logger.warning(f"Error in stationarity test: {str(e)}")
        characteristics['is_stationary'] = False
    
    # Check for seasonality if enough data points
    if len(years) >= 4:
        try:
            # Create a regular time series (important for seasonal_decompose)
            ts = pd.Series(rates, index=pd.date_range(start=f'{years[0]}-01-01', periods=len(years), freq='YS'))
            
            # Try to decompose the time series
            if len(years) >= 6:  # Need more data for seasonal decomposition
                result = seasonal_decompose(ts, model='additive', period=min(len(years)//2, 4))
                seasonal = result.seasonal
                characteristics['seasonal_strength'] = float(np.std(seasonal) / (np.std(result.resid) + np.std(seasonal)))
                characteristics['has_seasonality'] = characteristics['seasonal_strength'] > 0.3
            else:
                characteristics['has_seasonality'] = False
        except Exception as e:
            logger.warning(f"Error in seasonality check: {str(e)}")
            characteristics['has_seasonality'] = False
    else:
        characteristics['has_seasonality'] = False
    
    # Check for exponential growth pattern
    try:
        if np.all(rates > 0):  # Can only calculate log on positive values
            log_rates = np.log(rates)
            X = years.reshape(-1, 1)
            log_model = LinearRegression().fit(X, log_rates)
            characteristics['log_linear_r2'] = float(log_model.score(X, log_rates))
            characteristics['exponential_growth'] = characteristics['log_linear_r2'] > characteristics['linear_r2'] + 0.1
        else:
            characteristics['log_linear_r2'] = 0
            characteristics['exponential_growth'] = False
    except Exception as e:
        logger.warning(f"Error checking exponential growth: {str(e)}")
        characteristics['exponential_growth'] = False
    
    # Calculate autocorrelation and partial autocorrelation for ARIMA
    try:
        if len(rates) >= 4:
            acf_values = acf(rates, nlags=min(5, len(rates) - 1))
            pacf_values = pacf(rates, nlags=min(5, len(rates) - 1))
            characteristics['acf_values'] = [float(v) for v in acf_values]
            characteristics['pacf_values'] = [float(v) for v in pacf_values]
            characteristics['significant_autocorrelation'] = any([abs(v) > 0.3 for v in acf_values[1:]])
        else:
            characteristics['significant_autocorrelation'] = False
    except Exception as e:
        logger.warning(f"Error calculating autocorrelation: {str(e)}")
        characteristics['significant_autocorrelation'] = False
    
    return characteristics


def rule_based_model_selection(characteristics: Dict[str, Any]) -> str:
    """
    Select a forecasting model based on data characteristics using rules.
    
    Args:
        characteristics: Dictionary of data characteristics
        
    Returns:
        String name of the selected model
    """
    # Check if data has exponential growth pattern
    if characteristics.get('exponential_growth', False):
        return "exponential"
    
    # Check if data has significant autocorrelation or seasonality (ARIMA)
    if (characteristics.get('significant_autocorrelation', False) or 
        characteristics.get('has_seasonality', False)):
        # Only use ARIMA if there's enough data
        if len(characteristics.get('acf_values', [])) >= 4:
            return "arima"
    
    # Default to linear model
    return "linear"


def get_ai_model_recommendation(characteristics: Dict[str, Any], data: Dict[str, Any]) -> Optional[str]:
    """
    Use Claude API to recommend the best forecasting model.
    
    Args:
        characteristics: Dictionary of time series characteristics
        data: Original data dictionary with years and rates
        
    Returns:
        String name of the recommended model or None if AI is unavailable
    """
    # Check if Claude API is available
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_key:
        logger.warning("ANTHROPIC_API_KEY environment variable not set")
        return None
    
    try:
        client = anthropic.Anthropic(api_key=anthropic_key)
        
        # Format time series data
        years = data['years']
        rates = data['rates']
        data_points = "\n".join([f"Year {year}: Rate {rate:.4f}" for year, rate in zip(years, rates)])
        
        # Format characteristics for Claude
        chars_text = "\n".join([f"{key}: {value}" for key, value in characteristics.items()])
        
        # Create prompt for Claude
        prompt = f"""
        <context>
        You are an expert statistician specializing in time series analysis and forecasting.
        
        You need to recommend the best forecasting model for this property tax levy rate data:
        
        Data points:
        {data_points}
        
        Statistical characteristics:
        {chars_text}
        
        Based on the data characteristics, which of these models would be most appropriate:
        1. Linear model - for simple linear trends
        2. Exponential model - for exponential growth or decline patterns
        3. ARIMA model - for complex patterns with autocorrelation or seasonality
        
        Please analyze the data characteristics carefully and recommend a single model by name: "linear", "exponential", or "arima".
        
        Your entire response should be just one word: the name of the most appropriate model.
        </context>
        """
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            temperature=0.0,
            system="You are a time series forecasting expert. Always respond with only a single word model name from the allowed options: linear, exponential, or arima. No other text.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract model recommendation from Claude's response
        model_name = response.content[0].text.strip().lower()
        
        # Validate response
        if model_name in ["linear", "exponential", "arima"]:
            return model_name
        else:
            logger.warning(f"Unexpected model recommendation from Claude: {model_name}")
            return None
        
    except Exception as e:
        logger.error(f"Error getting AI model recommendation: {str(e)}")
        return None


def detect_anomalies_with_ai(years: List[int], rates: List[float], tax_code: str) -> List[Dict[str, Any]]:
    """
    Use AI to detect and explain anomalies in the historical tax rate data.
    
    Args:
        years: List of years
        rates: List of tax rates
        tax_code: The tax code being analyzed
        
    Returns:
        List of dictionaries containing anomaly information with AI-generated explanations
    """
    # First, detect statistical anomalies
    from utils.forecasting_utils import detect_anomalies
    statistical_anomalies = detect_anomalies(
        np.array(years), 
        np.array(rates), 
        method='zscore', 
        threshold=2.0
    )
    
    # If no anomalies or less than 3 data points, return statistical anomalies as is
    if len(years) < 3 or not statistical_anomalies:
        return statistical_anomalies
    
    # Check if Claude API is available
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_key:
        logger.warning("ANTHROPIC_API_KEY environment variable not set")
        return statistical_anomalies
    
    try:
        client = anthropic.Anthropic(api_key=anthropic_key)
        
        # Format time series data
        data_points = "\n".join([f"Year {year}: Rate {rate:.4f}" for year, rate in zip(years, rates)])
        
        # Format identified anomalies
        anomalies_text = "Detected statistical anomalies:\n"
        for anomaly in statistical_anomalies:
            anomalies_text += f"- Year {anomaly['year']}: Rate {anomaly['rate']:.4f} (Severity: {anomaly['severity']:.2f})\n"
        
        # Create prompt for Claude
        prompt = f"""
        <context>
        You are an expert property tax analyst examining tax levy rate anomalies for tax code {tax_code}.
        
        Historical tax levy rates:
        {data_points}
        
        {anomalies_text}
        
        For each of the anomalies detected by the statistical algorithm, provide:
        1. A concise explanation of why this data point might be anomalous
        2. Potential economic, policy, or administrative factors that could explain the anomaly
        3. An assessment of whether the anomaly represents a data error or a legitimate change
        
        Answer in this format for each anomaly:
        Year [year]: [1-2 sentence explanation], [severity classification: "low", "medium", or "high"]
        </context>
        """
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.3,
            system="You are a property tax analyst providing concise, expert explanations of anomalies in tax rate data. Focus on plausible economic and policy explanations.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract explanations from Claude's response
        text = response.content[0].text.strip()
        
        # Match explanations to anomalies using regex
        import re
        enhanced_anomalies = []
        
        for anomaly in statistical_anomalies:
            year = anomaly['year']
            
            # Try to find the explanation for this year
            pattern = rf"Year {year}:\s*(.*?)(?:,\s*|$)(low|medium|high)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            
            if match:
                explanation = match.group(1).strip()
                severity = match.group(2).lower()
                
                # Create enhanced anomaly
                enhanced_anomaly = anomaly.copy()
                enhanced_anomaly['explanation'] = explanation
                enhanced_anomaly['severity'] = severity
                enhanced_anomalies.append(enhanced_anomaly)
            else:
                # If no match, keep the original anomaly
                anomaly['explanation'] = "Statistical anomaly detected"
                anomaly['severity'] = "medium"  # Default severity
                enhanced_anomalies.append(anomaly)
        
        return enhanced_anomalies
        
    except Exception as e:
        logger.error(f"Error enhancing anomalies with AI: {str(e)}")
        
        # Return the original statistical anomalies with generic explanations
        for anomaly in statistical_anomalies:
            anomaly['explanation'] = "Statistical anomaly detected"
            anomaly['severity'] = "medium"  # Default severity
            
        return statistical_anomalies


def generate_forecast_recommendations(tax_code: str,
                                   historical_rates: List[float],
                                   forecast_rates: List[float],
                                   current_year: int,
                                   forecast_years: List[int]) -> List[str]:
    """
    Generate AI-enhanced recommendations based on the forecast.
    
    Args:
        tax_code: The tax code being forecasted
        historical_rates: List of historical rates
        forecast_rates: List of forecasted rates
        current_year: The current year
        forecast_years: List of years in the forecast
        
    Returns:
        List of recommendation strings
    """
    # Check if Claude API is available
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_key:
        logger.warning("ANTHROPIC_API_KEY environment variable not set")
        return ["AI-enhanced recommendations not available (API key not configured)."]
    
    client = anthropic.Anthropic(api_key=anthropic_key)
    
    # Calculate year-over-year changes
    historical_changes = []
    for i in range(1, len(historical_rates)):
        pct_change = ((historical_rates[i] - historical_rates[i-1]) / historical_rates[i-1]) * 100
        historical_changes.append(pct_change)
    
    forecast_changes = []
    for i in range(1, len(forecast_rates)):
        pct_change = ((forecast_rates[i] - forecast_rates[i-1]) / forecast_rates[i-1]) * 100
        forecast_changes.append(pct_change)
    
    # Calculate avg change in historical vs forecasted
    avg_historical_change = sum(historical_changes) / len(historical_changes) if historical_changes else 0
    avg_forecast_change = sum(forecast_changes) / len(forecast_changes) if forecast_changes else 0
    
    # Format data for Claude
    historical_data = "\n".join([f"Previous year {current_year - len(historical_rates) + i + 1}: Rate {rate:.4f}" 
                              for i, rate in enumerate(historical_rates)])
    
    forecast_data = "\n".join([f"Future year {year}: Rate {rate:.4f} (Change: {change:.2f}%)" 
                            for year, rate, change in zip(forecast_years[1:], forecast_rates[1:], forecast_changes)])
    
    # Create prompt for Claude
    prompt = f"""
    <context>
    You are an expert property tax consultant analyzing tax levy rate forecasts for tax code {tax_code}.
    
    Current year: {current_year}
    Current rate: {historical_rates[-1]:.4f}
    
    Historical rates:
    {historical_data}
    Average historical change: {avg_historical_change:.2f}%
    
    Forecast rates:
    Future year {forecast_years[0]}: Rate {forecast_rates[0]:.4f}
    {forecast_data}
    Average forecast change: {avg_forecast_change:.2f}%
    
    Based on this information, provide 3-5 specific, actionable recommendations for managing this tax code's levy rates.
    Focus on strategic financial planning, compliance with statutory limits, and balancing revenue needs with taxpayer impact.
    
    Format your response as a numbered list of recommendations, with each recommendation being 1-2 sentences.
    </context>
    """
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # The newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            max_tokens=800,
            temperature=0.3,
            system="You are a property tax consultant providing actionable recommendations for county tax administrators. Be specific, clear, and practical. Focus on implementation over theory.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract recommendations from Claude's response
        text = response.content[0].text.strip()
        
        # Split into recommendations - assuming they're numbered
        import re
        recommendations = []
        
        if text:
            # Try to match numbered items with regex
            matches = re.findall(r'\d+\.\s+(.*?)(?=\n\d+\.|\Z)', text, re.DOTALL)
            
            if matches:
                recommendations = [match.strip() for match in matches]
            else:
                # If regex fails, just split by newlines and clean up
                recommendations = [line.strip() for line in text.split('\n') 
                                 if line.strip() and not line.strip().isdigit()]
        
        return recommendations
    
    except Exception as e:
        logger.error(f"Error generating forecast recommendations: {str(e)}")
        return [f"An error occurred while generating recommendations: {str(e)}"]