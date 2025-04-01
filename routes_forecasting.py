"""
Routes for the forecasting functionality.

This module includes routes for tax levy forecasting and analysis:
- Forecast creation and management
- Visualization of forecast results
- Scenario comparison
- AI-enhanced forecasting and insights
- Interactive visualizations and dashboards
"""

import logging
import json
from datetime import datetime
from flask import render_template, request, jsonify, flash, Response
from app import app, db
from models import TaxCode, TaxCodeHistoricalRate
from utils import forecasting_utils
from utils import ai_forecasting_utils
from utils import interactive_visualization_utils

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


@app.route('/forecasting/ai', methods=['GET'])
def ai_forecasting_dashboard():
    """
    Dashboard for AI-enhanced property tax forecasting.
    
    Displays AI-powered forecasting options and features.
    """
    # Get all tax codes for selector
    tax_codes = TaxCode.query.order_by(TaxCode.code).all()
    
    # Get current year for context
    current_year = datetime.now().year
    
    return render_template('forecasting/ai_dashboard.html',
                         tax_codes=tax_codes,
                         current_year=current_year)


@app.route('/forecasting/ai/generate', methods=['POST'])
def generate_ai_forecast():
    """
    Generate an AI-enhanced forecast for a tax code.
    
    Uses AI to select the most appropriate model and generate explanations and recommendations.
    """
    # Get parameters from request
    tax_code = request.form.get('tax_code')
    years_ahead = int(request.form.get('years_ahead', 3))
    scenario = request.form.get('scenario', 'baseline')
    
    # Validate parameters
    if not tax_code:
        flash('Tax code is required', 'danger')
        return jsonify({'error': 'Tax code is required'}), 400
    
    if years_ahead < 1 or years_ahead > 10:
        flash('Years ahead must be between 1 and 10', 'danger')
        return jsonify({'error': 'Years ahead must be between 1 and 10'}), 400
    
    if scenario not in ['baseline', 'optimistic', 'pessimistic']:
        flash('Invalid scenario', 'danger')
        return jsonify({'error': 'Invalid scenario'}), 400
    
    try:
        # Get historical data for the tax code
        historical_data = forecasting_utils.get_historical_data_for_tax_code(tax_code)
        
        if not historical_data or len(historical_data['years']) < 3:
            flash('Insufficient historical data for AI forecasting', 'warning')
            return jsonify({'error': 'Insufficient historical data for AI forecasting'}), 400
        
        # Use AI to select the most appropriate model
        selected_model = ai_forecasting_utils.ai_forecast_model_selector(historical_data)
        
        # Generate forecast with the selected model
        forecast_result = forecasting_utils.generate_forecast_for_tax_code(
            tax_code=tax_code,
            model_type=selected_model.model_type,
            years_ahead=years_ahead,
            scenario=scenario
        )
        
        # Generate natural language explanation
        explanation = ai_forecasting_utils.generate_forecast_explanation(forecast_result)
        
        # Detect anomalies in historical data
        anomalies = ai_forecasting_utils.detect_anomalies(historical_data)
        
        # Generate recommendations
        recommendations = ai_forecasting_utils.generate_forecast_recommendations(forecast_result)
        
        # Add AI-enhanced data to the result
        forecast_result['ai_enhanced'] = {
            'selected_model': selected_model.model_type,
            'explanation': explanation,
            'anomalies': anomalies,
            'recommendations': recommendations
        }
        
        return jsonify(forecast_result)
    except Exception as e:
        logger.exception(f"Error generating AI forecast: {str(e)}")
        flash(f"Error generating AI forecast: {str(e)}", 'danger')
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/ai/anomalies', methods=['POST'])
def detect_historical_anomalies():
    """
    Detect anomalies in historical tax rate data for a tax code.
    
    Returns a list of detected anomalies with explanations.
    """
    # Get parameters from request
    tax_code = request.form.get('tax_code')
    
    # Validate parameters
    if not tax_code:
        flash('Tax code is required', 'danger')
        return jsonify({'error': 'Tax code is required'}), 400
    
    try:
        # Get historical data for the tax code
        historical_data = forecasting_utils.get_historical_data_for_tax_code(tax_code)
        
        if not historical_data or len(historical_data['years']) < 3:
            flash('Insufficient historical data for anomaly detection', 'warning')
            return jsonify({'error': 'Insufficient historical data for anomaly detection'}), 400
        
        # Detect anomalies
        anomalies = ai_forecasting_utils.detect_anomalies(historical_data)
        
        return jsonify({
            'tax_code': tax_code,
            'anomalies': anomalies
        })
    except Exception as e:
        logger.exception(f"Error detecting anomalies: {str(e)}")
        flash(f"Error detecting anomalies: {str(e)}", 'danger')
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/ai/recommendations', methods=['POST'])
def generate_forecast_recommendations():
    """
    Generate AI-powered recommendations based on a forecast.
    
    Accepts a forecast result and returns a list of recommendations.
    """
    # Get forecast data from request
    forecast_data = request.json
    
    if not forecast_data:
        flash('Forecast data is required', 'danger')
        return jsonify({'error': 'Forecast data is required'}), 400
    
    try:
        # Generate recommendations
        recommendations = ai_forecasting_utils.generate_forecast_recommendations(forecast_data)
        
        return jsonify({
            'tax_code': forecast_data.get('tax_code'),
            'recommendations': recommendations
        })
    except Exception as e:
        logger.exception(f"Error generating recommendations: {str(e)}")
        flash(f"Error generating recommendations: {str(e)}", 'danger')
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/interactive', methods=['GET'])
def interactive_forecasting_dashboard():
    """
    Interactive dashboard for property tax forecasting with enhanced visualizations.
    
    Provides an interface with advanced filtering, drill-down capabilities, and comparative analysis.
    """
    # Get all tax codes for selector
    tax_codes = TaxCode.query.order_by(TaxCode.code).all()
    
    # Get current year for context
    current_year = datetime.now().year
    
    return render_template('forecasting/interactive_dashboard.html',
                         tax_codes=tax_codes,
                         current_year=current_year)


@app.route('/forecasting/interactive/chart-config', methods=['POST'])
def get_interactive_chart_config():
    """
    Get interactive chart configuration for a specific chart type.
    
    Returns enhanced chart configuration with interactive features.
    """
    # Get parameters
    chart_type = request.form.get('chart_type', 'line')
    data = request.json or {}
    
    try:
        # Get chart configuration
        chart_config = interactive_visualization_utils.create_interactive_chart(data, chart_type)
        return jsonify(chart_config)
    except Exception as e:
        logger.exception(f"Error generating chart config: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/interactive/comparison', methods=['POST'])
def get_comparative_visualization():
    """
    Generate an enhanced comparative visualization for different scenarios.
    
    Returns visualization configuration with interactive features.
    """
    # Get parameters
    scenarios = request.json
    
    if not scenarios:
        return jsonify({'error': 'Scenario data is required'}), 400
    
    try:
        # Generate comparative visualization
        visualization = interactive_visualization_utils.create_comparative_visualization(scenarios)
        return jsonify(visualization)
    except Exception as e:
        logger.exception(f"Error generating comparative visualization: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/interactive/dashboard-config', methods=['POST'])
def get_dynamic_dashboard_config():
    """
    Generate a configuration for a dynamic dashboard with multiple visualizations.
    
    Returns dashboard configuration with panels, filters, and interaction settings.
    """
    # Get parameters
    datasets = request.json
    
    if not datasets:
        return jsonify({'error': 'Dataset information is required'}), 400
    
    try:
        # Generate dashboard configuration
        dashboard_config = interactive_visualization_utils.create_dynamic_dashboard(datasets)
        return jsonify(dashboard_config)
    except Exception as e:
        logger.exception(f"Error generating dashboard configuration: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/forecasting/districts/map', methods=['POST'])
def get_tax_district_map():
    """
    Generate a map visualization for tax districts.
    
    Returns a map with tax districts colored by levy rates.
    """
    # Get parameters
    district_data = request.json
    
    if not district_data:
        return jsonify({'error': 'District data is required'}), 400
    
    try:
        # Generate map visualization
        map_config = interactive_visualization_utils.create_tax_district_map(district_data)
        return jsonify(map_config)
    except Exception as e:
        logger.exception(f"Error generating district map: {str(e)}")
        return jsonify({'error': str(e)}), 500


def init_forecasting_routes():
    """Initialize forecasting routes with the Flask app."""
    # Routes are automatically registered via decorators
    logger.info("Forecasting routes initialized")