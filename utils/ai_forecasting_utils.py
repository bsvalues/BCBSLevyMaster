"""
AI-enhanced forecasting utilities for the Levy Calculation Application.

This module provides functions that use Claude API to generate explanations
and recommendations for forecast results.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import anthropic

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