"""
Routes for the forecasting module of the Levy Calculation Application.

This module provides routes for generating forecasts of levy rates
using historical data and various statistical models.
"""
import json
import logging
from typing import Dict, Any, List, Tuple, Optional

from flask import Blueprint, render_template, request, flash, redirect, url_for
from sqlalchemy import func

from app2 import db
from models import TaxCode, TaxCodeHistoricalRate
from utils.forecasting_utils import (
    generate_forecast_for_tax_code,
    create_forecast_chart_data,
    InsufficientDataError,
    FORECAST_MODELS
)

# Setup AI-enhanced forecasting if available
try:
    from utils.ai_forecasting_utils import (
        generate_forecast_explanation,
        generate_forecast_recommendations
    )
    AI_FORECASTING_AVAILABLE = True
except ImportError:
    AI_FORECASTING_AVAILABLE = False
    
# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
forecasting_bp = Blueprint('forecasting', __name__, url_prefix='/forecasting')

@forecasting_bp.route('/', methods=['GET'])
def index():
    """Render the forecasting index page."""
    # Get tax codes with sufficient historical data (at least 3 years)
    tax_codes_with_counts = db.session.query(
        TaxCode,
        func.count(TaxCodeHistoricalRate.id).label('history_count')
    ).join(
        TaxCodeHistoricalRate,
        TaxCode.id == TaxCodeHistoricalRate.tax_code_id
    ).group_by(
        TaxCode.id
    ).having(
        func.count(TaxCodeHistoricalRate.id) >= 3
    ).order_by(
        TaxCode.code
    ).all()
    
    # Format for the template
    tax_codes = []
    for tax_code, history_count in tax_codes_with_counts:
        tax_code.history_count = history_count
        tax_codes.append(tax_code)
    
    return render_template(
        'forecasting/index.html',
        page_title='Levy Rate Forecasting',
        tax_codes=tax_codes
    )

@forecasting_bp.route('/analyze/<int:tax_code_id>', methods=['GET'])
def analyze(tax_code_id: int):
    """Analyze historical data for a specific tax code."""
    # Get the tax code
    tax_code = TaxCode.query.get_or_404(tax_code_id)
    
    # Get historical rates for this tax code
    historical_rates = TaxCodeHistoricalRate.query.filter_by(
        tax_code_id=tax_code_id
    ).order_by(
        TaxCodeHistoricalRate.year
    ).all()
    
    if len(historical_rates) < 3:
        flash('Insufficient historical data for analysis. At least 3 years of data is required.', 'warning')
        return redirect(url_for('forecasting.index'))
    
    # Extract data for the template
    years = [rate.year for rate in historical_rates]
    rates = [rate.levy_rate for rate in historical_rates]
    levy_amounts = [rate.levy_amount for rate in historical_rates]
    assessed_values = [rate.total_assessed_value for rate in historical_rates]
    
    # Prepare JSON data for charts
    years_json = json.dumps(years)
    rates_json = json.dumps(rates)
    levy_amounts_json = json.dumps(levy_amounts)
    assessed_values_json = json.dumps(assessed_values)
    
    return render_template(
        'forecasting/analyze.html',
        page_title=f'Tax Code Analysis: {tax_code.code}',
        tax_code=tax_code,
        historical_rates=historical_rates,
        years=years,
        rates=rates,
        years_json=years_json,
        rates_json=rates_json,
        levy_amounts_json=levy_amounts_json,
        assessed_values_json=assessed_values_json
    )

@forecasting_bp.route('/forecast', methods=['GET', 'POST'])
def forecast():
    """Generate forecasts for a specific tax code."""
    # Get tax codes with sufficient historical data
    tax_codes_with_counts = db.session.query(
        TaxCode,
        func.count(TaxCodeHistoricalRate.id).label('history_count')
    ).join(
        TaxCodeHistoricalRate,
        TaxCode.id == TaxCodeHistoricalRate.tax_code_id
    ).group_by(
        TaxCode.id
    ).having(
        func.count(TaxCodeHistoricalRate.id) >= 3
    ).order_by(
        TaxCode.code
    ).all()
    
    # Format for the template
    tax_codes = []
    for tax_code, history_count in tax_codes_with_counts:
        tax_code.history_count = history_count
        tax_codes.append(tax_code)
    
    # For GET requests, show the form
    if request.method == 'GET':
        # Get optional pre-selected tax code from query string
        tax_code_id = request.args.get('tax_code_id', type=int)
        
        return render_template(
            'forecasting/forecast.html',
            page_title='Generate Forecast',
            tax_codes=tax_codes,
            tax_code_id=tax_code_id,
            years_to_forecast=3,
            confidence_level=0.95,
            preferred_model=None,
            include_explanation=AI_FORECASTING_AVAILABLE
        )
    
    # For POST requests, generate the forecast
    # Get form parameters
    tax_code_id = request.form.get('tax_code_id', type=int)
    years_to_forecast = request.form.get('years_to_forecast', type=int, default=3)
    confidence_level = request.form.get('confidence_level', type=float, default=0.95)
    preferred_model = request.form.get('preferred_model', default=None)
    include_explanation = request.form.get('include_explanation') == 'true'
    
    # Validate inputs
    if not tax_code_id:
        flash('Please select a tax code', 'danger')
        return render_template(
            'forecasting/forecast.html',
            page_title='Generate Forecast',
            tax_codes=tax_codes,
            years_to_forecast=years_to_forecast,
            confidence_level=confidence_level,
            preferred_model=preferred_model,
            include_explanation=include_explanation
        )
    
    if years_to_forecast < 1 or years_to_forecast > 10:
        flash('Years to forecast must be between 1 and 10', 'danger')
        return render_template(
            'forecasting/forecast.html',
            page_title='Generate Forecast',
            tax_codes=tax_codes,
            tax_code_id=tax_code_id,
            years_to_forecast=3,
            confidence_level=confidence_level,
            preferred_model=preferred_model,
            include_explanation=include_explanation
        )
    
    if preferred_model and preferred_model not in FORECAST_MODELS:
        flash(f'Invalid forecast model. Valid options are: {", ".join(FORECAST_MODELS)}', 'danger')
        return render_template(
            'forecasting/forecast.html',
            page_title='Generate Forecast',
            tax_codes=tax_codes,
            tax_code_id=tax_code_id,
            years_to_forecast=years_to_forecast,
            confidence_level=0.95,
            preferred_model=None,
            include_explanation=include_explanation
        )
    
    # Generate the forecast
    try:
        result = generate_forecast_for_tax_code(
            tax_code_id=tax_code_id,
            years_to_forecast=years_to_forecast,
            confidence_level=confidence_level,
            preferred_model=preferred_model
        )
        
        # Prepare chart data
        chart_data = create_forecast_chart_data(
            years=result['historical_years'],
            values=result['historical_rates'],
            future_years=result['forecast_years'],
            forecasts={
                result['best_model']: result['forecasts'][result['best_model']]
            }
        )
        
        # Generate AI-enhanced explanation if requested
        ai_explanation = None
        ai_recommendations = None
        
        if include_explanation and AI_FORECASTING_AVAILABLE:
            try:
                ai_explanation = generate_forecast_explanation(
                    tax_code=result['tax_code'],
                    historical_years=result['historical_years'],
                    historical_rates=result['historical_rates'],
                    forecast_years=result['forecast_years'],
                    forecast_rates=result['forecasts'][result['best_model']]['forecast'],
                    best_model=result['best_model'],
                    anomalies=result['anomalies']
                )
                
                ai_recommendations = generate_forecast_recommendations(
                    tax_code=result['tax_code'],
                    historical_rates=result['historical_rates'],
                    forecast_rates=result['forecasts'][result['best_model']]['forecast'],
                    current_year=result['historical_years'][-1],
                    forecast_years=result['forecast_years']
                )
            except Exception as e:
                logger.error(f"Error generating AI explanation: {str(e)}")
                flash('AI-enhanced explanation could not be generated.', 'warning')
        
        # Format data for the chart
        all_years_json = json.dumps(chart_data['years'])
        historical_with_nulls_json = json.dumps(chart_data['historical'])
        forecast_json = json.dumps(chart_data[f'{result["best_model"]}_forecast'])
        lower_bound_json = json.dumps(chart_data[f'{result["best_model"]}_lower'])
        upper_bound_json = json.dumps(chart_data[f'{result["best_model"]}_upper'])
        
        # Display confidence level as percentage
        confidence_percent = int(confidence_level * 100)
        
        return render_template(
            'forecasting/forecast_result.html',
            page_title=f'Forecast Results: {result["tax_code"]}',
            result=result,
            confidence_level=confidence_percent,
            all_years_json=all_years_json,
            historical_with_nulls_json=historical_with_nulls_json,
            forecast_json=forecast_json,
            lower_bound_json=lower_bound_json,
            upper_bound_json=upper_bound_json,
            ai_explanation=ai_explanation,
            ai_recommendations=ai_recommendations
        )
    
    except InsufficientDataError:
        flash('Insufficient historical data for forecasting. At least 3 years of data is required.', 'danger')
    except ValueError as e:
        flash(f'Error generating forecast: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Unexpected error in forecast: {str(e)}")
        flash('An unexpected error occurred while generating the forecast.', 'danger')
    
    return render_template(
        'forecasting/forecast.html',
        page_title='Generate Forecast',
        tax_codes=tax_codes,
        tax_code_id=tax_code_id,
        years_to_forecast=years_to_forecast,
        confidence_level=confidence_level,
        preferred_model=preferred_model,
        include_explanation=include_explanation
    )