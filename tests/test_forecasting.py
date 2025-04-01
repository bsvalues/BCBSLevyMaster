"""
Tests for the property tax forecasting system.

This module contains tests to verify the functionality of:
- Creating different forecasting models
- Generating forecasts from historical data
- Calculating accuracy metrics
- Visualizing forecast results
- Handling edge cases like insufficient data
"""

import unittest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import the forecasting module (to be created)
from utils import forecasting_utils


class TestForecasting(unittest.TestCase):
    """Test suite for property tax forecasting functionality."""
    
    def setUp(self):
        """Set up test data that can be used across test methods."""
        # Create sample historical data for testing
        self.sample_years = list(range(2020, 2025))
        self.sample_rates = [9.50, 9.75, 10.20, 10.35, 10.55]  # Sample levy rates
        self.sample_data = {
            'years': self.sample_years,
            'rates': self.sample_rates
        }
        
        # Sample tax code for testing
        self.test_tax_code = "12345"
        
    def test_forecast_model_creation(self):
        """Test that forecast models can be created with different parameters."""
        # Test linear trend model
        linear_model = forecasting_utils.create_forecast_model('linear', self.sample_data)
        self.assertIsNotNone(linear_model)
        self.assertEqual(linear_model.model_type, 'linear')
        
        # Test exponential smoothing model
        exp_model = forecasting_utils.create_forecast_model('exponential', self.sample_data)
        self.assertIsNotNone(exp_model)
        self.assertEqual(exp_model.model_type, 'exponential')
        
        # Test ARIMA model
        arima_model = forecasting_utils.create_forecast_model('arima', self.sample_data)
        self.assertIsNotNone(arima_model)
        self.assertEqual(arima_model.model_type, 'arima')
    
    def test_forecast_with_historical_data(self):
        """Test forecasting with existing historical data."""
        # Create model
        model = forecasting_utils.create_forecast_model('linear', self.sample_data)
        
        # Generate forecast for next 3 years
        forecast = forecasting_utils.generate_forecast(model, years_ahead=3)
        
        # Verify forecast structure
        self.assertEqual(len(forecast['years']), 3)
        self.assertEqual(len(forecast['predicted_rates']), 3)
        self.assertEqual(len(forecast['confidence_intervals']), 3)
        
        # Verify forecast years
        self.assertEqual(forecast['years'][0], 2025)
        self.assertEqual(forecast['years'][-1], 2027)
        
        # Basic sanity check - predicted rates should be in a reasonable range
        for rate in forecast['predicted_rates']:
            self.assertGreater(rate, 8.0)  # Should be greater than historical minimum
            self.assertLess(rate, 12.0)    # Should be less than a reasonable upper bound
    
    def test_forecast_accuracy_metrics(self):
        """Test accuracy metrics for forecasting models."""
        # Create model
        model = forecasting_utils.create_forecast_model('linear', self.sample_data)
        
        # Calculate accuracy metrics
        metrics = forecasting_utils.calculate_accuracy_metrics(model)
        
        # Verify expected metrics are present
        self.assertIn('rmse', metrics)
        self.assertIn('mae', metrics)
        self.assertIn('r_squared', metrics)
        
        # Verify metrics are in expected ranges
        self.assertGreaterEqual(metrics['rmse'], 0.0)
        self.assertGreaterEqual(metrics['mae'], 0.0)
        self.assertLessEqual(metrics['r_squared'], 1.0)
        self.assertGreaterEqual(metrics['r_squared'], 0.0)
    
    def test_forecast_visualization(self):
        """Test visualization components for forecasts."""
        # Create model and forecast
        model = forecasting_utils.create_forecast_model('linear', self.sample_data)
        forecast = forecasting_utils.generate_forecast(model, years_ahead=3)
        
        # Test line chart generation
        chart_data = forecasting_utils.create_forecast_chart_data(
            self.sample_data, forecast, chart_type='line')
        
        # Verify chart data structure
        self.assertIn('historical', chart_data)
        self.assertIn('forecast', chart_data)
        self.assertIn('confidence', chart_data)
        
        # Test comparison chart with multiple scenarios
        optimistic_model = forecasting_utils.create_forecast_model(
            'linear', self.sample_data, scenario='optimistic')
        pessimistic_model = forecasting_utils.create_forecast_model(
            'linear', self.sample_data, scenario='pessimistic')
        
        optimistic_forecast = forecasting_utils.generate_forecast(optimistic_model, years_ahead=3)
        pessimistic_forecast = forecasting_utils.generate_forecast(pessimistic_model, years_ahead=3)
        
        comparison_data = forecasting_utils.create_scenario_comparison_chart(
            self.sample_data, 
            {
                'baseline': forecast,
                'optimistic': optimistic_forecast,
                'pessimistic': pessimistic_forecast
            }
        )
        
        # Verify comparison data structure
        self.assertIn('historical', comparison_data)
        self.assertIn('scenarios', comparison_data)
        self.assertEqual(len(comparison_data['scenarios']), 3)
    
    def test_forecast_with_insufficient_data(self):
        """Test handling of insufficient historical data for forecasting."""
        # Create insufficient data (only 2 years)
        insufficient_data = {
            'years': [2023, 2024],
            'rates': [10.35, 10.55]
        }
        
        # Verify appropriate error is raised
        with self.assertRaises(forecasting_utils.InsufficientDataError):
            forecasting_utils.create_forecast_model('linear', insufficient_data)
    
    def test_forecast_from_database(self):
        """Test generating forecasts from database historical data."""
        # Mock the database query results
        with patch('utils.forecasting_utils.get_historical_data_for_tax_code') as mock_get_data:
            # Configure the mock to return our sample data
            mock_get_data.return_value = self.sample_data
            
            # Generate forecast using the tax code
            forecast_result = forecasting_utils.generate_forecast_for_tax_code(
                self.test_tax_code, model_type='linear', years_ahead=3)
            
            # Verify the mock was called with correct parameters
            mock_get_data.assert_called_once_with(self.test_tax_code)
            
            # Verify forecast result
            self.assertIn('tax_code', forecast_result)
            self.assertIn('historical_data', forecast_result)
            self.assertIn('forecast', forecast_result)
            self.assertIn('metrics', forecast_result)
            
            self.assertEqual(forecast_result['tax_code'], self.test_tax_code)
    
    def test_aggregated_district_forecast(self):
        """Test forecasting for an entire district with multiple tax codes."""
        # Mock the district tax code results
        with patch('utils.forecasting_utils.get_tax_codes_for_district') as mock_get_codes:
            # Configure mock to return a list of tax codes
            mock_get_codes.return_value = ['12345', '12346', '12347']
            
            # Mock individual forecasts
            with patch('utils.forecasting_utils.generate_forecast_for_tax_code') as mock_forecast:
                # Configure mock to return a sample forecast for each call
                mock_forecast.side_effect = [
                    {
                        'tax_code': code,
                        'forecast': {'years': [2025, 2026, 2027], 'predicted_rates': [10.7, 10.9, 11.1]}
                    }
                    for code in ['12345', '12346', '12347']
                ]
                
                # Generate district forecast
                district_forecast = forecasting_utils.generate_district_forecast(
                    district_id=5, model_type='linear', years_ahead=3)
                
                # Verify calls and result
                mock_get_codes.assert_called_once_with(5)
                self.assertEqual(mock_forecast.call_count, 3)
                
                # Verify district forecast structure
                self.assertIn('district_id', district_forecast)
                self.assertIn('tax_codes', district_forecast)
                self.assertIn('aggregate_forecast', district_forecast)
                self.assertEqual(district_forecast['district_id'], 5)
                self.assertEqual(len(district_forecast['tax_codes']), 3)


if __name__ == '__main__':
    unittest.main()