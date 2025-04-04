"""
Levy calculator routes for the Levy Calculation System.

This module provides routes for calculating property tax levies,
including statutory limits, distribution calculations, and what-if scenarios.
"""

import logging
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_, or_

from app import db
from models import (
    TaxDistrict, TaxCode, Property, LevyRate, LevyScenario,
    ComplianceIssue, User, AuditLog
)

# Create blueprint
levy_calculator_bp = Blueprint('levy_calculator', __name__, url_prefix='/levy-calculator')

# Configure logger
logger = logging.getLogger(__name__)


@levy_calculator_bp.route('/')
@login_required
def index():
    """
    Render the levy calculator landing page.
    
    Returns:
        Rendered template for the levy calculator
    """
    # Get current year
    current_year = datetime.now().year
    
    # Get available tax districts for calculation
    districts = TaxDistrict.query.filter_by(year=current_year).order_by(TaxDistrict.district_name).all()
    
    # Get recent calculations for this user
    recent_scenarios = LevyScenario.query.filter_by(
        user_id=current_user.id
    ).order_by(
        LevyScenario.updated_at.desc()
    ).limit(5).all()
    
    return render_template(
        'levy_calculator.html',
        districts=districts,
        recent_scenarios=recent_scenarios,
        current_year=current_year
    )


@levy_calculator_bp.route('/district/<int:district_id>')
@login_required
def district_rates(district_id):
    """
    Get levy rate details for a specific district.
    
    Args:
        district_id: The tax district ID
        
    Returns:
        JSON response with district rate details
    """
    try:
        # Get district
        district = TaxDistrict.query.get_or_404(district_id)
        
        # Get levy rates for this district
        levy_rates = LevyRate.query.filter_by(
            tax_district_id=district.id
        ).order_by(
            LevyRate.year.desc(), 
            LevyRate.is_final.desc()
        ).all()
        
        # Format rates for response
        rates_data = []
        for rate in levy_rates:
            rates_data.append({
                'id': rate.id,
                'year': rate.year,
                'levy_rate': float(rate.levy_rate),
                'levy_amount': float(rate.levy_amount),
                'assessed_value': float(rate.assessed_value_basis),
                'is_final': rate.is_final,
                'created_at': rate.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Get tax codes for this district
        tax_codes = TaxCode.query.filter_by(
            tax_district_id=district.id, 
            year=district.year
        ).all()
        
        # Count properties in this district
        property_count = Property.query.join(
            TaxCode, Property.tax_code_id == TaxCode.id
        ).filter(
            TaxCode.tax_district_id == district.id,
            Property.year == district.year
        ).count()
        
        # Format tax district data
        district_data = {
            'id': district.id,
            'name': district.district_name,
            'code': district.district_code,
            'type': district.district_type,
            'county': district.county,
            'statutory_limit': float(district.statutory_limit) if district.statutory_limit else None,
            'year': district.year,
            'tax_code_count': len(tax_codes),
            'property_count': property_count
        }
        
        return jsonify({
            'status': 'success',
            'district': district_data,
            'levy_rates': rates_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching district rates: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@levy_calculator_bp.route('/calculate', methods=['POST'])
@login_required
def calculate_levy():
    """
    Calculate levy rate based on provided parameters.
    
    Returns:
        JSON response with calculation results
    """
    try:
        # Get form data
        district_id = request.form.get('district_id', type=int)
        year = request.form.get('year', datetime.now().year, type=int)
        levy_amount = request.form.get('levy_amount', type=float)
        
        if not district_id or not levy_amount:
            return jsonify({
                'status': 'error',
                'message': 'District ID and levy amount are required'
            }), 400
        
        # Get district
        district = TaxDistrict.query.get_or_404(district_id)
        
        # Get total assessed value for this district
        total_assessed_value = db.session.query(
            func.sum(Property.assessed_value)
        ).join(
            TaxCode, Property.tax_code_id == TaxCode.id
        ).filter(
            TaxCode.tax_district_id == district.id,
            Property.year == year,
            Property.tax_exempt == False
        ).scalar() or 0
        
        # If no assessed value, check tax code total
        if total_assessed_value == 0:
            total_assessed_value = db.session.query(
                func.sum(TaxCode.total_assessed_value)
            ).filter(
                TaxCode.tax_district_id == district.id,
                TaxCode.year == year
            ).scalar() or 0
        
        if total_assessed_value == 0:
            return jsonify({
                'status': 'error',
                'message': 'No assessed value found for this district and year'
            }), 400
        
        # Calculate levy rate per $1,000 of assessed value
        levy_rate = (levy_amount / total_assessed_value) * 1000
        
        # Check for statutory limit
        statutory_limit = district.statutory_limit
        compliance_issues = []
        
        if statutory_limit and levy_rate > statutory_limit:
            compliance_issues.append({
                'type': 'OVER_LIMIT',
                'message': f'Calculated rate ({levy_rate:.4f}) exceeds statutory limit of {statutory_limit:.4f}',
                'severity': 'HIGH'
            })
            
            # Adjust to statutory limit
            adjusted_rate = statutory_limit
            adjusted_amount = (adjusted_rate * total_assessed_value) / 1000
            
            adjustment_data = {
                'original_rate': levy_rate,
                'adjusted_rate': adjusted_rate,
                'original_amount': levy_amount,
                'adjusted_amount': adjusted_amount,
                'difference': levy_amount - adjusted_amount
            }
        else:
            adjustment_data = None
        
        # Result data
        result = {
            'district_id': district_id,
            'district_name': district.district_name,
            'year': year,
            'levy_amount': levy_amount,
            'assessed_value': total_assessed_value,
            'levy_rate': levy_rate,
            'statutory_limit': statutory_limit,
            'compliance_issues': compliance_issues,
            'adjustment_data': adjustment_data
        }
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error calculating levy: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@levy_calculator_bp.route('/save-scenario', methods=['POST'])
@login_required
def save_scenario():
    """
    Save a levy calculation scenario.
    
    Returns:
        JSON response with saved scenario details
    """
    try:
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description', '')
        district_id = request.form.get('district_id', type=int)
        base_year = request.form.get('base_year', datetime.now().year, type=int)
        target_year = request.form.get('target_year', base_year, type=int)
        levy_amount = request.form.get('levy_amount', type=float)
        assessed_value_change = request.form.get('assessed_value_change', 0, type=float)
        new_construction_value = request.form.get('new_construction_value', 0, type=float)
        annexation_value = request.form.get('annexation_value', 0, type=float)
        is_public = request.form.get('is_public') == 'true'
        
        if not name or not district_id or not levy_amount:
            return jsonify({
                'status': 'error',
                'message': 'Name, district ID, and levy amount are required'
            }), 400
        
        # Get district
        district = TaxDistrict.query.get_or_404(district_id)
        
        # Get total assessed value for this district/year
        total_assessed_value = db.session.query(
            func.sum(Property.assessed_value)
        ).join(
            TaxCode, Property.tax_code_id == TaxCode.id
        ).filter(
            TaxCode.tax_district_id == district.id,
            Property.year == base_year,
            Property.tax_exempt == False
        ).scalar() or 0
        
        # If no assessed value, check tax code total
        if total_assessed_value == 0:
            total_assessed_value = db.session.query(
                func.sum(TaxCode.total_assessed_value)
            ).filter(
                TaxCode.tax_district_id == district.id,
                TaxCode.year == base_year
            ).scalar() or 0
        
        # Calculate levy rate per $1,000 of assessed value
        levy_rate = (levy_amount / total_assessed_value) * 1000
        
        # Create or update scenario
        scenario_id = request.form.get('scenario_id', type=int)
        if scenario_id:
            # Update existing scenario
            scenario = LevyScenario.query.get(scenario_id)
            if not scenario or scenario.user_id != current_user.id:
                return jsonify({
                    'status': 'error',
                    'message': 'Scenario not found or you do not have permission to update it'
                }), 404
        else:
            # Create new scenario
            scenario = LevyScenario(
                user_id=current_user.id,
                year=base_year,
                created_by_id=current_user.id,
                updated_by_id=current_user.id
            )
        
        # Update scenario fields
        scenario.name = name
        scenario.description = description
        scenario.tax_district_id = district_id
        scenario.base_year = base_year
        scenario.target_year = target_year
        scenario.levy_amount = levy_amount
        scenario.assessed_value_change = assessed_value_change / 100 if assessed_value_change else 0  # Convert percentage to decimal
        scenario.new_construction_value = new_construction_value
        scenario.annexation_value = annexation_value
        scenario.is_public = is_public
        scenario.result_levy_rate = levy_rate
        scenario.result_levy_amount = levy_amount
        scenario.status = 'FINAL'
        scenario.updated_by_id = current_user.id
        
        # Save to database
        db.session.add(scenario)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'scenario_id': scenario.id,
            'message': 'Scenario saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving scenario: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@levy_calculator_bp.route('/scenario/<int:scenario_id>')
@login_required
def get_scenario(scenario_id):
    """
    Get details for a specific levy scenario.
    
    Args:
        scenario_id: The levy scenario ID
        
    Returns:
        JSON response with scenario details
    """
    try:
        # Get scenario
        scenario = LevyScenario.query.get_or_404(scenario_id)
        
        # Check permissions
        if not scenario.is_public and scenario.user_id != current_user.id:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to view this scenario'
            }), 403
        
        # Get district
        district = TaxDistrict.query.get(scenario.tax_district_id)
        
        # Format for response
        scenario_data = {
            'id': scenario.id,
            'name': scenario.name,
            'description': scenario.description,
            'user_id': scenario.user_id,
            'user_name': scenario.user.username if scenario.user else None,
            'district_id': scenario.tax_district_id,
            'district_name': district.district_name if district else None,
            'base_year': scenario.base_year,
            'target_year': scenario.target_year,
            'levy_amount': float(scenario.levy_amount),
            'assessed_value_change': float(scenario.assessed_value_change) * 100,  # Convert back to percentage
            'new_construction_value': float(scenario.new_construction_value),
            'annexation_value': float(scenario.annexation_value),
            'is_public': scenario.is_public,
            'result_levy_rate': float(scenario.result_levy_rate),
            'result_levy_amount': float(scenario.result_levy_amount),
            'status': scenario.status,
            'created_at': scenario.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': scenario.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({
            'status': 'success',
            'scenario': scenario_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching scenario: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@levy_calculator_bp.route('/scenarios')
@login_required
def list_scenarios():
    """
    List levy calculation scenarios.
    
    Returns:
        JSON response with scenarios list
    """
    try:
        # Get query parameters
        year = request.args.get('year', datetime.now().year, type=int)
        district_id = request.args.get('district_id', type=int)
        
        # Build query
        query = LevyScenario.query.filter(
            or_(
                LevyScenario.user_id == current_user.id,
                LevyScenario.is_public == True
            )
        )
        
        # Apply filters
        if year:
            query = query.filter(LevyScenario.target_year == year)
        
        if district_id:
            query = query.filter(LevyScenario.tax_district_id == district_id)
        
        # Execute query with sorting
        scenarios = query.order_by(LevyScenario.updated_at.desc()).all()
        
        # Format response
        scenario_list = []
        for scenario in scenarios:
            district = TaxDistrict.query.get(scenario.tax_district_id)
            scenario_list.append({
                'id': scenario.id,
                'name': scenario.name,
                'description': scenario.description,
                'district_id': scenario.tax_district_id,
                'district_name': district.district_name if district else None,
                'base_year': scenario.base_year,
                'target_year': scenario.target_year,
                'result_levy_rate': float(scenario.result_levy_rate),
                'result_levy_amount': float(scenario.result_levy_amount),
                'is_public': scenario.is_public,
                'status': scenario.status,
                'user_id': scenario.user_id,
                'user_name': scenario.user.username if scenario.user else None,
                'updated_at': scenario.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'status': 'success',
            'scenarios': scenario_list
        })
        
    except Exception as e:
        logger.error(f"Error listing scenarios: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@levy_calculator_bp.route('/delete-scenario/<int:scenario_id>', methods=['POST'])
@login_required
def delete_scenario(scenario_id):
    """
    Delete a levy calculation scenario.
    
    Args:
        scenario_id: The scenario ID to delete
        
    Returns:
        JSON response with deletion status
    """
    try:
        # Get scenario
        scenario = LevyScenario.query.get_or_404(scenario_id)
        
        # Check ownership
        if scenario.user_id != current_user.id:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to delete this scenario'
            }), 403
        
        # Delete scenario
        db.session.delete(scenario)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Scenario deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting scenario: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@levy_calculator_bp.route('/bill-impact')
@login_required
def bill_impact_calculator():
    """
    Render the bill impact calculator page.
    
    This calculator shows how levy changes impact individual property tax bills.
    
    Returns:
        Rendered template for the bill impact calculator
    """
    # Get current year
    current_year = datetime.now().year
    
    # Get available tax districts
    districts = TaxDistrict.query.filter_by(year=current_year).order_by(TaxDistrict.district_name).all()
    
    return render_template(
        'bill_impact_calculator.html',
        districts=districts,
        current_year=current_year
    )


@levy_calculator_bp.route('/tax-codes/<int:district_id>')
@login_required
def get_tax_codes(district_id):
    """
    Get tax codes for a specific district.
    
    Args:
        district_id: The tax district ID
        
    Returns:
        JSON response with tax codes
    """
    try:
        # Get district
        district = TaxDistrict.query.get_or_404(district_id)
        
        # Get tax codes
        tax_codes = TaxCode.query.filter_by(
            tax_district_id=district.id,
            year=district.year
        ).order_by(TaxCode.tax_code).all()
        
        # Format response
        tax_code_list = []
        for code in tax_codes:
            # Get property count
            property_count = Property.query.filter_by(
                tax_code_id=code.id,
                year=code.year
            ).count()
            
            tax_code_list.append({
                'id': code.id,
                'tax_code': code.tax_code,
                'description': code.description,
                'total_assessed_value': float(code.total_assessed_value),
                'total_levy_amount': float(code.total_levy_amount),
                'effective_tax_rate': float(code.effective_tax_rate),
                'property_count': property_count
            })
        
        return jsonify({
            'status': 'success',
            'tax_codes': tax_code_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching tax codes: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@levy_calculator_bp.route('/calculate-bill-impact', methods=['POST'])
@login_required
def calculate_bill_impact():
    """
    Calculate the impact of levy changes on individual property tax bills.
    
    Returns:
        JSON response with bill impact calculation results
    """
    try:
        # Get form data
        district_id = request.form.get('district_id', type=int)
        tax_code_id = request.form.get('tax_code_id', type=int)
        current_year = request.form.get('current_year', datetime.now().year, type=int)
        property_value = request.form.get('property_value', type=float)
        current_levy_rate = request.form.get('current_levy_rate', type=float)
        proposed_levy_rate = request.form.get('proposed_levy_rate', type=float)
        
        if not district_id or not property_value or current_levy_rate is None or proposed_levy_rate is None:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters'
            }), 400
        
        # Calculate current and proposed tax bills
        current_tax = (property_value * current_levy_rate) / 1000
        proposed_tax = (property_value * proposed_levy_rate) / 1000
        
        # Calculate differences
        difference = proposed_tax - current_tax
        percentage_change = (difference / current_tax) * 100 if current_tax > 0 else 0
        
        # Sample properties if tax code provided
        sample_properties = []
        if tax_code_id:
            # Get 5 random properties in this tax code
            properties = Property.query.filter_by(
                tax_code_id=tax_code_id,
                year=current_year
            ).order_by(func.random()).limit(5).all()
            
            for prop in properties:
                prop_current_tax = (prop.assessed_value * current_levy_rate) / 1000
                prop_proposed_tax = (prop.assessed_value * proposed_levy_rate) / 1000
                prop_difference = prop_proposed_tax - prop_current_tax
                prop_percentage_change = (prop_difference / prop_current_tax) * 100 if prop_current_tax > 0 else 0
                
                sample_properties.append({
                    'parcel_id': prop.parcel_id,
                    'address': prop.property_address,
                    'assessed_value': float(prop.assessed_value),
                    'current_tax': float(prop_current_tax),
                    'proposed_tax': float(prop_proposed_tax),
                    'difference': float(prop_difference),
                    'percentage_change': float(prop_percentage_change)
                })
        
        result = {
            'property_value': property_value,
            'current_levy_rate': current_levy_rate,
            'proposed_levy_rate': proposed_levy_rate,
            'current_tax': float(current_tax),
            'proposed_tax': float(proposed_tax),
            'difference': float(difference),
            'percentage_change': float(percentage_change),
            'sample_properties': sample_properties
        }
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error calculating bill impact: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def register_levy_calculator_routes(app):
    """
    Register levy calculator routes with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(levy_calculator_bp)
    logger.info("Registered levy calculator routes")