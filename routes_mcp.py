"""
Routes for MCP (Model Content Protocol) insights and integration.

This module provides routes for the MCP insights page and related functionality.
It integrates with the Anthropic Claude API to provide AI-powered insights.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, current_app, request, jsonify, session, redirect, url_for, flash
from sqlalchemy import desc, func, case

from app import db
from models import TaxDistrict, TaxCode, Property, ImportLog, ExportLog
from utils.anthropic_utils import get_claude_service, check_api_key_status
from utils.html_sanitizer import sanitize_html
from utils.api_logging import get_api_statistics
from utils.schema_utils import (
    get_recent_import_logs,
    get_recent_export_logs,
    get_tax_code_summary,
    get_table_counts,
    get_property_assessed_value_avg
)

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp')

@mcp_bp.route('/check-api-key', methods=['GET'])
def check_api_key():
    """
    Check the status of the configured Anthropic API key.
    
    This endpoint checks if an API key is configured and if it has the correct format.
    It returns the status and a message with details.
    """
    try:
        key_status = check_api_key_status()
        
        # Add additional details based on status
        if key_status['status'] == 'no_credits':
            key_status['details'] = {
                'help_link': 'https://console.anthropic.com/settings/billing',
                'suggestion': 'Add credits to your account or use a different API key',
                'action_required': True
            }
        elif key_status['status'] == 'missing':
            key_status['details'] = {
                'help_link': 'https://console.anthropic.com/account/keys',
                'suggestion': 'Configure an Anthropic API key to enable AI-powered insights',
                'action_required': True
            }
        elif key_status['status'] == 'valid':
            key_status['details'] = {
                'suggestion': 'Your API key is properly configured',
                'action_required': False
            }
        
        return jsonify(key_status)
    except Exception as e:
        logger.error(f"Error checking API key status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'details': {
                'suggestion': 'An error occurred while checking API key status',
                'action_required': True
            }
        }), 500
        
@mcp_bp.route('/api/status', methods=['GET'])
def api_status_check():
    """
    API endpoint to check the status of the Anthropic API integration.
    
    This endpoint returns JSON with detailed status information about the API key,
    including validation, credit status, and response times.
    """
    try:
        # Get API key status with retry capability
        key_status = check_api_key_status(max_retries=2, retry_delay=0.5)
        
        # Basic response with status information
        response = {
            'status': key_status['status'],
            'message': key_status['message'],
            'timestamp': datetime.utcnow().isoformat(),
            'details': {}
        }
        
        # Add status-specific details
        if key_status['status'] == 'valid':
            response['details'] = {
                'credit_status': 'available',
                'model': 'claude-3-5-sonnet-20241022',
                'suggestion': 'API key is valid and has sufficient credits',
                'action_required': False
            }
        elif key_status['status'] == 'no_credits':
            response['details'] = {
                'credit_status': 'insufficient',
                'billing_url': 'https://console.anthropic.com/settings/billing',
                'suggestion': 'Add credits to your account or use a different API key',
                'action_required': True
            }
        elif key_status['status'] == 'missing':
            response['details'] = {
                'help_link': 'https://console.anthropic.com/account/keys',
                'suggestion': 'Configure an Anthropic API key to enable AI-powered insights',
                'action_required': True
            }
        elif key_status['status'] == 'invalid':
            response['details'] = {
                'help_link': 'https://console.anthropic.com/account/keys',
                'suggestion': 'Your API key appears to be invalid. Please check and reconfigure it.',
                'action_required': True
            }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error checking API status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'details': {
                'suggestion': 'An unexpected error occurred while checking API status',
                'action_required': True
            }
        }), 500

@mcp_bp.route('/configure-api-key', methods=['POST'])
def configure_api_key():
    """
    Configure the Anthropic API key for MCP insights.
    
    This endpoint accepts a POST request with the API key to be configured.
    It sets the key in the environment and validates it, checking for credit issues.
    """
    try:
        data = request.json
        api_key = data.get('api_key', '').strip()
        
        if not api_key:
            return jsonify({'success': False, 'message': 'API key is required'}), 400
            
        # Basic validation
        if not api_key.startswith('sk-ant-'):
            return jsonify({'success': False, 'message': 'Invalid API key format. Anthropic API keys should start with "sk-ant-"'}), 400
        
        # Set the key in the environment
        os.environ['ANTHROPIC_API_KEY'] = api_key
        
        # Validate the key and check its status
        key_status = check_api_key_status()
        logger.info(f"API key configured with status: {key_status['status']}")
        
        if key_status['status'] == 'valid':
            # Successfully configured
            return jsonify({
                'success': True, 
                'message': 'API key configured successfully',
                'status': key_status['status']
            })
        elif key_status['status'] == 'no_credits':
            # Key is valid but has no credits
            return jsonify({
                'success': False, 
                'message': 'API key is valid but has insufficient credits. Please add credits to your Anthropic account.',
                'status': key_status['status']
            })
        else:
            # Other validation issues
            return jsonify({
                'success': False, 
                'message': f'API key validation failed: {key_status["message"]}',
                'status': key_status['status']
            })
    except Exception as e:
        logger.error(f"Error configuring API key: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@mcp_bp.route('/api-status', methods=['GET'])
def api_status():
    """
    Render the API status page with detailed diagnostics and troubleshooting information.
    
    This page provides a comprehensive view of the Anthropic API connection status,
    including diagnostics, troubleshooting guides, and links to external resources.
    """
    return render_template('mcp_api_status.html')
    

@mcp_bp.route('/api-analytics', methods=['GET'])
def api_analytics():
    """
    Render the API analytics page with historical data and performance metrics.
    
    This page provides charts, graphs, and tables showing API usage patterns,
    error rates, and performance statistics over different time periods.
    """
    return render_template('api_analytics.html')


@mcp_bp.route('/api/service-breakdown', methods=['GET'])
def api_service_breakdown():
    """
    API endpoint to retrieve a breakdown of API calls by service.
    
    This endpoint returns JSON with statistics about API calls grouped by service,
    including success rates, error rates, and performance metrics.
    
    Query Parameters:
    - timeframe: Filter by time period (day, week, month, all)
    """
    try:
        from models import APICallLog, db
        from sqlalchemy import func
        
        # Parse query parameters
        timeframe = request.args.get('timeframe', 'week')
        
        # Build query
        query = db.session.query(
            APICallLog.service,
            func.count().label('total'),
            func.sum(case((APICallLog.success == True, 1), else_=0)).label('success_count'),
            func.sum(case((APICallLog.success == False, 1), else_=0)).label('error_count'),
            func.avg(APICallLog.duration_ms).label('avg_duration')
        )
        
        # Apply timeframe filter
        if timeframe == 'day':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=1))
            )
        elif timeframe == 'week':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(weeks=1))
            )
        elif timeframe == 'month':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=30))
            )
        
        # Group by service
        query = query.group_by(APICallLog.service)
        
        # Order by total calls descending
        query = query.order_by(func.count().desc())
        
        # Execute query
        results = query.all()
        
        # Format results
        services = []
        for result in results:
            services.append({
                'service': result.service,
                'total_calls': result.total,
                'success_count': result.success_count or 0,
                'error_count': result.error_count or 0,
                'error_rate_percent': round((result.error_count or 0) / result.total * 100, 2) if result.total > 0 else 0,
                'avg_duration_ms': round(result.avg_duration or 0, 2)
            })
        
        # Return JSON response
        return jsonify({
            'services': services,
            'timeframe': timeframe,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving service breakdown: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500


@mcp_bp.route('/api/timeseries', methods=['GET'])
def api_timeseries():
    """
    API endpoint to retrieve time series data for API calls.
    
    This endpoint returns JSON with data points for API calls over time,
    grouped by the specified interval.
    
    Query Parameters:
    - timeframe: Filter by time period (day, week, month, all)
    - interval: Interval for grouping (hour, day, week, month)
    - service: Filter by service name (optional)
    """
    try:
        from models import APICallLog, db
        from sqlalchemy import func
        
        # Parse query parameters
        timeframe = request.args.get('timeframe', 'week')
        interval = request.args.get('interval', 'day')
        service_filter = request.args.get('service')
        
        # Determine timestamp truncation function based on interval
        if interval == 'hour':
            # Truncate to hour
            date_trunc = func.date_trunc('hour', APICallLog.timestamp)
        elif interval == 'day':
            # Truncate to day
            date_trunc = func.date_trunc('day', APICallLog.timestamp)
        elif interval == 'week':
            # Truncate to week
            date_trunc = func.date_trunc('week', APICallLog.timestamp)
        else:  # month
            # Truncate to month
            date_trunc = func.date_trunc('month', APICallLog.timestamp)
        
        # Build query
        query = db.session.query(
            date_trunc.label('interval'),
            func.count().label('total'),
            func.sum(case((APICallLog.success == True, 1), else_=0)).label('success'),
            func.sum(case((APICallLog.success == False, 1), else_=0)).label('error'),
            func.avg(APICallLog.duration_ms).label('avg_duration')
        )
        
        # Apply timeframe filter
        if timeframe == 'day':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=1))
            )
        elif timeframe == 'week':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(weeks=1))
            )
        elif timeframe == 'month':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=30))
            )
        
        # Apply service filter if provided
        if service_filter:
            query = query.filter(APICallLog.service == service_filter)
        
        # Group by interval and order by interval
        query = query.group_by(date_trunc).order_by(date_trunc)
        
        # Execute query
        results = query.all()
        
        # Format results
        data_points = []
        for result in results:
            data_points.append({
                'timestamp': result.interval.isoformat(),
                'total': result.total,
                'success': result.success or 0,
                'error': result.error or 0,
                'avg_duration_ms': float(result.avg_duration or 0)
            })
        
        # Return JSON response
        return jsonify({
            'data_points': data_points,
            'timeframe': timeframe,
            'interval': interval,
            'service': service_filter or 'all'
        })
        
    except Exception as e:
        logger.error(f"Error retrieving API time series data: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500


@mcp_bp.route('/api/response-time-distribution', methods=['GET'])
def api_response_time_distribution():
    """
    API endpoint to retrieve distribution of API call response times.
    
    This endpoint returns JSON with the distribution of API calls by response time buckets,
    which can be used to analyze performance and identify slow calls.
    
    Query Parameters:
    - timeframe: Filter by time period (day, week, month, all)
    - service: Filter by service name (optional)
    """
    try:
        from models import APICallLog, db
        from sqlalchemy import func, case
        
        # Parse query parameters
        timeframe = request.args.get('timeframe', 'week')
        service_filter = request.args.get('service')
        
        # Build query
        query = db.session.query(APICallLog)
        
        # Apply timeframe filter
        if timeframe == 'day':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=1))
            )
        elif timeframe == 'week':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(weeks=1))
            )
        elif timeframe == 'month':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=30))
            )
        
        # Apply service filter if provided
        if service_filter:
            query = query.filter(APICallLog.service == service_filter)
        
        # Get all response times
        calls = query.all()
        
        # Define buckets for response time distribution
        buckets = {
            'under_500ms': 0,
            '500ms_to_1s': 0,
            '1s_to_2s': 0,
            '2s_to_5s': 0,
            'over_5s': 0
        }
        
        # Count calls in each bucket
        for call in calls:
            duration = call.duration_ms
            if duration is None:
                continue
                
            if duration < 500:
                buckets['under_500ms'] += 1
            elif duration < 1000:
                buckets['500ms_to_1s'] += 1
            elif duration < 2000:
                buckets['1s_to_2s'] += 1
            elif duration < 5000:
                buckets['2s_to_5s'] += 1
            else:
                buckets['over_5s'] += 1
        
        # Calculate total calls and percentages
        total_calls = sum(buckets.values())
        percentages = {}
        
        if total_calls > 0:
            for key, value in buckets.items():
                percentages[key] = round((value / total_calls) * 100, 2)
        else:
            for key in buckets.keys():
                percentages[key] = 0
        
        # Return JSON response
        return jsonify({
            'buckets': buckets,
            'percentages': percentages,
            'total_calls': total_calls,
            'timeframe': timeframe,
            'service': service_filter or 'all',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving response time distribution: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500


@mcp_bp.route('/api/historical-calls', methods=['GET'])
def api_historical_calls():
    """
    API endpoint to retrieve historical API call data.
    
    This endpoint returns JSON with a list of recent API calls from the database,
    with pagination support.
    
    Query Parameters:
    - timeframe: Filter by time period (day, week, month, all)
    - page: Page number for pagination (default: 1)
    - per_page: Number of records per page (default: 10)
    - service: Filter by service name (optional)
    - success: Filter by success status (true/false, optional)
    """
    try:
        from models import APICallLog, db
        
        # Parse query parameters
        timeframe = request.args.get('timeframe', 'all')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        service_filter = request.args.get('service')
        success_filter = request.args.get('success')
        
        # Build query
        query = db.session.query(APICallLog)
        
        # Apply timeframe filter
        if timeframe == 'day':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=1))
            )
        elif timeframe == 'week':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(weeks=1))
            )
        elif timeframe == 'month':
            query = query.filter(
                APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=30))
            )
        
        # Apply service filter if provided
        if service_filter:
            query = query.filter(APICallLog.service == service_filter)
        
        # Apply success filter if provided
        if success_filter is not None:
            success_bool = success_filter.lower() == 'true'
            query = query.filter(APICallLog.success == success_bool)
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(APICallLog.timestamp.desc())
        
        # Paginate results
        total_count = query.count()
        calls = query.limit(per_page).offset((page - 1) * per_page).all()
        
        # Format results
        results = []
        for call in calls:
            # Create a result dictionary with all available fields
            result = {
                'id': call.id,
                'timestamp': call.timestamp.isoformat(),
                'service': call.service,
                'method': call.method,
                'duration_ms': call.duration_ms,
                'success': call.success,
                'error_message': call.error_message,
            }
            
            # Add additional fields if they exist
            if hasattr(call, 'details'):
                result['details'] = call.details
            elif hasattr(call, 'response_summary'):
                result['details'] = call.response_summary
            
            results.append(result)
        
        # Build pagination metadata
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        # Return JSON response
        return jsonify({
            'calls': results,
            'meta': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving historical API calls: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500

@mcp_bp.route('/insights', methods=['GET'])
def insights():
    """
    Render the MCP insights page with AI-powered analysis.
    
    This page displays AI-generated insights about the tax data,
    system statistics, and recent activity.
    """
    try:
        # Get database counts using schema utility
        counts = get_table_counts()
        property_count = counts.get('property', 0)
        tax_code_count = counts.get('tax_code', 0)
        district_count = counts.get('tax_district', 0)
        
        # Get recent import and export logs using schema utilities
        recent_imports = get_recent_import_logs(limit=5)
        recent_exports = get_recent_export_logs(limit=5)
        
        # Get tax code summary using schema utility
        tax_summary = get_tax_code_summary(limit=10)
        
        # Get tax codes for AI insights
        tax_codes = []
        try:
            tax_codes = TaxCode.query.all()
        except Exception as e:
            logger.error(f"Error getting tax codes for insights: {str(e)}")
        
        # Generate AI insights
        mcp_insights = generate_mcp_insights(tax_codes if 'tax_codes' in locals() else [])
        
        # Render template with data
        return render_template('mcp_insights_new.html',
                            property_count=property_count,
                            tax_code_count=tax_code_count,
                            district_count=district_count,
                            recent_imports=recent_imports,
                            recent_exports=recent_exports,
                            tax_summary=tax_summary,
                            mcp_insights=mcp_insights)
    
    except Exception as e:
        logger.error(f"Error rendering MCP insights: {str(e)}")
        # Return a basic error view
        error_message = sanitize_html(str(e))
        return render_template('mcp_insights_new.html', 
                             error=True, 
                             error_message=error_message,
                             property_count=0,
                             tax_code_count=0,
                             district_count=0,
                             recent_imports=[],
                             recent_exports=[],
                             tax_summary=[],
                             mcp_insights={
                                'narrative': 'Error generating insights.',
                                'data': {
                                    'recommendations': {},
                                    'avg_assessed_value': 'N/A'
                                }
                            })


def generate_mcp_insights(tax_codes):
    """
    Generate AI-powered insights about the tax data.
    
    Args:
        tax_codes: List of TaxCode objects
        
    Returns:
        Dictionary with narrative and data for the insights page
    """
    # Check if Anthropic API key is configured
    key_status = check_api_key_status()
    status = key_status.get('status')
    
    if status == 'valid':
        api_key_status = "configured"
    elif status == 'no_credits':
        api_key_status = "no_credits"
    else:
        api_key_status = "missing"
    
    # Default values if API is not available
    default_insights = {
        'narrative': sanitize_html(
            "<p>MCP insights are generated by analyzing your property tax data with "
            "Anthropic's Claude 3.5 Sonnet model.</p>"
        ),
        'data': {
            'recommendations': {
                'Configure API': 'Set up your Anthropic API key to enable AI insights.',
                'Import Data': 'Add property and tax code data for better analysis.',
                'Explore Reports': 'Review existing reports for manual insights.'
            },
            'avg_assessed_value': 'N/A',
            'api_status': api_key_status,
            'trends': [],
            'anomalies': [],
            'impacts': []
        }
    }
    
    # Add appropriate message based on API key status
    if api_key_status == "missing":
        default_insights['narrative'] += sanitize_html(
            "<div class='alert alert-warning mt-3'>"
            "<i class='bi bi-exclamation-triangle me-2'></i>"
            "<strong>API Key Required:</strong> Configure your ANTHROPIC_API_KEY "
            "environment variable to enable AI-powered insights."
            "<div class='mt-2'>"
            "<a href='https://console.anthropic.com/account/keys' "
            "class='btn btn-sm btn-outline-primary me-2' target='_blank'>"
            "<i class='bi bi-key me-1'></i>Get Anthropic API Key</a>"
            "<button type='button' class='btn btn-sm btn-outline-success' "
            "data-bs-toggle='modal' data-bs-target='#apiKeyModal'>"
            "<i class='bi bi-gear me-1'></i>Configure API Key</button>"
            "</div>"
            "</div>"
        )
    elif api_key_status == "no_credits":
        default_insights['narrative'] += sanitize_html(
            "<div class='alert alert-danger mt-3'>"
            "<i class='bi bi-exclamation-triangle me-2'></i>"
            "<strong>Credit Balance Issue:</strong> Your Anthropic API key is valid, "
            "but has insufficient credits. Add credits to your account or configure a different key."
            "<div class='mt-2'>"
            "<a href='https://console.anthropic.com/settings/billing' "
            "class='btn btn-sm btn-outline-danger me-2' target='_blank'>"
            "<i class='bi bi-credit-card me-1'></i>Add Credits</a>"
            "<button type='button' class='btn btn-sm btn-outline-primary' "
            "data-bs-toggle='modal' data-bs-target='#apiKeyModal'>"
            "<i class='bi bi-key me-1'></i>Update API Key</button>"
            "</div>"
            "</div>"
        )
    
    # Get average assessed value using schema utility
    avg_value = get_property_assessed_value_avg()
    if avg_value:
        default_insights['data']['avg_assessed_value'] = "${:,.2f}".format(avg_value)
    else:
        default_insights['data']['avg_assessed_value'] = "N/A"
    
    # Generate enhanced fallback insights based on available data
    # These fallback insights will be used if the API is unavailable or lacks credits
    if api_key_status != "configured":
        # Enhanced fallback recommendations based on database state
        enhanced_fallback = generate_enhanced_fallback_insights(tax_codes)
        if enhanced_fallback:
            default_insights['data']['recommendations'] = enhanced_fallback['recommendations']
            default_insights['data']['trends'] = enhanced_fallback['trends']
            default_insights['data']['anomalies'] = enhanced_fallback['anomalies']
            default_insights['data']['impacts'] = enhanced_fallback['impacts']
            
            # Add limited narrative based on data analysis
            if enhanced_fallback.get('narrative'):
                default_insights['narrative'] += sanitize_html(enhanced_fallback['narrative'])
    
    try:
        # Check if we can access the Claude service
        claude_service = get_claude_service()
        if not claude_service:
            logger.warning("Claude service not available")
            return default_insights
        
        # Prepare data for analysis
        tax_code_data = []
        for tc in tax_codes:
            try:
                # Use a try/except block to handle potential attribute errors
                tax_code_data.append({
                    'code': getattr(tc, 'tax_code', 'Unknown'),  # Using tax_code attribute
                    'total_assessed_value': getattr(tc, 'total_assessed_value', 0),
                    'effective_tax_rate': getattr(tc, 'effective_tax_rate', 0),
                    'total_levy_amount': getattr(tc, 'total_levy_amount', 0),
                    'district_id': getattr(tc, 'tax_district_id', None),
                })
            except Exception as e:
                logger.error(f"Error processing tax code data: {str(e)}")
                # Skip this tax code if there's an error
                continue
        
        # Get historical data
        historical_data = []  # In a real app, we'd get this from a history table
        
        # If we have enough data, generate insights
        if len(tax_code_data) > 0:
            insights = claude_service.generate_levy_insights(tax_code_data, historical_data)
            
            # Format the narrative
            narrative = sanitize_html(
                "<p>Based on analysis of your property tax data, here are some key insights:</p>"
                "<ul>"
            )
            
            # Add trends
            if 'trends' in insights and insights['trends']:
                for trend in insights['trends'][:3]:  # Limit to top 3
                    narrative += f"<li>{trend}</li>"
            
            # Add anomalies
            if 'anomalies' in insights and insights['anomalies']:
                for anomaly in insights['anomalies'][:2]:  # Limit to top 2
                    narrative += f"<li>{anomaly}</li>"
            
            narrative += "</ul>"
            
            # Format recommendations
            recommendations = {}
            if 'recommendations' in insights and insights['recommendations']:
                for i, rec in enumerate(insights['recommendations'][:3], 1):  # Limit to top 3
                    recommendations[f"Recommendation {i}"] = rec
            else:
                recommendations = default_insights['data']['recommendations']
            
            # Return the insights
            return {
                'narrative': narrative,
                'data': {
                    'recommendations': recommendations,
                    'avg_assessed_value': default_insights['data']['avg_assessed_value'],
                    'api_status': api_key_status,
                    'trends': insights.get('trends', []),
                    'anomalies': insights.get('anomalies', []),
                    'impacts': insights.get('impacts', [])
                }
            }
        else:
            logger.warning("Not enough data for meaningful insights")
            return default_insights
    
    except Exception as e:
        logger.error(f"Error generating MCP insights: {str(e)}")
        return default_insights

def generate_enhanced_fallback_insights(tax_codes):
    """
    Generate basic insights without using the AI API, based on available data.
    
    Args:
        tax_codes: List of TaxCode objects
        
    Returns:
        Dictionary with enhanced insights based on database state and statistics
    """
    try:
        if not tax_codes or len(tax_codes) == 0:
            return None
            
        # Process tax codes to calculate basic statistics
        total_assessed_values = []
        tax_rates = []
        levy_amounts = []
        
        for tc in tax_codes:
            try:
                total_assessed_value = getattr(tc, 'total_assessed_value', 0)
                effective_tax_rate = getattr(tc, 'effective_tax_rate', 0)
                total_levy_amount = getattr(tc, 'total_levy_amount', 0)
                
                if total_assessed_value:
                    total_assessed_values.append(total_assessed_value)
                if effective_tax_rate:
                    tax_rates.append(effective_tax_rate)
                if total_levy_amount:
                    levy_amounts.append(total_levy_amount)
            except Exception:
                continue
        
        # Generate basic trends based on statistics
        trends = []
        anomalies = []
        impacts = []
        recommendations = {}
        
        # Calculate statistics if we have enough data
        if total_assessed_values:
            avg_assessed = sum(total_assessed_values) / len(total_assessed_values)
            max_assessed = max(total_assessed_values)
            min_assessed = min(total_assessed_values)
            
            trends.append(f"Average assessed property value is ${avg_assessed:,.2f}")
            
            if max_assessed > avg_assessed * 2:
                anomalies.append(f"Highest property assessment (${max_assessed:,.2f}) is significantly above average")
            
            if tax_rates:
                avg_rate = sum(tax_rates) / len(tax_rates)
                trends.append(f"Average effective tax rate is {avg_rate:.4f}")
                
                # Find any outliers in tax rates
                outlier_threshold = avg_rate * 1.5
                outliers = [rate for rate in tax_rates if rate > outlier_threshold]
                if outliers:
                    anomalies.append(f"Some tax rates exceed {outlier_threshold:.4f}, which is 50% above the average")
            
            if levy_amounts:
                total_levy = sum(levy_amounts)
                impacts.append(f"Total levy amount across all properties is ${total_levy:,.2f}")
        
        # Generate recommendations based on the data
        recommendations = {
            "Review Tax Data": "Analyze the distribution of property values to identify potential assessment issues",
            "Rate Optimization": "Consider adjusting tax rates based on property value distribution for more equitable taxation",
            "Data Completeness": "Ensure all property records have complete assessment information for accurate calculations"
        }
        
        # Create a narrative based on findings
        narrative = ""
        if trends or anomalies or impacts:
            narrative = "<p>Based on basic statistical analysis of your property tax data:</p><ul>"
            
            for trend in trends[:2]:
                narrative += f"<li>{trend}</li>"
            
            for anomaly in anomalies[:1]:
                narrative += f"<li>{anomaly}</li>"
            
            for impact in impacts[:1]:
                narrative += f"<li>{impact}</li>"
                
            narrative += "</ul>"
            
            # Add note about limited analysis
            narrative += "<p><em>Note: These insights are based on basic statistical analysis. " + \
                        "For more comprehensive insights, please configure an Anthropic API key " + \
                        "with sufficient credits.</em></p>"
        
        return {
            'recommendations': recommendations,
            'trends': trends,
            'anomalies': anomalies,
            'impacts': impacts,
            'narrative': narrative
        }
    
    except Exception as e:
        logger.error(f"Error generating enhanced fallback insights: {str(e)}")
        return None


@mcp_bp.route('/api/statistics', methods=['GET'])
def api_statistics():
    """
    API endpoint to retrieve API call statistics.
    
    This endpoint returns JSON with statistics about API calls, including
    success rates, error rates, and performance metrics.
    """
    try:
        # Check if we should include historical data (from database)
        include_historical = request.args.get('historical', 'false').lower() == 'true'
        timeframe = request.args.get('timeframe', 'session')  # session, day, week, month, all
        
        # Get current session API statistics from the in-memory tracker
        current_stats = get_api_statistics()
        
        # Add timestamp to the response
        statistics = current_stats.copy()
        statistics['timestamp'] = datetime.utcnow().isoformat()
        
        # If historical data is requested, query the database
        if include_historical and timeframe != 'session':
            from models import APICallLog, db
            from sqlalchemy import func
            
            # Build query based on timeframe
            query = db.session.query(
                func.count().label('total'),
                func.sum(case((APICallLog.success == True, 1), else_=0)).label('success_count'),
                func.sum(case((APICallLog.success == False, 1), else_=0)).label('error_count'),
                func.avg(APICallLog.duration_ms).label('avg_duration'),
                func.sum(APICallLog.duration_ms).label('total_duration')
            )
            
            # Apply timeframe filter
            if timeframe == 'day':
                query = query.filter(
                    APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=1))
                )
            elif timeframe == 'week':
                query = query.filter(
                    APICallLog.timestamp >= (datetime.utcnow() - timedelta(weeks=1))
                )
            elif timeframe == 'month':
                query = query.filter(
                    APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=30))
                )
            
            # Execute query
            result = query.first()
            
            # Get service breakdown
            service_query = db.session.query(
                APICallLog.service,
                func.count().label('count')
            )
            
            # Apply same timeframe filter
            if timeframe == 'day':
                service_query = service_query.filter(
                    APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=1))
                )
            elif timeframe == 'week':
                service_query = service_query.filter(
                    APICallLog.timestamp >= (datetime.utcnow() - timedelta(weeks=1))
                )
            elif timeframe == 'month':
                service_query = service_query.filter(
                    APICallLog.timestamp >= (datetime.utcnow() - timedelta(days=30))
                )
            
            # Group by service and execute
            service_query = service_query.group_by(APICallLog.service)
            service_counts = {row.service: row.count for row in service_query.all()}
            
            # Only update stats if we have historical data
            if result.total:
                # Calculate statistics from database results
                historical_stats = {
                    'total_calls': result.total or 0,
                    'success_count': result.success_count or 0,
                    'error_count': result.error_count or 0,
                    'avg_duration_ms': round(result.avg_duration or 0, 2),
                    'total_duration_ms': round(result.total_duration or 0, 2),
                    'calls_by_service': service_counts,
                    'source': f'historical_{timeframe}',
                    'timeframe': timeframe
                }
                
                # Calculate error rate
                if historical_stats['total_calls'] > 0:
                    historical_stats['error_rate_percent'] = round(
                        (historical_stats['error_count'] / historical_stats['total_calls']) * 100, 2
                    )
                else:
                    historical_stats['error_rate_percent'] = 0
                
                # Replace memory-only stats with historical stats
                statistics.update(historical_stats)
        
        # Add human-readable summaries for the dashboard
        if statistics['total_calls'] > 0:
            statistics['summary'] = {
                'status': 'active' if statistics['error_rate_percent'] < 25 else 'degraded',
                'message': (f"{statistics['total_calls']} API calls tracked with "
                           f"{statistics['error_rate_percent']}% error rate"),
                'avg_latency': f"{statistics['avg_duration_ms']:.1f}ms"
            }
        else:
            statistics['summary'] = {
                'status': 'inactive',
                'message': "No API calls have been tracked yet",
                'avg_latency': "N/A"
            }
        
        return jsonify(statistics)
    except Exception as e:
        logger.error(f"Error retrieving API statistics: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


def init_mcp_routes(app):
    """Register MCP routes with the Flask app."""
    app.register_blueprint(mcp_bp)
    logger.info("MCP routes initialized")