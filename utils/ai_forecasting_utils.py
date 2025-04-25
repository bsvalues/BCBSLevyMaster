"""
AI-enhanced forecasting utilities for the Levy Calculation Application.

This module provides functions that use multi-provider LLM integration to generate explanations
and recommendations for forecast results, as well as AI-enhanced model selection
and anomaly detection.
"""

import os
import numpy as np
import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import importlib
from utils.mcp_llm import create_llm_service
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

from models import SystemSetting

def get_active_ai_provider():
    setting = SystemSetting.query.filter_by(key="ai_provider").first()
    return setting.value if setting else os.environ.get("AI_PROVIDER", "openai")

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
    Generate an AI-enhanced explanation of the forecast using any available LLM provider.
    """
    try:
        llm = create_llm_service(provider_name=get_active_ai_provider())
        prompt = f"""
        Tax Code: {tax_code}
        Historical Years: {historical_years}
        Historical Rates: {historical_rates}
        Forecast Years: {forecast_years}
        Forecast Rates: {forecast_rates}
        Best Model: {best_model}
        Anomalies: {anomalies}

        Please provide a concise, plain-English explanation of the forecast, highlighting trends, confidence, and any anomalies detected. Include actionable insights if appropriate.
        """
        explanation = llm.generate_text(prompt)
        return explanation
    except Exception as e:
        logger.error(f"Error generating forecast explanation: {str(e)}")
        return f"AI-enhanced explanation not available: {str(e)}"


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
    
    # Use LLM to analyze data characteristics if available
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
    Use the best available LLM provider to recommend the best forecasting model.
    """
    try:
        llm = create_llm_service(provider_name=get_active_ai_provider())
        prompt = f"""
        Given the following time series characteristics and data, recommend the best forecasting model (linear, exponential, ARIMA, or AI-enhanced):
        Characteristics: {characteristics}
        Data: {data}
        Respond only with the model name.
        """
        response = llm.generate_text(prompt)
        model_name = response.strip().lower()
        if model_name in ["linear", "exponential", "arima", "ai-enhanced"]:
            return model_name
        else:
            logger.warning(f"Unexpected model recommendation from LLM: {model_name}")
            return None
    except Exception as e:
        logger.error(f"Error getting model recommendation from LLM: {str(e)}")
        return None


def detect_anomalies_with_ai(years: List[int], rates: List[float], tax_code: str) -> List[Dict[str, Any]]:
    """
    Use any available LLM provider to detect and explain anomalies in the historical tax rate data.
    """
    from utils.forecasting_utils import detect_anomalies
    statistical_anomalies = detect_anomalies(
        np.array(years), np.array(rates)
    )
    try:
        llm = create_llm_service(provider_name=get_active_ai_provider())
        enhanced_anomalies = []
        for anomaly in statistical_anomalies:
            prompt = f"""
            Tax Code: {tax_code}
            Year: {anomaly['year']}
            Rate: {anomaly['rate']}
            Description: {anomaly['description']}
            Please explain why this data point may be an anomaly and rate its severity (low, medium, high).
            """
            explanation = llm.generate_text(prompt)
            anomaly['explanation'] = explanation
            anomaly['severity'] = "medium"  # Default, can be improved by parsing LLM output
            enhanced_anomalies.append(anomaly)
        return enhanced_anomalies
    except Exception as e:
        logger.error(f"Error enhancing anomalies with LLM: {str(e)}")
        # Return the original statistical anomalies with generic explanations
        for anomaly in statistical_anomalies:
            anomaly['explanation'] = "Statistical anomaly detected"
            anomaly['severity'] = "medium"
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
    try:
        llm = create_llm_service(provider_name=get_active_ai_provider())
        prompt = f"""
        Tax Code: {tax_code}
        Historical Rates: {historical_rates}
        Forecast Rates: {forecast_rates}
        Current Year: {current_year}
        Forecast Years: {forecast_years}
        Please provide 3-5 actionable recommendations for managing this tax code's levy rates, focusing on strategic financial planning, compliance with statutory limits, and balancing revenue needs with taxpayer impact.
        """
        recommendations = llm.generate_text(prompt)
        return recommendations.split('\n')
    except Exception as e:
        logger.error(f"Error generating forecast recommendations: {str(e)}")
        return [f"An error occurred while generating recommendations: {str(e)}"]