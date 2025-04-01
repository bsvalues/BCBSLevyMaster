"""
Routes for the forecasting functionality.

This module includes routes for tax levy forecasting and analysis:
- Forecast creation and management
- Visualization of forecast results
- Scenario comparison
"""

import logging
import json
from datetime import datetime
from flask import render_template, request, jsonify, flash, Response
from app import app, db
from models import TaxCode, TaxCodeHistoricalRate
from utils import forecasting_utils

# Configure logger
logger = logging.getLogger(__name__)


@app.route('/forecasting', methods=['GET'])
def forecasting_dashboard():
    """
    Dashboard for property tax forecasting.
    
    Displays forecasting options and saved forecasts.
    """
    # Get all tax codes for selector
    tax_codes = TaxCode.query.order_by(TaxCode.code).all()
    
    # Get current year for context
    current_year = datetime.now().year
    
    return render_template('forecasting/dashboard.html',
                         tax_codes=tax_codes,
                         current_year=current_year)


@app.route('/forecasting/generate', methods=['POST'])
def generate_forecast():
    """
    Generate a forecast for a tax code.
    
    Accepts parameters for forecast generation and returns the forecast data.
    """
    # Get parameters from request
    tax_code = request.form.get('tax_code')
    model_type = request.form.get('model_type', 'linear')
    years_ahead = int(request.form.get('years_ahead', 3))
    scenario = request.form.get('scenario', 'baseline')
    
    # Validate parameters
    if not tax_code:
        flash('Tax code is required', 'danger')
        return jsonify({'error': 'Tax code is required'}), 400
    
    if model_type not in ['linear', 'exponential', 'arima']:
        flash('Invalid model type', 'danger')
        return jsonify({'error': 'Invalid model type'}), 400
    
    if years_ahead < 1 or years_ahead > 10:
        flash('Years ahead must be between 1 and 10', 'danger')
        return jsonify({'error': 'Years ahead must be between 1 and 10'}), 400
    
    if scenario not in ['baseline', 'optimistic', 'pessimistic']:
        flash('Invalid scenario', 'danger')
        return jsonify({'error': 'Invalid scenario'}), 400
    
    try:
        # Generate forecast
        forecast_result = forecasting_utils.generate_forecast_for_tax_code(
            tax_code=tax_code,
            model_type=model_type,
            years_ahead=years_ahead,
            scenario=scenario
        )
        
        return jsonify(forecast_result)
    except forecasting_utils.InsufficientDataError as e:
        flash(str(e), 'warning')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception(f"Error generating forecast: {str(e)}")
        flash(f"Error generating forecast: {str(e)}", 'danger')
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/compare', methods=['GET'])
def forecast_comparison():
    """
    Page for comparing different forecast scenarios.
    """
    # Get all tax codes for selector
    tax_codes = TaxCode.query.order_by(TaxCode.code).all()
    
    # Get current year for context
    current_year = datetime.now().year
    
    return render_template('forecasting/comparison.html',
                         tax_codes=tax_codes,
                         current_year=current_year)


@app.route('/forecasting/compare', methods=['POST'])
def generate_comparison():
    """
    Generate a comparison of different forecast scenarios.
    
    Accepts parameters for scenario generation and returns the comparison data.
    """
    # Get parameters from request
    tax_code = request.form.get('tax_code')
    model_type = request.form.get('model_type', 'linear')
    years_ahead = int(request.form.get('years_ahead', 3))
    
    # Validate parameters
    if not tax_code:
        flash('Tax code is required', 'danger')
        return jsonify({'error': 'Tax code is required'}), 400
    
    if model_type not in ['linear', 'exponential', 'arima']:
        flash('Invalid model type', 'danger')
        return jsonify({'error': 'Invalid model type'}), 400
    
    if years_ahead < 1 or years_ahead > 10:
        flash('Years ahead must be between 1 and 10', 'danger')
        return jsonify({'error': 'Years ahead must be between 1 and 10'}), 400
    
    try:
        # Generate forecasts for different scenarios
        baseline_forecast = forecasting_utils.generate_forecast_for_tax_code(
            tax_code=tax_code,
            model_type=model_type,
            years_ahead=years_ahead,
            scenario='baseline'
        )
        
        optimistic_forecast = forecasting_utils.generate_forecast_for_tax_code(
            tax_code=tax_code,
            model_type=model_type,
            years_ahead=years_ahead,
            scenario='optimistic'
        )
        
        pessimistic_forecast = forecasting_utils.generate_forecast_for_tax_code(
            tax_code=tax_code,
            model_type=model_type,
            years_ahead=years_ahead,
            scenario='pessimistic'
        )
        
        # Create comparison data
        comparison_data = {
            'tax_code': tax_code,
            'historical_data': baseline_forecast['historical_data'],
            'scenarios': {
                'baseline': baseline_forecast['forecast'],
                'optimistic': optimistic_forecast['forecast'],
                'pessimistic': pessimistic_forecast['forecast']
            },
            'chart_data': forecasting_utils.create_scenario_comparison_chart(
                baseline_forecast['historical_data'],
                {
                    'baseline': baseline_forecast['forecast'],
                    'optimistic': optimistic_forecast['forecast'],
                    'pessimistic': pessimistic_forecast['forecast']
                }
            )
        }
        
        return jsonify(comparison_data)
    except forecasting_utils.InsufficientDataError as e:
        flash(str(e), 'warning')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception(f"Error generating comparison: {str(e)}")
        flash(f"Error generating comparison: {str(e)}", 'danger')
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/district', methods=['GET'])
def district_forecasting():
    """
    Page for forecasting at the district level.
    """
    # Query for all districts
    query = """
        SELECT DISTINCT tax_district_id 
        FROM tax_district 
        ORDER BY tax_district_id
    """
    districts = db.session.execute(query).fetchall()
    
    # Get current year for context
    current_year = datetime.now().year
    
    return render_template('forecasting/district.html',
                         districts=districts,
                         current_year=current_year)


@app.route('/forecasting/district/generate', methods=['POST'])
def generate_district_forecast():
    """
    Generate a forecast for a district.
    
    Accepts parameters for district forecast generation and returns the forecast data.
    """
    # Get parameters from request
    district_id = int(request.form.get('district_id'))
    model_type = request.form.get('model_type', 'linear')
    years_ahead = int(request.form.get('years_ahead', 3))
    scenario = request.form.get('scenario', 'baseline')
    
    # Validate parameters
    if not district_id:
        flash('District ID is required', 'danger')
        return jsonify({'error': 'District ID is required'}), 400
    
    if model_type not in ['linear', 'exponential', 'arima']:
        flash('Invalid model type', 'danger')
        return jsonify({'error': 'Invalid model type'}), 400
    
    if years_ahead < 1 or years_ahead > 10:
        flash('Years ahead must be between 1 and 10', 'danger')
        return jsonify({'error': 'Years ahead must be between 1 and 10'}), 400
    
    if scenario not in ['baseline', 'optimistic', 'pessimistic']:
        flash('Invalid scenario', 'danger')
        return jsonify({'error': 'Invalid scenario'}), 400
    
    try:
        # Generate district forecast
        forecast_result = forecasting_utils.generate_district_forecast(
            district_id=district_id,
            model_type=model_type,
            years_ahead=years_ahead,
            scenario=scenario
        )
        
        return jsonify(forecast_result)
    except forecasting_utils.InsufficientDataError as e:
        flash(str(e), 'warning')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception(f"Error generating district forecast: {str(e)}")
        flash(f"Error generating district forecast: {str(e)}", 'danger')
        return jsonify({'error': str(e)}), 500


def init_forecasting_routes():
    """Initialize forecasting routes with the Flask app."""
    # Routes are automatically registered via decorators
    logger.info("Forecasting routes initialized")