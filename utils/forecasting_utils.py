"""
Forecasting utilities for property tax levy rates.

This module provides tools to analyze historical tax rate data and
generate forecasts for future years using various statistical models.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Union, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA

from models import TaxCode, TaxCodeHistoricalRate
from app import db

# Configure logging
logger = logging.getLogger(__name__)

# Custom exception for insufficient data
class InsufficientDataError(Exception):
    """Exception raised when there is not enough historical data for forecasting."""
    pass


@dataclass
class ForecastModel:
    """Base class for forecast models."""
    model_type: str
    data: Dict[str, Union[List[int], List[float]]]
    model: Any = None
    min_years_required: int = 3
    scenario: str = 'baseline'  # 'baseline', 'optimistic', or 'pessimistic'
    
    def __post_init__(self):
        """Initialize the model after instantiation."""
        # Verify we have sufficient data
        if len(self.data['years']) < self.min_years_required:
            raise InsufficientDataError(
                f"At least {self.min_years_required} years of historical data are required."
            )
        
        # Additional setup should be done in subclasses
        self._validate_data()
    
    def _validate_data(self):
        """Validate that the data meets requirements."""
        if 'years' not in self.data or 'rates' not in self.data:
            raise ValueError("Data must include 'years' and 'rates' keys")
        
        if len(self.data['years']) != len(self.data['rates']):
            raise ValueError("Years and rates must have the same length")


class LinearTrendModel(ForecastModel):
    """Linear regression forecast model."""
    
    def __post_init__(self):
        """Initialize the linear regression model."""
        super().__post_init__()
        
        # Prepare data
        X = np.array(self.data['years']).reshape(-1, 1)
        y = np.array(self.data['rates'])
        
        # Apply scenario adjustments if needed
        if self.scenario != 'baseline':
            y = self._adjust_for_scenario(y)
        
        # Create and fit the model
        self.model = LinearRegression()
        self.model.fit(X, y)
        
        # Store coefficients for later use
        self.slope = self.model.coef_[0]
        self.intercept = self.model.intercept_
    
    def _adjust_for_scenario(self, y):
        """Adjust rates based on scenario type."""
        if self.scenario == 'optimistic':
            # For optimistic scenario, slightly reduce growth rate
            return y * 0.95
        elif self.scenario == 'pessimistic':
            # For pessimistic scenario, slightly increase growth rate
            return y * 1.05
        return y
    
    def predict(self, years):
        """Make predictions for the given years."""
        X_pred = np.array(years).reshape(-1, 1)
        return self.model.predict(X_pred)
    
    def calculate_confidence_intervals(self, years, confidence=0.95):
        """Calculate confidence intervals for predictions."""
        # This is a simplified approach - in a real model, we would use
        # proper statistical methods to calculate the prediction intervals
        X = np.array(self.data['years']).reshape(-1, 1)
        y = np.array(self.data['rates'])
        
        # Calculate residuals
        y_pred = self.model.predict(X)
        residuals = y - y_pred
        
        # Use residual standard error for confidence intervals
        residual_std = np.std(residuals)
        
        # Z-score for the given confidence level (assuming normal distribution)
        if confidence == 0.95:
            z = 1.96
        elif confidence == 0.99:
            z = 2.58
        else:
            z = 1.645  # default to 90%
        
        # Make predictions for new years
        X_pred = np.array(years).reshape(-1, 1)
        predictions = self.model.predict(X_pred)
        
        # Calculate intervals
        intervals = []
        for pred in predictions:
            margin = z * residual_std
            intervals.append((pred - margin, pred + margin))
        
        return intervals


class ExponentialSmoothingModel(ForecastModel):
    """Exponential smoothing forecast model."""
    
    def __post_init__(self):
        """Initialize the exponential smoothing model."""
        super().__post_init__()
        
        # Minimum of 4 years needed for this model
        if len(self.data['years']) < 4:
            raise InsufficientDataError(
                "At least 4 years of historical data are required for exponential smoothing."
            )
        
        # Prepare data
        y = pd.Series(self.data['rates'], index=pd.DatetimeIndex(
            [f"{year}-01-01" for year in self.data['years']], freq='AS'))
        
        # Apply scenario adjustments if needed
        if self.scenario != 'baseline':
            y = self._adjust_for_scenario(y)
        
        # Create and fit the model (Holt's method - linear trend)
        self.model = ExponentialSmoothing(
            y, trend='add', seasonal=None, damped=False
        ).fit()
    
    def _adjust_for_scenario(self, y):
        """Adjust rates based on scenario type."""
        if self.scenario == 'optimistic':
            return y * 0.95
        elif self.scenario == 'pessimistic':
            return y * 1.05
        return y
    
    def predict(self, years):
        """Make predictions for the given years."""
        # Calculate number of steps to forecast
        last_year = self.data['years'][-1]
        steps = max(years) - last_year
        
        # Generate forecast
        forecast = self.model.forecast(steps=steps)
        
        # Extract the predictions for the requested years
        predictions = []
        forecast_years = list(range(last_year + 1, last_year + steps + 1))
        
        for year in years:
            if year in forecast_years:
                idx = forecast_years.index(year)
                predictions.append(forecast[idx])
            else:
                # If year is in historical data, use that value
                if year in self.data['years']:
                    idx = self.data['years'].index(year)
                    predictions.append(self.data['rates'][idx])
                else:
                    # This should not happen with our usage, but just in case
                    predictions.append(None)
        
        return predictions
    
    def calculate_confidence_intervals(self, years, confidence=0.95):
        """Calculate confidence intervals for predictions."""
        # Similar to the linear model, but adapting for exponential smoothing
        last_year = self.data['years'][-1]
        steps = max(years) - last_year
        
        # Get prediction intervals from statsmodels
        forecast = self.model.get_forecast(steps=steps)
        conf_int = forecast.conf_int(alpha=1-confidence)
        
        # Extract the intervals for the requested years
        intervals = []
        forecast_years = list(range(last_year + 1, last_year + steps + 1))
        
        for year in years:
            if year in forecast_years:
                idx = forecast_years.index(year)
                intervals.append((conf_int.iloc[idx, 0], conf_int.iloc[idx, 1]))
            else:
                # For historical years, use a narrower interval
                if year in self.data['years']:
                    idx = self.data['years'].index(year)
                    value = self.data['rates'][idx]
                    intervals.append((value * 0.98, value * 1.02))
                else:
                    intervals.append((None, None))
        
        return intervals


class ARIMAModel(ForecastModel):
    """ARIMA forecast model."""
    
    def __post_init__(self):
        """Initialize the ARIMA model."""
        super().__post_init__()
        
        # ARIMA typically needs more data
        if len(self.data['years']) < 5:
            raise InsufficientDataError(
                "At least 5 years of historical data are required for ARIMA."
            )
        
        # Prepare data
        y = np.array(self.data['rates'])
        
        # Apply scenario adjustments if needed
        if self.scenario != 'baseline':
            y = self._adjust_for_scenario(y)
        
        # Create and fit the model
        # Using (1,1,1) order as a reasonable default
        # In practice, order selection would be more sophisticated
        self.model = ARIMA(y, order=(1, 1, 1))
        self.model_fit = self.model.fit()
    
    def _adjust_for_scenario(self, y):
        """Adjust rates based on scenario type."""
        if self.scenario == 'optimistic':
            return y * 0.95
        elif self.scenario == 'pessimistic':
            return y * 1.05
        return y
    
    def predict(self, years):
        """Make predictions for the given years."""
        # Calculate number of steps to forecast
        last_year = self.data['years'][-1]
        steps = max(years) - last_year
        
        # Generate forecast
        forecast = self.model_fit.forecast(steps=steps)
        
        # Extract the predictions for the requested years
        predictions = []
        forecast_years = list(range(last_year + 1, last_year + steps + 1))
        
        for year in years:
            if year in forecast_years:
                idx = forecast_years.index(year)
                predictions.append(forecast[idx])
            else:
                # If year is in historical data, use that value
                if year in self.data['years']:
                    idx = self.data['years'].index(year)
                    predictions.append(self.data['rates'][idx])
                else:
                    # This should not happen with our usage, but just in case
                    predictions.append(None)
        
        return predictions
    
    def calculate_confidence_intervals(self, years, confidence=0.95):
        """Calculate confidence intervals for predictions."""
        # Calculate number of steps to forecast
        last_year = self.data['years'][-1]
        steps = max(years) - last_year
        
        # Generate forecast with confidence intervals
        forecast = self.model_fit.get_forecast(steps=steps)
        conf_int = forecast.conf_int(alpha=1-confidence)
        
        # Extract the intervals for the requested years
        intervals = []
        forecast_years = list(range(last_year + 1, last_year + steps + 1))
        
        for year in years:
            if year in forecast_years:
                idx = forecast_years.index(year)
                intervals.append((conf_int.iloc[idx, 0], conf_int.iloc[idx, 1]))
            else:
                # For historical years, use a narrower interval
                if year in self.data['years']:
                    idx = self.data['years'].index(year)
                    value = self.data['rates'][idx]
                    intervals.append((value * 0.98, value * 1.02))
                else:
                    intervals.append((None, None))
        
        return intervals


def create_forecast_model(
    model_type: str, 
    data: Dict[str, Union[List[int], List[float]]],
    scenario: str = 'baseline'
) -> ForecastModel:
    """
    Create a forecast model of the specified type.
    
    Args:
        model_type: Type of forecast model ('linear', 'exponential', 'arima')
        data: Dictionary containing historical years and rates
        scenario: Scenario type ('baseline', 'optimistic', 'pessimistic')
        
    Returns:
        A forecast model instance
    """
    if model_type == 'linear':
        return LinearTrendModel(model_type=model_type, data=data, scenario=scenario)
    elif model_type == 'exponential':
        return ExponentialSmoothingModel(model_type=model_type, data=data, scenario=scenario)
    elif model_type == 'arima':
        return ARIMAModel(model_type=model_type, data=data, scenario=scenario)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")


def generate_forecast(
    model: ForecastModel, 
    years_ahead: int = 3,
    confidence: float = 0.95
) -> Dict[str, Any]:
    """
    Generate a forecast for future years.
    
    Args:
        model: The forecast model to use
        years_ahead: Number of years to forecast
        confidence: Confidence level for intervals (0.95 = 95%)
        
    Returns:
        Dictionary containing forecast data
    """
    # Determine the years to forecast
    last_historical_year = max(model.data['years'])
    forecast_years = list(range(last_historical_year + 1, 
                               last_historical_year + years_ahead + 1))
    
    # Generate predictions
    predicted_rates = model.predict(forecast_years)
    
    # Calculate confidence intervals
    confidence_intervals = model.calculate_confidence_intervals(forecast_years, confidence)
    
    # Return the forecast data
    return {
        'years': forecast_years,
        'predicted_rates': predicted_rates,
        'confidence_intervals': confidence_intervals,
        'model_type': model.model_type,
        'scenario': model.scenario
    }


def calculate_accuracy_metrics(model: ForecastModel) -> Dict[str, float]:
    """
    Calculate accuracy metrics for a forecast model.
    
    Args:
        model: The forecast model to evaluate
        
    Returns:
        Dictionary of accuracy metrics
    """
    # Use the model to predict values for the historical years
    historical_years = model.data['years']
    historical_rates = model.data['rates']
    predicted_historical = model.predict(historical_years)
    
    # Calculate metrics
    rmse = np.sqrt(mean_squared_error(historical_rates, predicted_historical))
    mae = mean_absolute_error(historical_rates, predicted_historical)
    r_squared = r2_score(historical_rates, predicted_historical)
    
    # Calculate mean absolute percentage error (MAPE)
    mape = np.mean(np.abs((np.array(historical_rates) - np.array(predicted_historical)) / 
                         np.array(historical_rates))) * 100
    
    # Return the metrics
    return {
        'rmse': rmse,
        'mae': mae,
        'r_squared': r_squared,
        'mape': mape
    }


def create_forecast_chart_data(
    historical_data: Dict[str, List],
    forecast_data: Dict[str, Any],
    chart_type: str = 'line'
) -> Dict[str, Any]:
    """
    Create data formatted for visualization.
    
    Args:
        historical_data: Dictionary of historical years and rates
        forecast_data: Dictionary of forecast data
        chart_type: Type of chart to create ('line', 'bar')
        
    Returns:
        Dictionary of data formatted for visualization
    """
    # Format historical data
    historical = {
        'x': historical_data['years'],
        'y': historical_data['rates'],
        'type': chart_type,
        'name': 'Historical',
        'mode': 'lines+markers' if chart_type == 'line' else None,
        'marker': {'color': 'blue'}
    }
    
    # Format forecast data
    forecast = {
        'x': forecast_data['years'],
        'y': forecast_data['predicted_rates'],
        'type': chart_type,
        'name': 'Forecast',
        'mode': 'lines+markers' if chart_type == 'line' else None,
        'marker': {'color': 'red'},
        'line': {'dash': 'dot'} if chart_type == 'line' else None
    }
    
    # Format confidence intervals (only for line charts)
    confidence = None
    if chart_type == 'line':
        lower_bounds = [ci[0] for ci in forecast_data['confidence_intervals']]
        upper_bounds = [ci[1] for ci in forecast_data['confidence_intervals']]
        
        confidence = {
            'x': forecast_data['years'] + forecast_data['years'][::-1],
            'y': upper_bounds + lower_bounds[::-1],
            'fill': 'toself',
            'fillcolor': 'rgba(255, 0, 0, 0.2)',
            'line': {'color': 'transparent'},
            'name': '95% Confidence Interval',
            'showlegend': True
        }
    
    return {
        'historical': historical,
        'forecast': forecast,
        'confidence': confidence
    }


def create_scenario_comparison_chart(
    historical_data: Dict[str, List],
    scenario_forecasts: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create data for comparing different forecast scenarios.
    
    Args:
        historical_data: Dictionary of historical years and rates
        scenario_forecasts: Dictionary of forecast data for different scenarios
        
    Returns:
        Dictionary of data formatted for visualization
    """
    # Format historical data
    historical = {
        'x': historical_data['years'],
        'y': historical_data['rates'],
        'type': 'line',
        'name': 'Historical',
        'mode': 'lines+markers',
        'marker': {'color': 'blue'}
    }
    
    # Format scenario data
    scenarios = []
    colors = {'baseline': 'red', 'optimistic': 'green', 'pessimistic': 'orange'}
    
    for name, forecast in scenario_forecasts.items():
        scenario = {
            'x': forecast['years'],
            'y': forecast['predicted_rates'],
            'type': 'line',
            'name': name.capitalize(),
            'mode': 'lines+markers',
            'marker': {'color': colors.get(name, 'gray')},
            'line': {'dash': 'dot' if name != 'baseline' else 'solid'}
        }
        scenarios.append(scenario)
    
    return {
        'historical': historical,
        'scenarios': scenarios
    }


def get_historical_data_for_tax_code(tax_code: str) -> Dict[str, List]:
    """
    Retrieve historical data for a tax code from the database.
    
    Args:
        tax_code: The tax code to retrieve data for
        
    Returns:
        Dictionary containing historical years and rates
    """
    # Get the tax code object
    tax_code_obj = TaxCode.query.filter_by(code=tax_code).first()
    
    if not tax_code_obj:
        raise ValueError(f"Tax code {tax_code} not found")
    
    # Get historical rates for this tax code
    historical_rates = TaxCodeHistoricalRate.query.filter_by(
        tax_code_id=tax_code_obj.id
    ).order_by(TaxCodeHistoricalRate.year).all()
    
    # Format the data
    years = [rate.year for rate in historical_rates]
    rates = [rate.levy_rate for rate in historical_rates]
    
    # Include current year if not already in historical data
    current_year = datetime.now().year
    if current_year not in years and tax_code_obj.levy_rate:
        years.append(current_year)
        rates.append(tax_code_obj.levy_rate)
    
    return {
        'years': years,
        'rates': rates
    }


def generate_forecast_for_tax_code(
    tax_code: str,
    model_type: str = 'linear',
    years_ahead: int = 3,
    scenario: str = 'baseline'
) -> Dict[str, Any]:
    """
    Generate a forecast for a specific tax code.
    
    Args:
        tax_code: The tax code to forecast
        model_type: Type of forecast model to use
        years_ahead: Number of years to forecast
        scenario: Scenario type
        
    Returns:
        Dictionary with forecast results
    """
    # Get historical data
    historical_data = get_historical_data_for_tax_code(tax_code)
    
    # Create forecast model
    model = create_forecast_model(model_type, historical_data, scenario)
    
    # Generate forecast
    forecast = generate_forecast(model, years_ahead)
    
    # Calculate accuracy metrics
    metrics = calculate_accuracy_metrics(model)
    
    # Return the results
    return {
        'tax_code': tax_code,
        'historical_data': historical_data,
        'forecast': forecast,
        'metrics': metrics
    }


def get_tax_codes_for_district(district_id: int) -> List[str]:
    """
    Get all tax codes associated with a district.
    
    Args:
        district_id: The district ID
        
    Returns:
        List of tax codes in the district
    """
    # Query the database for tax codes in this district
    from models import TaxDistrict
    
    # Get current year
    current_year = datetime.now().year
    
    # Get all tax district relationships for this district and year
    districts = TaxDistrict.query.filter_by(
        tax_district_id=district_id,
        year=current_year
    ).all()
    
    # Extract all unique tax codes (from both levy_code and linked_levy_code)
    tax_codes = set()
    for district in districts:
        tax_codes.add(district.levy_code)
        tax_codes.add(district.linked_levy_code)
    
    return list(tax_codes)


def generate_district_forecast(
    district_id: int,
    model_type: str = 'linear',
    years_ahead: int = 3,
    scenario: str = 'baseline'
) -> Dict[str, Any]:
    """
    Generate a forecast for all tax codes in a district.
    
    Args:
        district_id: The district ID
        model_type: Type of forecast model to use
        years_ahead: Number of years to forecast
        scenario: Scenario type
        
    Returns:
        Dictionary with aggregated forecast results
    """
    # Get all tax codes for this district
    tax_codes = get_tax_codes_for_district(district_id)
    
    # Generate forecasts for each tax code
    forecasts = []
    for code in tax_codes:
        try:
            forecast = generate_forecast_for_tax_code(
                code, model_type, years_ahead, scenario)
            forecasts.append(forecast)
        except Exception as e:
            logger.warning(f"Error forecasting tax code {code}: {str(e)}")
            continue
    
    # Calculate aggregate forecast (average across all tax codes)
    if not forecasts:
        raise ValueError("No valid forecasts generated for this district")
    
    # Determine the years to include in aggregate
    forecast_years = forecasts[0]['forecast']['years']
    
    # Calculate average predicted rates for each year
    aggregate_rates = []
    for i, year in enumerate(forecast_years):
        rates = [f['forecast']['predicted_rates'][i] for f in forecasts 
                if i < len(f['forecast']['predicted_rates'])]
        aggregate_rates.append(sum(rates) / len(rates))
    
    # Return district forecast
    return {
        'district_id': district_id,
        'tax_codes': tax_codes,
        'individual_forecasts': forecasts,
        'aggregate_forecast': {
            'years': forecast_years,
            'predicted_rates': aggregate_rates,
            'model_type': model_type,
            'scenario': scenario
        }
    }


def save_forecast_to_database(forecast_data: Dict[str, Any]) -> int:
    """
    Save a forecast to the database for future reference.
    
    Args:
        forecast_data: The forecast data to save
        
    Returns:
        ID of the saved forecast
    """
    # This would implement database storage of forecast results
    # We'll leave this as a placeholder for now
    pass