"""
AI-enhanced forecasting utilities for the Levy Calculation System.

This module provides AI-powered forecasting capabilities by combining traditional
statistical models with AI-generated insights and explanations.
"""
import logging
import os
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import norm

from app2 import db
from models import TaxCode, TaxCodeHistoricalRate
from utils.anthropic_utils import ClaudeClient
from utils.forecasting_utils import (
    create_forecast_model, generate_forecast, 
    calculate_accuracy_metrics, detect_anomalies,
    FORECAST_MODELS
)

# Set up logging
logger = logging.getLogger(__name__)

class AIEnhancedForecast:
    """Class for AI-enhanced forecasting capabilities."""
    
    def __init__(self):
        """Initialize the AI forecasting service."""
        # Initialize the Claude client if API key is available
        self.claude_client = None
        if os.environ.get('ANTHROPIC_API_KEY'):
            self.claude_client = ClaudeClient()
    
    def forecast_levy_rates(
        self, 
        tax_code_id: Optional[int] = None,
        tax_code: Optional[str] = None,
        years_to_forecast: int = 3,
        confidence_level: float = 0.95,
        include_explanation: bool = True
    ) -> Dict[str, Any]:
        """
        Generate forecasts for levy rates with AI-enhanced explanations.
        
        Args:
            tax_code_id: ID of the tax code to forecast
            tax_code: Code of the tax code to forecast (alternative to tax_code_id)
            years_to_forecast: Number of years to forecast
            confidence_level: Confidence level for prediction intervals (0-1)
            include_explanation: Whether to include AI-generated explanations
            
        Returns:
            Dictionary containing forecast results and AI-enhanced explanations
        """
        # Validate parameters
        if not tax_code_id and not tax_code:
            raise ValueError("Either tax_code_id or tax_code must be provided")
        
        # Get tax code if only the ID was provided
        if tax_code_id and not tax_code:
            tax_code_obj = TaxCode.query.get(tax_code_id)
            if not tax_code_obj:
                raise ValueError(f"Tax code with ID {tax_code_id} not found")
            tax_code = tax_code_obj.code
        
        # Get historical data
        if tax_code_id:
            historical_data = self._get_historical_data_by_id(tax_code_id)
        else:
            historical_data = self._get_historical_data_by_code(tax_code)
        
        if len(historical_data) < 3:
            raise ValueError(f"Insufficient historical data for tax code {tax_code}. Need at least 3 years.")
        
        # Prepare data for forecasting
        years = [data.year for data in historical_data]
        rates = [data.levy_rate for data in historical_data]
        levy_amounts = [data.levy_amount for data in historical_data]
        assessed_values = [data.total_assessed_value for data in historical_data]
        
        # Generate forecasts with multiple models
        models_results = {}
        errors = {}
        
        for model_name in FORECAST_MODELS:
            try:
                # Create and train the model
                model = create_forecast_model(model_name, years, rates)
                
                # Generate forecast
                forecast_years = list(range(max(years) + 1, max(years) + years_to_forecast + 1))
                forecast_values, lower_bound, upper_bound = generate_forecast(
                    model, forecast_years, confidence_level
                )
                
                # Calculate accuracy metrics on historical data
                rmse, mae, mape = calculate_accuracy_metrics(model, years, rates)
                
                # Store results
                models_results[model_name] = {
                    'forecast': forecast_values,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound
                }
                
                errors[model_name] = {
                    'rmse': rmse,
                    'mae': mae,
                    'mape': mape
                }
                
            except Exception as e:
                logger.warning(f"Error generating forecast with {model_name} model: {str(e)}")
                # Continue with other models
        
        if not models_results:
            raise ValueError("All forecasting models failed")
        
        # Select the best model based on RMSE
        best_model = min(errors, key=lambda x: errors[x]['rmse'])
        
        # Detect anomalies in historical data
        anomalies = detect_anomalies(years, rates)
        
        # Convert historical data to list of dicts for JSON
        historical_data_json = [
            {
                'year': data.year,
                'levy_rate': data.levy_rate,
                'levy_amount': data.levy_amount,
                'total_assessed_value': data.total_assessed_value
            }
            for data in historical_data
        ]
        
        # Prepare the result
        result = {
            'tax_code_id': tax_code_id,
            'tax_code': tax_code,
            'historical_data': historical_data_json,
            'years_forecasted': list(range(max(years) + 1, max(years) + years_to_forecast + 1)),
            'models': list(models_results.keys()),
            'forecasts': models_results,
            'errors': errors,
            'best_model': best_model,
            'best_forecast': models_results[best_model],
            'anomalies': [
                {'year': year, 'levy_rate': rate, 'type': anomaly_type}
                for year, rate, anomaly_type in anomalies
            ],
            'generated_at': datetime.now().isoformat()
        }
        
        # Add AI-enhanced explanation if requested
        if include_explanation and self.claude_client:
            try:
                explanation = self._generate_forecast_explanation(
                    historical_data=historical_data_json,
                    forecast_result=result,
                    tax_code=tax_code
                )
                result['explanation'] = explanation
                
                # Generate recommendations
                recommendations = self._generate_recommendations(
                    historical_data=historical_data_json,
                    forecast_result=result,
                    tax_code=tax_code
                )
                result['recommendations'] = recommendations
                
            except Exception as e:
                logger.error(f"Error generating AI explanation: {str(e)}")
                result['explanation'] = f"Error generating explanation: {str(e)}"
        
        return result
    
    def analyze_tax_code_trends(
        self,
        tax_code_id: Optional[int] = None,
        tax_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze trends in tax code historical data.
        
        Args:
            tax_code_id: ID of the tax code to analyze
            tax_code: Code of the tax code to analyze (alternative to tax_code_id)
            
        Returns:
            Dictionary containing trend analysis results
        """
        # Validate parameters
        if not tax_code_id and not tax_code:
            raise ValueError("Either tax_code_id or tax_code must be provided")
        
        # Get historical data
        if tax_code_id:
            historical_data = self._get_historical_data_by_id(tax_code_id)
        else:
            historical_data = self._get_historical_data_by_code(tax_code)
        
        if len(historical_data) < 3:
            raise ValueError(f"Insufficient historical data. Need at least 3 years.")
        
        # Prepare data for analysis
        years = [data.year for data in historical_data]
        rates = [data.levy_rate for data in historical_data]
        levy_amounts = [data.levy_amount for data in historical_data]
        assessed_values = [data.total_assessed_value for data in historical_data]
        
        # Calculate year-over-year changes
        rate_changes = [
            (rates[i] - rates[i-1]) / rates[i-1] * 100 if rates[i-1] else 0
            for i in range(1, len(rates))
        ]
        
        amount_changes = [
            (levy_amounts[i] - levy_amounts[i-1]) / levy_amounts[i-1] * 100 if levy_amounts[i-1] else 0
            for i in range(1, len(levy_amounts))
        ]
        
        value_changes = [
            (assessed_values[i] - assessed_values[i-1]) / assessed_values[i-1] * 100 if assessed_values[i-1] else 0
            for i in range(1, len(assessed_values))
        ]
        
        # Calculate averages
        avg_rate_change = sum(rate_changes) / len(rate_changes) if rate_changes else 0
        avg_amount_change = sum(amount_changes) / len(amount_changes) if amount_changes else 0
        avg_value_change = sum(value_changes) / len(value_changes) if value_changes else 0
        
        # Prepare the result
        result = {
            'tax_code_id': tax_code_id,
            'tax_code': tax_code,
            'years': years,
            'rates': rates,
            'levy_amounts': levy_amounts,
            'assessed_values': assessed_values,
            'rate_changes': rate_changes,
            'amount_changes': amount_changes,
            'value_changes': value_changes,
            'avg_rate_change': avg_rate_change,
            'avg_amount_change': avg_amount_change,
            'avg_value_change': avg_value_change,
            'years_of_data': len(years),
            'generated_at': datetime.now().isoformat()
        }
        
        # Add AI-enhanced analysis if available
        if self.claude_client:
            try:
                analysis = self._generate_trend_analysis(result)
                result['analysis'] = analysis
            except Exception as e:
                logger.error(f"Error generating trend analysis: {str(e)}")
        
        return result
    
    def detect_anomalies(
        self,
        tax_code_id: Optional[int] = None,
        tax_code: Optional[str] = None,
        z_threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in historical tax code data.
        
        Args:
            tax_code_id: ID of the tax code to analyze
            tax_code: Code of the tax code to analyze (alternative to tax_code_id)
            z_threshold: Z-score threshold for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        # Validate parameters
        if not tax_code_id and not tax_code:
            raise ValueError("Either tax_code_id or tax_code must be provided")
        
        # Get historical data
        if tax_code_id:
            historical_data = self._get_historical_data_by_id(tax_code_id)
        else:
            historical_data = self._get_historical_data_by_code(tax_code)
        
        if len(historical_data) < 3:
            raise ValueError(f"Insufficient historical data. Need at least 3 years.")
        
        # Prepare data for analysis
        years = [data.year for data in historical_data]
        rates = [data.levy_rate for data in historical_data]
        
        # Detect anomalies
        anomalies = detect_anomalies(years, rates, z_threshold)
        
        # Format results
        result = [
            {
                'year': year,
                'levy_rate': rate,
                'type': anomaly_type,
                'z_score': z_score,
                'tax_code': tax_code or TaxCode.query.get(tax_code_id).code
            }
            for year, rate, anomaly_type, z_score in anomalies
        ]
        
        return result
    
    def _get_historical_data_by_id(self, tax_code_id: int) -> List[TaxCodeHistoricalRate]:
        """Get historical data for a tax code by ID."""
        historical_data = TaxCodeHistoricalRate.query.filter_by(
            tax_code_id=tax_code_id
        ).order_by(
            TaxCodeHistoricalRate.year
        ).all()
        
        return historical_data
    
    def _get_historical_data_by_code(self, tax_code: str) -> List[TaxCodeHistoricalRate]:
        """Get historical data for a tax code by code."""
        tax_code_obj = TaxCode.query.filter_by(code=tax_code).first()
        if not tax_code_obj:
            raise ValueError(f"Tax code {tax_code} not found")
            
        return self._get_historical_data_by_id(tax_code_obj.id)
    
    def _generate_forecast_explanation(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_result: Dict[str, Any],
        tax_code: str
    ) -> str:
        """
        Generate an AI-enhanced explanation of the forecast.
        
        Args:
            historical_data: Historical data for the tax code
            forecast_result: Forecast results
            tax_code: Tax code being forecasted
            
        Returns:
            AI-generated explanation
        """
        if not self.claude_client:
            return "AI explanation not available (API key not configured)"
        
        # Format data for the prompt
        historical_text = "\n".join([
            f"Year {data['year']}: Levy Rate {data['levy_rate']:.4f}, " +
            f"Assessed Value ${data['total_assessed_value']:,.2f}, " +
            f"Levy Amount ${data['levy_amount']:,.2f}"
            for data in historical_data
        ])
        
        forecast_text = "\n".join([
            f"Year {year}: Forecasted Rate {forecast_result['best_forecast']['forecast'][i]:.4f} " +
            f"(Range: {forecast_result['best_forecast']['lower_bound'][i]:.4f} - {forecast_result['best_forecast']['upper_bound'][i]:.4f})"
            for i, year in enumerate(forecast_result['years_forecasted'])
        ])
        
        model_comparison = "\n".join([
            f"- {model.title()} Model: RMSE {forecast_result['errors'][model]['rmse']:.4f}, " +
            f"MAE {forecast_result['errors'][model]['mae']:.4f}, " +
            f"MAPE {forecast_result['errors'][model]['mape']:.2f}%"
            for model in forecast_result['models']
        ])
        
        # Prepare the prompt
        prompt = f"""
        As an expert tax analyst, explain the following levy rate forecast for Tax Code {tax_code}.
        
        Historical Data:
        {historical_text}
        
        Forecast Results ({forecast_result['best_model'].title()} model was selected as best):
        {forecast_text}
        
        Model Comparison:
        {model_comparison}
        
        Please provide:
        1. A clear explanation of the forecast and what it means
        2. Analysis of any trends in the historical data
        3. Interpretation of the forecast confidence intervals
        4. Possible factors that might influence future levy rates
        5. How this forecast might impact property owners and tax districts
        
        Keep your explanation clear, concise, and suitable for tax professionals who need to make policy decisions.
        """
        
        # Get explanation from Claude
        explanation = self.claude_client.generate_text(prompt, max_tokens=1200)
        
        return explanation
    
    def _generate_recommendations(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_result: Dict[str, Any],
        tax_code: str
    ) -> List[str]:
        """
        Generate strategic recommendations based on the forecast.
        
        Args:
            historical_data: Historical data for the tax code
            forecast_result: Forecast results
            tax_code: Tax code being forecasted
            
        Returns:
            List of AI-generated recommendations
        """
        if not self.claude_client:
            return ["AI recommendations not available (API key not configured)"]
        
        # Format data for the prompt
        historical_text = "\n".join([
            f"Year {data['year']}: Levy Rate {data['levy_rate']:.4f}, " +
            f"Assessed Value ${data['total_assessed_value']:,.2f}, " +
            f"Levy Amount ${data['levy_amount']:,.2f}"
            for data in historical_data
        ])
        
        forecast_text = "\n".join([
            f"Year {year}: Forecasted Rate {forecast_result['best_forecast']['forecast'][i]:.4f} " +
            f"(Range: {forecast_result['best_forecast']['lower_bound'][i]:.4f} - {forecast_result['best_forecast']['upper_bound'][i]:.4f})"
            for i, year in enumerate(forecast_result['years_forecasted'])
        ])
        
        # Prepare the prompt
        prompt = f"""
        As a strategic tax policy advisor, provide 3-5 actionable recommendations based on this levy rate forecast for Tax Code {tax_code}.
        
        Historical Data:
        {historical_text}
        
        Forecast Results ({forecast_result['best_model'].title()} model):
        {forecast_text}
        
        Provide recommendations that would help:
        1. Optimize tax policy planning
        2. Address potential future challenges suggested by the forecast
        3. Balance revenue needs with taxpayer impact
        4. Improve long-term fiscal stability
        
        Format your response as a bullet point list with clear, concise recommendations that could be implemented by tax administrators.
        Each recommendation should be 1-2 sentences long.
        """
        
        # Get recommendations from Claude
        response = self.claude_client.generate_text(prompt, max_tokens=800)
        
        # Parse the bullet points
        recommendations = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                recommendations.append(line[1:].strip())
        
        # If parsing failed, just return the whole response
        if not recommendations:
            return [response]
        
        return recommendations
    
    def _generate_trend_analysis(
        self,
        trend_data: Dict[str, Any]
    ) -> str:
        """
        Generate an AI-enhanced analysis of tax code trends.
        
        Args:
            trend_data: Trend analysis data
            
        Returns:
            AI-generated trend analysis
        """
        if not self.claude_client:
            return "AI analysis not available (API key not configured)"
        
        # Format data for the prompt
        yearly_data = "\n".join([
            f"Year {trend_data['years'][i]}: " +
            f"Levy Rate {trend_data['rates'][i]:.4f}, " +
            f"Assessed Value ${trend_data['assessed_values'][i]:,.2f}, " +
            f"Levy Amount ${trend_data['levy_amounts'][i]:,.2f}"
            for i in range(len(trend_data['years']))
        ])
        
        if len(trend_data['rate_changes']) > 0:
            changes_data = "\n".join([
                f"Years {trend_data['years'][i]} to {trend_data['years'][i+1]}: " +
                f"Rate Change {trend_data['rate_changes'][i]:.2f}%, " +
                f"Amount Change {trend_data['amount_changes'][i]:.2f}%, " +
                f"Value Change {trend_data['value_changes'][i]:.2f}%"
                for i in range(len(trend_data['rate_changes']))
            ])
        else:
            changes_data = "No year-over-year change data available (insufficient historical data)"
        
        # Prepare the prompt
        prompt = f"""
        As an expert tax analyst, analyze the following trends for Tax Code {trend_data['tax_code']}.
        
        Annual Data:
        {yearly_data}
        
        Year-over-Year Changes:
        {changes_data}
        
        Averages:
        - Average Levy Rate Change: {trend_data['avg_rate_change']:.2f}%
        - Average Levy Amount Change: {trend_data['avg_amount_change']:.2f}%
        - Average Assessed Value Change: {trend_data['avg_value_change']:.2f}%
        
        Please provide:
        1. A clear analysis of the overall trends
        2. Identification of any unusual patterns or outliers
        3. Relationship between assessed values and levy rates
        4. Possible explanations for the observed trends
        5. Implications for tax planning and administration
        
        Keep your analysis clear, concise, and suitable for tax professionals.
        """
        
        # Get analysis from Claude
        analysis = self.claude_client.generate_text(prompt, max_tokens=1000)
        
        return analysis