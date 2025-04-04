"""
Routes for MCP (Model Content Protocol) insights and integration.

This module provides routes for the MCP insights page and related functionality.
It integrates with the Anthropic Claude API to provide AI-powered insights.
"""

import json
import logging
import os
from datetime import datetime
from flask import Blueprint, render_template, current_app, request, jsonify
from sqlalchemy import desc, func

from app import db
from models import TaxDistrict, TaxCode, Property, ImportLog, ExportLog
from utils.anthropic_utils import get_claude_service, check_api_key_status
from utils.html_sanitizer import sanitize_html
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
        return jsonify(key_status)
    except Exception as e:
        logger.error(f"Error checking API key status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
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
            'api_status': api_key_status
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


def init_mcp_routes(app):
    """Register MCP routes with the Flask app."""
    app.register_blueprint(mcp_bp)
    logger.info("MCP routes initialized")