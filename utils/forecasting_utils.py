"""
Forecasting utilities for the Levy Calculation System.

This module provides various forecasting models and utilities for predicting
future levy rates, tax amounts, and assessed values.
"""
import logging
from typing import Dict, List, Tuple, Any, Optional, Union, Type

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA

from app2 import db
from models import TaxCode, TaxCodeHistoricalRate

# Set up logging
logger = logging.getLogger(__name__)

# Available forecasting models
FORECAST_MODELS = ['linear', 'exponential', 'arima']

class InsufficientDataError(Exception):
    """Exception raised when there is insufficient data for forecasting."""
    pass

class ForecastModel:
    """Base class for forecasting models."""
    
    def __init__(self, years: List[int], values: List[float]):
        """
        Initialize the forecast model.
        
        Args:
            years: List of years for historical data
            values: List of values (rates, amounts, etc.) for historical data
        """
        if len(years) < 3:
            raise InsufficientDataError("At least 3 years of historical data is required")
        
        self.years = years
        self.values = values
        self.model = None
    
    def train(self) -> None:
        """Train the model on the historical data."""
        raise NotImplementedError("Subclasses must implement train()")
    
    def predict(self, future_years: List[int], confidence_level: float = 0.95) -> Tuple[List[float], List[float], List[float]]:
        """
        Generate predictions for future years.
        
        Args:
            future_years: List of years to forecast
            confidence_level: Confidence level for prediction intervals (0-1)
            
        Returns:
            Tuple of (predictions, lower_bound, upper_bound)
        """
        raise NotImplementedError("Subclasses must implement predict()")

class LinearTrendModel(ForecastModel):
    """Linear regression-based forecasting model."""
    
    def train(self) -> None:
        """Train a linear regression model on the historical data."""
        X = np.array(self.years).reshape(-1, 1)
        y = np.array(self.values)
        
        self.model = LinearRegression()
        self.model.fit(X, y)
        
        # Calculate residuals for prediction intervals
        self.predictions = self.model.predict(X)
        self.residuals = y - self.predictions
        self.residual_std = np.std(self.residuals)
    
    def predict(self, future_years: List[int], confidence_level: float = 0.95) -> Tuple[List[float], List[float], List[float]]:
        """
        Generate linear trend predictions for future years.
        
        Args:
            future_years: List of years to forecast
            confidence_level: Confidence level for prediction intervals (0-1)
            
        Returns:
            Tuple of (predictions, lower_bound, upper_bound)
        """
        if self.model is None:
            self.train()
            
        X_future = np.array(future_years).reshape(-1, 1)
        predictions = self.model.predict(X_future)
        
        # Calculate prediction intervals
        z_score = abs(np.percentile(np.random.standard_normal(10000), (1 - confidence_level) / 2 * 100))
        interval = z_score * self.residual_std
        
        lower_bound = predictions - interval
        upper_bound = predictions + interval
        
        return predictions.tolist(), lower_bound.tolist(), upper_bound.tolist()

class ExponentialSmoothingModel(ForecastModel):
    """Exponential smoothing-based forecasting model."""
    
    def train(self) -> None:
        """Train an exponential smoothing model on the historical data."""
        # Need at least 4 observations for seasonal (annual) patterns
        seasonal_periods = 1  # Default to non-seasonal
        if len(self.years) >= 4:
            seasonal_periods = 1  # Annual seasonality if enough data
            
        # Ensure consecutive years
        df = pd.DataFrame({'year': self.years, 'value': self.values})
        df = df.sort_values('year')
        
        # Fill any missing years with interpolated values
        year_range = range(min(self.years), max(self.years) + 1)
        if len(year_range) > len(self.years):
            full_df = pd.DataFrame({'year': list(year_range)})
            df = pd.merge(full_df, df, on='year', how='left')
            df['value'] = df['value'].interpolate(method='linear')
        
        # Create time series
        self.ts = pd.Series(df['value'].values, index=df['year'])
        
        # Fit model - use additive for tax rates which can be close to zero
        self.model = ExponentialSmoothing(
            self.ts,
            trend='add',
            seasonal=None,
            seasonal_periods=seasonal_periods
        ).fit()
        
        # Calculate residuals for prediction intervals
        self.residuals = self.ts - self.model.fittedvalues
        self.residual_std = np.std(self.residuals)
    
    def predict(self, future_years: List[int], confidence_level: float = 0.95) -> Tuple[List[float], List[float], List[float]]:
        """
        Generate exponential smoothing predictions for future years.
        
        Args:
            future_years: List of years to forecast
            confidence_level: Confidence level for prediction intervals (0-1)
            
        Returns:
            Tuple of (predictions, lower_bound, upper_bound)
        """
        if self.model is None:
            self.train()
            
        # Get predictions
        steps = len(future_years)
        forecast = self.model.forecast(steps)
        
        # Match forecast index to future_years
        if len(forecast) == steps:
            predictions = forecast.values
        else:
            # If index doesn't match, interpolate to match future_years
            forecast_years = forecast.index.tolist()
            forecast_values = forecast.values
            
            # Create a mapping of years to values
            year_to_value = dict(zip(forecast_years, forecast_values))
            
            # Extract values for requested future years
            predictions = np.array([
                year_to_value.get(year, np.nan) 
                for year in future_years
            ])
            
            # Interpolate any missing values
            nan_mask = np.isnan(predictions)
            if np.any(nan_mask):
                x = np.where(~nan_mask)[0]
                y = predictions[~nan_mask]
                
                # Interpolate missing values
                if len(x) > 0:
                    predictions[nan_mask] = np.interp(
                        np.where(nan_mask)[0], 
                        x, 
                        y
                    )
        
        # Calculate prediction intervals using residual standard deviation
        z_score = abs(np.percentile(np.random.standard_normal(10000), (1 - confidence_level) / 2 * 100))
        interval = z_score * self.residual_std * np.sqrt(np.arange(1, steps + 1))
        
        lower_bound = predictions - interval
        upper_bound = predictions + interval
        
        return predictions.tolist(), lower_bound.tolist(), upper_bound.tolist()

class ARIMAModel(ForecastModel):
    """ARIMA-based forecasting model."""
    
    def train(self) -> None:
        """Train an ARIMA model on the historical data."""
        # Ensure data is in chronological order
        data = pd.DataFrame({'year': self.years, 'value': self.values})
        data = data.sort_values('year')
        
        # Fill missing years with interpolated values
        year_range = range(min(self.years), max(self.years) + 1)
        if len(year_range) > len(self.years):
            full_df = pd.DataFrame({'year': list(year_range)})
            data = pd.merge(full_df, data, on='year', how='left')
            data['value'] = data['value'].interpolate(method='linear')
        
        self.ts = pd.Series(data['value'].values, index=data['year'])
        
        # Start with simple model for limited data
        p, d, q = 1, 1, 0
        if len(self.years) >= 5:
            # More complex model if we have enough data
            p, d, q = 1, 1, 1
        
        try:
            self.model = ARIMA(self.ts, order=(p, d, q))
            self.result = self.model.fit()
            
            # Calculate residuals for prediction intervals
            self.residuals = self.result.resid
            self.residual_std = np.std(self.residuals)
        except Exception as e:
            logger.warning(f"ARIMA model fitting failed: {str(e)}")
            # Fall back to a simpler model
            try:
                self.model = ARIMA(self.ts, order=(1, 0, 0))
                self.result = self.model.fit()
                
                # Calculate residuals
                self.residuals = self.result.resid
                self.residual_std = np.std(self.residuals)
            except Exception as e2:
                raise ValueError(f"ARIMA model failed: {str(e2)}")
    
    def predict(self, future_years: List[int], confidence_level: float = 0.95) -> Tuple[List[float], List[float], List[float]]:
        """
        Generate ARIMA predictions for future years.
        
        Args:
            future_years: List of years to forecast
            confidence_level: Confidence level for prediction intervals (0-1)
            
        Returns:
            Tuple of (predictions, lower_bound, upper_bound)
        """
        if not hasattr(self, 'result'):
            self.train()
            
        # Determine steps based on the difference between last historical year and future years
        steps = len(future_years)
        forecast_result = self.result.forecast(steps=steps)
        
        # Extract point forecasts
        if isinstance(forecast_result, pd.Series):
            predictions = forecast_result.values
        else:
            predictions = forecast_result
            
        # If the forecast is longer than requested, truncate it
        if len(predictions) > len(future_years):
            predictions = predictions[:len(future_years)]
        
        # If the forecast is shorter, extend it using the trend
        if len(predictions) < len(future_years):
            # Calculate the average trend from the existing predictions
            if len(predictions) > 1:
                avg_trend = (predictions[-1] - predictions[0]) / (len(predictions) - 1)
            else:
                # If only one prediction, use the historical trend
                if len(self.values) > 1:
                    avg_trend = (self.values[-1] - self.values[0]) / (len(self.values) - 1)
                else:
                    avg_trend = 0
            
            # Extend with the trend
            last_pred = predictions[-1]
            for i in range(len(predictions), len(future_years)):
                last_pred += avg_trend
                predictions = np.append(predictions, last_pred)
        
        # Calculate prediction intervals
        z_score = abs(np.percentile(np.random.standard_normal(10000), (1 - confidence_level) / 2 * 100))
        interval = z_score * self.residual_std * np.sqrt(np.arange(1, steps + 1))
        
        lower_bound = predictions - interval
        upper_bound = predictions + interval
        
        return predictions.tolist(), lower_bound.tolist(), upper_bound.tolist()

def create_forecast_model(model_name: str, years: List[int], values: List[float]) -> ForecastModel:
    """
    Create and train a forecast model based on the specified type.
    
    Args:
        model_name: Type of forecasting model ('linear', 'exponential', 'arima')
        years: List of years for historical data
        values: List of values for historical data
        
    Returns:
        Trained forecasting model
    """
    model_classes = {
        'linear': LinearTrendModel,
        'exponential': ExponentialSmoothingModel,
        'arima': ARIMAModel
    }
    
    if model_name not in model_classes:
        raise ValueError(f"Unknown forecast model: {model_name}")
    
    model = model_classes[model_name](years, values)
    model.train()
    
    return model

def generate_forecast(
    model: ForecastModel, 
    future_years: List[int], 
    confidence_level: float = 0.95
) -> Tuple[List[float], List[float], List[float]]:
    """
    Generate forecasts using the provided model.
    
    Args:
        model: Trained forecasting model
        future_years: List of years to forecast
        confidence_level: Confidence level for prediction intervals
        
    Returns:
        Tuple of (predictions, lower_bound, upper_bound)
    """
    return model.predict(future_years, confidence_level)

def calculate_accuracy_metrics(
    model: ForecastModel, 
    years: List[int], 
    actual_values: List[float]
) -> Tuple[float, float, float]:
    """
    Calculate accuracy metrics for the forecast model.
    
    Args:
        model: Trained forecasting model
        years: Years of historical data
        actual_values: Actual values for comparison
        
    Returns:
        Tuple of (rmse, mae, mape)
    """
    # Use cross-validation approach if we have enough data
    if len(years) >= 5:
        # Hold out the last 2 years for validation
        train_years = years[:-2]
        train_values = actual_values[:-2]
        test_years = years[-2:]
        test_values = actual_values[-2:]
        
        # Retrain the model on the training subset
        model_class = model.__class__
        cv_model = model_class(train_years, train_values)
        cv_model.train()
        
        # Generate predictions for test years
        predictions, _, _ = cv_model.predict(test_years)
        
    else:
        # For limited data, use in-sample accuracy
        # Retrain to ensure we have predictions for all years
        model_class = model.__class__
        cv_model = model_class(years, actual_values)
        cv_model.train()
        
        # Generate in-sample predictions
        predictions, _, _ = cv_model.predict(years)
        test_values = actual_values
    
    # Calculate error metrics
    errors = np.array(test_values) - np.array(predictions)
    rmse = np.sqrt(mean_squared_error(test_values, predictions))
    mae = mean_absolute_error(test_values, predictions)
    
    # Calculate MAPE, avoiding division by zero
    non_zero_mask = np.array(test_values) != 0
    if np.any(non_zero_mask):
        mape = np.mean(np.abs(errors[non_zero_mask] / np.array(test_values)[non_zero_mask])) * 100
    else:
        mape = float('inf')
    
    return rmse, mae, mape

def detect_anomalies(
    years: List[int], 
    values: List[float], 
    z_threshold: float = 2.0
) -> List[Tuple[int, float, str, float]]:
    """
    Detect anomalies in historical data using z-scores.
    
    Args:
        years: Years of historical data
        values: Values to analyze for anomalies
        z_threshold: Z-score threshold for anomaly detection
        
    Returns:
        List of tuples (year, value, anomaly_type, z_score)
    """
    from scipy.stats import zscore
    
    # Need at least 3 data points for meaningful z-scores
    if len(values) < 3:
        return []
    
    # Calculate z-scores
    z_scores = zscore(values)
    
    # Identify anomalies
    anomalies = []
    for i, (year, value, z) in enumerate(zip(years, values, z_scores)):
        if abs(z) > z_threshold:
            anomaly_type = 'high' if z > 0 else 'low'
            anomalies.append((year, value, anomaly_type, float(z)))
    
    return anomalies

def create_forecast_chart_data(
    years: List[int],
    values: List[float],
    future_years: List[int],
    forecasts: Dict[str, Dict[str, List[float]]]
) -> Dict[str, List[float]]:
    """
    Create data structure for forecast visualization charts.
    
    Args:
        years: Historical years
        values: Historical values
        future_years: Years being forecasted
        forecasts: Dictionary of forecast results by model
        
    Returns:
        Dictionary with chart data formatted for JavaScript charts
    """
    # Combine years for x-axis
    all_years = years + future_years
    
    # Prepare historical data (with nulls for future years)
    historical_values = values + [None] * len(future_years)
    
    # Initialize result with historical data
    result = {
        'years': all_years,
        'historical': historical_values
    }
    
    # Add forecast data for each model (with nulls for historical years)
    for model_name, forecast_data in forecasts.items():
        # Create arrays with nulls for historical period
        forecast_values = [None] * len(years) + forecast_data['forecast']
        lower_values = [None] * len(years) + forecast_data['lower_bound']
        upper_values = [None] * len(years) + forecast_data['upper_bound']
        
        # Add to result
        result[f'{model_name}_forecast'] = forecast_values
        result[f'{model_name}_lower'] = lower_values
        result[f'{model_name}_upper'] = upper_values
    
    return result

def create_scenario_comparison_chart(
    years: List[int],
    baseline_values: List[float],
    scenarios: Dict[str, List[float]]
) -> Dict[str, List[float]]:
    """
    Create data structure for comparing different forecast scenarios.
    
    Args:
        years: Years for the chart (historical + forecast)
        baseline_values: Baseline values (historical + forecast)
        scenarios: Dictionary of scenario names to values
        
    Returns:
        Dictionary with chart data formatted for JavaScript charts
    """
    result = {
        'years': years,
        'baseline': baseline_values
    }
    
    # Add each scenario
    for name, values in scenarios.items():
        result[name] = values
    
    return result

def generate_forecast_for_tax_code(
    tax_code_id: int,
    years_to_forecast: int = 3,
    confidence_level: float = 0.95,
    preferred_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete forecast for a specific tax code.
    
    Args:
        tax_code_id: ID of the tax code to forecast
        years_to_forecast: Number of years to forecast
        confidence_level: Confidence level for prediction intervals
        preferred_model: Optional preferred model to use
        
    Returns:
        Dictionary with forecast results
    """
    # Get tax code details
    tax_code = TaxCode.query.get(tax_code_id)
    if not tax_code:
        raise ValueError(f"Tax code with ID {tax_code_id} not found")
    
    # Get historical data
    historical_rates = TaxCodeHistoricalRate.query.filter_by(
        tax_code_id=tax_code_id
    ).order_by(
        TaxCodeHistoricalRate.year
    ).all()
    
    if len(historical_rates) < 3:
        raise InsufficientDataError(f"Insufficient historical data for tax code {tax_code.code}")
    
    # Extract data
    years = [rate.year for rate in historical_rates]
    rates = [rate.levy_rate for rate in historical_rates]
    
    # Generate forecasts with each model
    future_years = list(range(max(years) + 1, max(years) + years_to_forecast + 1))
    forecasts = {}
    errors = {}
    
    for model_name in FORECAST_MODELS:
        if preferred_model and model_name != preferred_model:
            continue
            
        try:
            # Create and train model
            model = create_forecast_model(model_name, years, rates)
            
            # Generate forecast
            forecast, lower, upper = generate_forecast(model, future_years, confidence_level)
            
            # Calculate accuracy metrics
            rmse, mae, mape = calculate_accuracy_metrics(model, years, rates)
            
            # Store results
            forecasts[model_name] = {
                'forecast': forecast,
                'lower_bound': lower,
                'upper_bound': upper
            }
            
            errors[model_name] = {
                'rmse': rmse,
                'mae': mae,
                'mape': mape
            }
            
        except Exception as e:
            logger.warning(f"Error with {model_name} model: {str(e)}")
            # Continue with other models
    
    if not forecasts:
        if preferred_model:
            raise ValueError(f"Preferred model {preferred_model} failed to generate forecast")
        else:
            raise ValueError("All forecast models failed")
    
    # Select best model based on RMSE
    if preferred_model and preferred_model in errors:
        best_model = preferred_model
    else:
        best_model = min(errors, key=lambda x: errors[x]['rmse'])
    
    # Detect anomalies
    anomalies = detect_anomalies(years, rates)
    
    # Prepare result
    result = {
        'tax_code_id': tax_code_id,
        'tax_code': tax_code.code,
        'historical_years': years,
        'historical_rates': rates,
        'forecast_years': future_years,
        'forecasts': forecasts,
        'errors': errors,
        'best_model': best_model,
        'anomalies': anomalies
    }
    
    return result

def generate_district_forecast(
    district_id: int,
    years_to_forecast: int = 3
) -> Dict[str, Any]:
    """
    Generate forecasts for all tax codes in a district.
    
    Args:
        district_id: ID of the tax district to forecast
        years_to_forecast: Number of years to forecast
        
    Returns:
        Dictionary with forecast results for all tax codes in the district
    """
    from sqlalchemy import func
    
    # Get all tax codes for the district
    tax_codes = db.session.query(TaxCode).join(
        TaxDistrict, TaxCode.id == TaxDistrict.tax_code_id
    ).filter(
        TaxDistrict.id == district_id
    ).all()
    
    if not tax_codes:
        raise ValueError(f"No tax codes found for district ID {district_id}")
    
    # Generate forecasts for each tax code
    forecasts = {}
    for tax_code in tax_codes:
        try:
            forecast = generate_forecast_for_tax_code(
                tax_code.id,
                years_to_forecast=years_to_forecast
            )
            forecasts[tax_code.code] = forecast
        except Exception as e:
            logger.warning(f"Error forecasting tax code {tax_code.code}: {str(e)}")
            # Continue with other tax codes
    
    # Get district details
    district = TaxDistrict.query.get(district_id)
    
    # Prepare aggregate result
    result = {
        'district_id': district_id,
        'district_name': district.name if district else f"District {district_id}",
        'forecasts': forecasts,
        'tax_codes': list(forecasts.keys())
    }
    
    return result