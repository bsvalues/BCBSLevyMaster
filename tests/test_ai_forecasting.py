"""
Tests for AI-enhanced forecasting features.

This module contains tests to verify the functionality of:
- AI model selection for forecasting
- Forecast explanation generation
- Anomaly detection in historical data
- AI-generated recommendations based on forecast trends
"""

import pytest
import numpy as np
from datetime import datetime
from utils.ai_forecasting_utils import (
    ai_forecast_model_selector,
    generate_forecast_explanation,
    detect_anomalies,
    generate_forecast_recommendations
)
from utils.forecasting_utils import (
    ForecastModel,
    LinearTrendModel,
    ExponentialSmoothingModel,
    ARIMAModel
)


def generate_linear_test_data():
    """Generate data with a clear linear trend."""
    years = list(range(2015, 2025))
    # Linear trend with small random noise
    rates = [0.05 + 0.002 * (year - 2015) + np.random.normal(0, 0.0005) for year in years]
    return {'years': years, 'rates': rates}


def generate_seasonal_test_data():
    """Generate data with a seasonal pattern."""
    years = list(range(2015, 2025))
    # Base trend with cyclical pattern
    rates = []
    for i, year in enumerate(years):
        base = 0.05 + 0.001 * i
        seasonal = 0.002 * np.sin(i * np.pi / 2)  # 4-year cycle
        noise = np.random.normal(0, 0.0002)
        rates.append(base + seasonal + noise)
    return {'years': years, 'rates': rates}


def generate_sparse_test_data(points=4):
    """Generate sparse data with few data points."""
    years = list(range(2021, 2021 + points))
    rates = [0.05 + 0.001 * i + np.random.normal(0, 0.0002) for i in range(points)]
    return {'years': years, 'rates': rates}


def generate_data_with_anomalies():
    """Generate data with deliberate anomalies."""
    years = list(range(2015, 2025))
    rates = [0.05 + 0.001 * (year - 2015) + np.random.normal(0, 0.0002) for year in years]
    # Add an anomaly in 2022 (index 7)
    rates[7] = 0.07  # Significantly higher than the trend
    return {'years': years, 'rates': rates}


def generate_sample_forecast():
    """Generate a sample forecast result for testing."""
    data = generate_linear_test_data()
    future_years = list(range(2025, 2028))
    future_rates = [0.05 + 0.002 * (year - 2015) for year in future_years]
    confidence_intervals = [
        (rate - 0.001, rate + 0.001) for rate in future_rates
    ]
    
    return {
        'historical_data': data,
        'forecast': {
            'years': future_years,
            'predicted_rates': future_rates,
            'confidence_intervals': confidence_intervals,
            'model_type': 'linear',
            'scenario': 'baseline'
        },
        'metrics': {
            'rmse': 0.0003,
            'mae': 0.0002,
            'r_squared': 0.95,
            'mape': 0.3
        },
        'tax_code': 'TEST123'
    }


class TestAIModelSelection:
    """Tests for AI model selection for forecasting."""
    
    def test_model_selection_linear(self):
        """Test that AI selects linear model for linear data."""
        data = generate_linear_test_data()
        model = ai_forecast_model_selector(data)
        assert isinstance(model, LinearTrendModel)
        assert model.model_type == "linear"
    
    def test_model_selection_seasonal(self):
        """Test that AI selects appropriate model for seasonal data."""
        data = generate_seasonal_test_data()
        model = ai_forecast_model_selector(data)
        # Should select either exponential or ARIMA for seasonal data
        assert model.model_type in ["exponential", "arima"]
        assert isinstance(model, (ExponentialSmoothingModel, ARIMAModel))
    
    def test_model_selection_sparse(self):
        """Test that AI selects simpler model for sparse data."""
        data = generate_sparse_test_data(points=4)
        model = ai_forecast_model_selector(data)
        # Should select linear model for sparse data
        assert isinstance(model, LinearTrendModel)
        assert model.model_type == "linear"
    
    def test_model_handles_edge_cases(self):
        """Test that model selection handles edge cases."""
        # Test with minimum required data points
        min_data = generate_sparse_test_data(points=3)
        model = ai_forecast_model_selector(min_data)
        assert model is not None
        
        # Test with flat data (no trend)
        years = list(range(2015, 2025))
        flat_rates = [0.05 + np.random.normal(0, 0.0001) for _ in years]
        flat_data = {'years': years, 'rates': flat_rates}
        model = ai_forecast_model_selector(flat_data)
        assert model is not None


class TestForecastExplanation:
    """Tests for forecast explanation generation."""
    
    def test_explanation_content(self):
        """Test that explanations contain expected content."""
        forecast_data = generate_sample_forecast()
        explanation = generate_forecast_explanation(forecast_data)
        
        # Explanation should be non-empty
        assert explanation is not None
        assert len(explanation) > 100
        
        # Should mention key elements
        assert "trend" in explanation.lower()
        assert "forecast" in explanation.lower()
        assert "confidence" in explanation.lower()
        
        # Should include the tax code
        assert forecast_data['tax_code'] in explanation
        
        # Should include years
        for year in forecast_data['forecast']['years']:
            assert str(year) in explanation
    
    def test_explanation_based_on_metrics(self):
        """Test that explanation changes based on metrics."""
        forecast_data = generate_sample_forecast()
        good_explanation = generate_forecast_explanation(forecast_data)
        
        # Create a version with poor metrics
        poor_forecast = forecast_data.copy()
        poor_forecast['metrics'] = {
            'rmse': 0.03,
            'mae': 0.025,
            'r_squared': 0.4,
            'mape': 15.0
        }
        poor_explanation = generate_forecast_explanation(poor_forecast)
        
        # Explanations should differ
        assert good_explanation != poor_explanation
        
        # Poor explanation should indicate uncertainty
        assert "uncertain" in poor_explanation.lower() or "caution" in poor_explanation.lower() or "limited" in poor_explanation.lower()


class TestAnomalyDetection:
    """Tests for anomaly detection in historical data."""
    
    def test_normal_data_no_anomalies(self):
        """Test that normal data has no anomalies detected."""
        data = generate_linear_test_data()
        anomalies = detect_anomalies(data)
        assert len(anomalies) == 0
    
    def test_detect_obvious_anomalies(self):
        """Test that obvious anomalies are detected."""
        data = generate_data_with_anomalies()
        anomalies = detect_anomalies(data)
        
        # Should detect the anomaly
        assert len(anomalies) > 0
        
        # Identify the year with anomaly
        anomaly_years = [a['year'] for a in anomalies]
        assert 2022 in anomaly_years  # The year with the injected anomaly
    
    def test_anomaly_contains_explanation(self):
        """Test that detected anomalies include explanations."""
        data = generate_data_with_anomalies()
        anomalies = detect_anomalies(data)
        
        # Each anomaly should have an explanation
        for anomaly in anomalies:
            assert 'explanation' in anomaly
            assert len(anomaly['explanation']) > 0
            
            # Should have severity
            assert 'severity' in anomaly
            assert anomaly['severity'] in ['low', 'medium', 'high']


class TestForecastRecommendations:
    """Tests for AI-generated recommendations based on forecasts."""
    
    def test_recommendations_generation(self):
        """Test that recommendations are generated from forecasts."""
        forecast_data = generate_sample_forecast()
        recommendations = generate_forecast_recommendations(forecast_data)
        
        # Should have at least one recommendation
        assert len(recommendations) > 0
        
        # Each recommendation should have required fields
        for rec in recommendations:
            assert 'title' in rec
            assert 'description' in rec
            assert 'priority' in rec
            assert rec['priority'] in ['low', 'medium', 'high']
    
    def test_recommendations_differ_by_scenario(self):
        """Test that different scenarios produce different recommendations."""
        base_forecast = generate_sample_forecast()
        
        # Create pessimistic scenario
        pessimistic = base_forecast.copy()
        pessimistic['forecast'] = base_forecast['forecast'].copy()
        pessimistic['forecast']['scenario'] = 'pessimistic'
        pessimistic['forecast']['predicted_rates'] = [
            r * 1.05 for r in base_forecast['forecast']['predicted_rates']
        ]
        
        base_recs = generate_forecast_recommendations(base_forecast)
        pess_recs = generate_forecast_recommendations(pessimistic)
        
        # Recommendations should differ
        assert base_recs != pess_recs