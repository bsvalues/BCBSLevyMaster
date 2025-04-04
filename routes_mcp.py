"""
Routes for MCP (Model Content Protocol) insights and integration.

This module provides routes for the MCP insights page and related functionality.
It integrates with the Anthropic Claude API to provide AI-powered insights.
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, current_app, request, jsonify
from sqlalchemy import desc, func

from app import db
from models import TaxDistrict, TaxCode, Property, ImportLog, ExportLog
from utils.anthropic_utils import get_claude_service
from utils.html_sanitizer import sanitize_html

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp')

@mcp_bp.route('/insights', methods=['GET'])
def insights():
    """
    Render the MCP insights page with AI-powered analysis.
    
    This page displays AI-generated insights about the tax data,
    system statistics, and recent activity.
    """
    try:
        # Get database counts safely
        try:
            property_count = db.session.query(func.count(Property.id)).scalar() or 0
            tax_code_count = db.session.query(func.count(TaxCode.id)).scalar() or 0 
            district_count = db.session.query(func.count(TaxDistrict.id)).scalar() or 0
        except Exception as e:
            logger.error(f"Error getting database counts: {str(e)}")
            property_count = 0
            tax_code_count = 0
            district_count = 0
        
        # Get recent import and export logs
        try:
            # Use actual column names from database
            recent_imports = db.session.query(ImportLog).order_by(desc(ImportLog.id)).limit(5).all()
            recent_exports = db.session.query(ExportLog).order_by(desc(ExportLog.export_date)).limit(5).all()
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
            recent_imports = []
            recent_exports = []
        
        # Get tax code summary for distribution visualization
        tax_summary = []
        try:
            tax_codes = TaxCode.query.all()
            total_assessed_value = sum(tc.total_assessed_value or 0 for tc in tax_codes)
            
            if total_assessed_value > 0:
                for tc in tax_codes:
                    if tc.total_assessed_value:
                        percent = (tc.total_assessed_value / total_assessed_value) * 100
                        tax_summary.append({
                            'code': tc.tax_code,  # Using tax_code instead of code
                            'assessed_value': tc.total_assessed_value,
                            'percent_of_total': percent
                        })
                
                # Sort by assessed value, descending
                tax_summary = sorted(tax_summary, key=lambda x: x['assessed_value'], reverse=True)
                
                # Limit to top 10
                tax_summary = tax_summary[:10]
        except Exception as e:
            logger.error(f"Error getting tax summary: {str(e)}")
            tax_codes = []
        
        # Generate AI insights
        mcp_insights = generate_mcp_insights(tax_codes if 'tax_codes' in locals() else [])
        
        # Render template with data
        return render_template('mcp_insights.html',
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
        return render_template('mcp_insights.html', 
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
    # Default values if API is not available
    default_insights = {
        'narrative': sanitize_html(
            "<p>MCP insights are generated by analyzing your property tax data with "
            "Anthropic's Claude 3.5 Sonnet model. Configure your ANTHROPIC_API_KEY "
            "environment variable to enable AI-powered insights.</p>"
        ),
        'data': {
            'recommendations': {
                'Configure API': 'Set up your Anthropic API key to enable AI insights.',
                'Import Data': 'Add property and tax code data for better analysis.',
                'Explore Reports': 'Review existing reports for manual insights.'
            },
            'avg_assessed_value': 'N/A'
        }
    }
    
    # Get average assessed value
    try:
        avg_value = db.session.query(func.avg(Property.assessed_value)).scalar()
        if avg_value:
            default_insights['data']['avg_assessed_value'] = "${:,.2f}".format(avg_value)
    except Exception as e:
        logger.warning(f"Could not get average assessed value: {str(e)}")
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
            tax_code_data.append({
                'code': tc.tax_code,  # Using tax_code attribute
                'total_assessed_value': tc.total_assessed_value,
                'levy_rate': tc.levy_rate,
                'tax_district_name': tc.tax_district.name if hasattr(tc, 'tax_district') and tc.tax_district else 'Unknown',
                'effective_tax_rate': tc.effective_tax_rate
            })
        
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