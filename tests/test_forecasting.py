"""
Tests for the forecasting utilities module.

This file contains tests for the various forecasting models and algorithms
used in the levy calculation application.
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our application modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.forecasting_utils import (
    LinearRateForecast,
    ExponentialRateForecast,
    ARIMAForecast,
    AIEnhancedForecast,
    ForecastEvaluator,
    detect_anomalies,
    check_statutory_compliance
)

class TestForecastModels(unittest.TestCase):
    """Test cases for the various forecasting models."""
    
    def setUp(self):
        """Set up test data for forecasting models."""
        # Create sample historical data
        self.years = np.array([2017, 2018, 2019, 2020, 2021])
        
        # Sample data with linear growth pattern
        self.linear_data = np.array([1.2, 1.4, 1.6, 1.8, 2.0])
        
        # Sample data with exponential growth pattern
        self.exp_data = np.array([1.0, 1.1, 1.3, 1.7, 2.2])
        
        # Sample data with more complex pattern for ARIMA
        self.complex_data = np.array([1.5, 1.3, 1.7, 1.9, 1.8])
        
        # Create DataFrame with this data
        self.test_df = pd.DataFrame({
            'year': self.years,
            'linear_rate': self.linear_data,
            'exp_rate': self.exp_data,
            'complex_rate': self.complex_data
        })
        
        # Sample district info for AI forecasting
        self.district_info = {
            'name': 'Test District',
            'code': 'TEST01',
            'type': 'School',
            'established': 2015,
            'population': 50000,
            'assessed_value_history': [500000000, 550000000, 600000000, 650000000, 700000000]
        }
        
        # Define test statutory limits
        self.statutory_limits = {
            'School': 2.5,
            'County': 1.8,
            'City': 3.0,
            'Fire': 1.5
        }
    
    def test_linear_forecast_accuracy(self):
        """Test linear forecast model for accuracy."""
        # Create a forecast model using first 4 years of data
        model = LinearRateForecast(
            years=self.years[:-1],
            rates=self.linear_data[:-1]
        )
        
        # Predict the value for 2021
        prediction = model.predict(self.years[-1])
        
        # Check it's close to the actual value (within 5%)
        self.assertAlmostEqual(prediction, self.linear_data[-1], delta=0.1)
    
    def test_exponential_forecast_accuracy(self):
        """Test exponential forecast model for accuracy."""
        # Create a forecast model using first 4 years of data
        model = ExponentialRateForecast(
            years=self.years[:-1],
            rates=self.exp_data[:-1]
        )
        
        # Predict the value for 2021
        prediction = model.predict(self.years[-1])
        
        # Check it's close to the actual value (within 10%)
        self.assertAlmostEqual(prediction, self.exp_data[-1], delta=0.22)
    
    def test_arima_forecast_accuracy(self):
        """Test ARIMA model forecast accuracy."""
        # Create a forecast model using first 4 years of data
        model = ARIMAForecast(
            years=self.years[:-1],
            rates=self.complex_data[:-1]
        )
        
        # Predict the value for 2021
        prediction = model.predict(self.years[-1])
        
        # Check it's close to the actual value (within 15% as ARIMA is more complex)
        self.assertAlmostEqual(prediction, self.complex_data[-1], delta=0.27)
    
    def test_ai_enhanced_forecast(self):
        """Test AI-enhanced forecast model."""
        # Skip if ANTHROPIC_API_KEY is not available
        if 'ANTHROPIC_API_KEY' not in os.environ:
            self.skipTest("Skipping test_ai_enhanced_forecast: ANTHROPIC_API_KEY not available")
        
        # Create an AI-enhanced forecast model
        model = AIEnhancedForecast(
            years=self.years[:-1],
            rates=self.linear_data[:-1],
            district_info=self.district_info
        )
        
        # Predict for 2021
        prediction = model.predict(self.years[-1])
        
        # Should return a reasonable value (not just the trend but potentially adjusted)
        self.assertTrue(1.5 <= prediction <= 2.5,
                       f"AI prediction {prediction} not in reasonable range")
    
    def test_forecast_evaluator(self):
        """Test the forecast evaluator that compares different models."""
        # Create the evaluator with our test data
        evaluator = ForecastEvaluator(
            years=self.years[:-1],
            rates=self.linear_data[:-1],
            test_year=self.years[-1],
            actual_rate=self.linear_data[-1]
        )
        
        # Run the evaluation
        results = evaluator.compare_models()
        
        # Should have results for each model type
        self.assertIn('linear', results)
        self.assertIn('exponential', results)
        self.assertIn('arima', results)
        
        # Each result should have error metrics
        for model_name, model_results in results.items():
            self.assertIn('mae', model_results)
            self.assertIn('rmse', model_results)
            self.assertIn('predicted_value', model_results)
    
    def test_handles_insufficient_data(self):
        """Test that forecast models handle insufficient data gracefully."""
        # Try with just one year of data
        with self.assertRaises(ValueError):
            model = LinearRateForecast(
                years=np.array([2020]),
                rates=np.array([1.5])
            )


class TestAnomalyDetection(unittest.TestCase):
    """Test cases for anomaly detection in tax rate data."""
    
    def setUp(self):
        """Set up test data for anomaly detection."""
        # Regular pattern data
        self.regular_years = np.array([2017, 2018, 2019, 2020, 2021])
        self.regular_rates = np.array([1.5, 1.55, 1.6, 1.65, 1.7])
        
        # Data with an anomaly (spike in 2019)
        self.anomaly_years = np.array([2017, 2018, 2019, 2020, 2021])
        self.anomaly_rates = np.array([1.5, 1.55, 2.5, 1.65, 1.7])
        
        # Data with seasonal pattern (not anomalies)
        self.seasonal_years = np.array([2017, 2018, 2019, 2020, 2021])
        self.seasonal_rates = np.array([1.5, 1.7, 1.5, 1.7, 1.5])
    
    def test_identifies_rate_spike(self):
        """Test system can identify a significant rate spike."""
        anomalies = detect_anomalies(self.anomaly_years, self.anomaly_rates)
        
        # Should detect anomaly in 2019
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['year'], 2019)
        self.assertGreater(anomalies[0]['severity'], 0.5)  # Should have high severity
    
    def test_ignores_regular_pattern(self):
        """Test system doesn't flag regular growth patterns."""
        anomalies = detect_anomalies(self.regular_years, self.regular_rates)
        
        # Should not detect any anomalies
        self.assertEqual(len(anomalies), 0)
    
    def test_ignores_seasonal_patterns(self):
        """Test system doesn't flag normal seasonal variations."""
        anomalies = detect_anomalies(self.seasonal_years, self.seasonal_rates, 
                                    seasonal_pattern=True)
        
        # Should not detect any anomalies when seasonal_pattern is True
        self.assertEqual(len(anomalies), 0)


class TestComplianceChecking(unittest.TestCase):
    """Test cases for statutory compliance checking."""
    
    def setUp(self):
        """Set up test data for compliance checking."""
        # Define test statutory limits
        self.statutory_limits = {
            'School': 2.5,
            'County': 1.8,
            'City': 3.0,
            'Fire': 1.5
        }
        
        # Test district approaching limit
        self.approaching_limit = {
            'name': 'Test School District',
            'type': 'School',
            'current_rate': 2.3,
            'trend': 0.1  # Increasing 0.1 each year
        }
        
        # Test district well under limit
        self.under_limit = {
            'name': 'Test County',
            'type': 'County',
            'current_rate': 1.2,
            'trend': 0.05  # Increasing 0.05 each year
        }
        
        # Test district over limit
        self.over_limit = {
            'name': 'Test Fire District',
            'type': 'Fire',
            'current_rate': 1.6,
            'trend': 0.0  # Not changing
        }
    
    def test_detects_approaching_statutory_limit(self):
        """Test that the system warns when approaching statutory limits."""
        result = check_statutory_compliance(
            self.approaching_limit, 
            self.statutory_limits
        )
        
        # Should be flagged as approaching limit
        self.assertTrue(result['approaching_limit'])
        self.assertFalse(result['exceeds_limit'])
        self.assertLess(result['years_until_limit'], 3)  # Should hit limit in < 3 years
    
    def test_detects_exceeded_statutory_limit(self):
        """Test that the system flags rates exceeding statutory limits."""
        result = check_statutory_compliance(
            self.over_limit, 
            self.statutory_limits
        )
        
        # Should be flagged as exceeding limit
        self.assertTrue(result['exceeds_limit'])
        self.assertEqual(result['years_until_limit'], 0)
    
    def test_handles_under_limit_case(self):
        """Test system correctly handles rates well under limits."""
        result = check_statutory_compliance(
            self.under_limit, 
            self.statutory_limits
        )
        
        # Should not be flagged
        self.assertFalse(result['approaching_limit'])
        self.assertFalse(result['exceeds_limit'])
        self.assertGreater(result['years_until_limit'], 5)


if __name__ == '__main__':
    unittest.main()