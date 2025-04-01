"""
Public-facing routes for property tax information.

This module provides routes for the public property tax information portal,
including property search, property details, and tax district information.
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, abort, current_app
from sqlalchemy import and_, or_, func, desc

from app import db
from models import Property, TaxDistrict, TaxCode, PropertyType, TaxCodeHistoricalRate


# Create blueprint
public_bp = Blueprint('public', __name__, url_prefix='/public')


@public_bp.route('/')
def index():
    """
    Render the public property tax portal home page.
    
    Returns:
        Rendered template for the public portal home page
    """
    # Get property count
    property_count = db.session.query(func.count(Property.id)).scalar() or 0
    
    # Get district count
    district_count = db.session.query(func.count(TaxDistrict.id)).scalar() or 0
    
    # Get latest year
    latest_year = db.session.query(func.max(Property.year)).scalar() or datetime.now().year
    
    # Get available property types for search
    property_types = list(PropertyType)
    
    return render_template(
        'public/index.html',
        property_count=property_count,
        district_count=district_count,
        latest_year=latest_year,
        property_types=property_types
    )


@public_bp.route('/search', methods=['GET', 'POST'])
def search():
    """
    Search properties with filtering options.
    
    Returns:
        Rendered template with search results or search form
    """
    # Get query parameters
    parcel_id = request.args.get('parcel_id', '') or request.form.get('parcel_id', '')
    address = request.args.get('address', '') or request.form.get('address', '')
    owner_name = request.args.get('owner_name', '') or request.form.get('owner_name', '')
    tax_code = request.args.get('tax_code', '') or request.form.get('tax_code', '')
    property_type_id = request.args.get('property_type_id', '') or request.form.get('property_type_id', '')
    page = request.args.get('page', 1, type=int)
    
    # Get available years for filtering
    available_years = db.session.query(Property.year).distinct().order_by(desc(Property.year)).all()
    available_years = [year[0] for year in available_years] or [datetime.now().year]
    
    # Get selected year (default to most recent)
    year = request.args.get('year', available_years[0], type=int) or request.form.get('year', available_years[0], type=int)
    
    # Get available property types for filtering
    property_types = list(PropertyType)
    
    # Create query
    query = db.session.query(Property).filter(Property.year == year)
    
    # Apply filters if provided
    if parcel_id:
        query = query.filter(Property.parcel_id.ilike(f'%{parcel_id}%'))
    
    if address:
        query = query.filter(Property.address.ilike(f'%{address}%'))
    
    if owner_name:
        query = query.filter(Property.owner_name.ilike(f'%{owner_name}%'))
    
    if tax_code:
        query = query.filter(Property.tax_code.ilike(f'%{tax_code}%'))
    
    if property_type_id:
        query = query.filter(Property.property_type_id == int(property_type_id))
    
    # Determine if search was performed
    search_performed = any([parcel_id, address, owner_name, tax_code, property_type_id])
    
    # Get results with pagination
    if search_performed:
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        results = pagination.items
    else:
        results = []
        pagination = None
    
    # Query parameters for pagination links
    query_params = {
        'parcel_id': parcel_id,
        'address': address,
        'owner_name': owner_name,
        'tax_code': tax_code,
        'property_type_id': property_type_id,
        'year': year
    }
    
    return render_template(
        'public/search.html',
        results=results,
        pagination=pagination,
        search_performed=search_performed,
        query_params=query_params,
        property_types=property_types,
        available_years=available_years
    )


@public_bp.route('/property/<string:parcel_id>')
def property_detail(parcel_id):
    """
    Show detailed information for a specific property.
    
    Args:
        parcel_id: The unique parcel identifier
        
    Returns:
        Rendered template with property details
    """
    # Get available years
    available_years = db.session.query(Property.year).filter(
        Property.parcel_id == parcel_id
    ).distinct().order_by(desc(Property.year)).all()
    available_years = [year[0] for year in available_years]
    
    if not available_years:
        abort(404)
    
    # Get selected year (default to most recent)
    year = request.args.get('year', available_years[0], type=int)
    
    # Get property data for the selected year
    property = Property.query.filter(
        Property.parcel_id == parcel_id,
        Property.year == year
    ).first_or_404()
    
    # Get tax code information
    tax_code = None
    if property.tax_code:
        tax_code = TaxCode.query.filter(
            TaxCode.tax_code == property.tax_code,
            TaxCode.year == year
        ).first()
    
    # Get district information
    districts = []
    if tax_code:
        districts = TaxDistrict.query.join(
            TaxCode, TaxCode.district_codes.contains(TaxDistrict.district_code)
        ).filter(
            TaxCode.tax_code == property.tax_code,
            TaxDistrict.year == year
        ).all()
    
    # Get historical rate information
    historical_rate = None
    if tax_code:
        historical_rate = TaxCodeHistoricalRate.query.filter(
            TaxCodeHistoricalRate.tax_code_id == tax_code.id,
            TaxCodeHistoricalRate.year == year
        ).first()
    
    # Get tax history for this property
    tax_history = []
    for hist_year in available_years:
        prop_data = Property.query.filter(
            Property.parcel_id == parcel_id,
            Property.year == hist_year
        ).first()
        
        if prop_data:
            # Calculate tax amount if we have the data
            tax_amount = None
            hist_tax_code = None
            if prop_data.tax_code:
                hist_tax_code = TaxCode.query.filter(
                    TaxCode.tax_code == prop_data.tax_code,
                    TaxCode.year == hist_year
                ).first()
                
                if hist_tax_code:
                    hist_rate = TaxCodeHistoricalRate.query.filter(
                        TaxCodeHistoricalRate.tax_code_id == hist_tax_code.id,
                        TaxCodeHistoricalRate.year == hist_year
                    ).first()
                    
                    if hist_rate and hist_rate.levy_rate and prop_data.assessed_value:
                        tax_amount = prop_data.assessed_value * hist_rate.levy_rate / 1000
            
            tax_history.append({
                'year': hist_year,
                'assessed_value': prop_data.assessed_value,
                'tax_amount': tax_amount
            })
    
    # Get property value history (for chart)
    value_history = []
    for hist_year in available_years:
        prop_data = Property.query.filter(
            Property.parcel_id == parcel_id,
            Property.year == hist_year
        ).first()
        
        if prop_data and prop_data.assessed_value:
            value_history.append({
                'year': hist_year,
                'assessed_value': prop_data.assessed_value
            })
    
    return render_template(
        'public/property_detail.html',
        property=property,
        tax_code=tax_code,
        districts=districts,
        historical_rate=historical_rate,
        tax_history=tax_history,
        value_history=value_history,
        available_years=available_years,
        current_year=year
    )


@public_bp.route('/compare')
def compare_properties():
    """
    Compare multiple properties side by side.
    
    Returns:
        Rendered template with property comparison
    """
    # Get property IDs from query parameters
    property_ids = request.args.getlist('property_ids') or []
    if request.method == 'POST':
        property_ids = request.form.getlist('property_ids') or []
    
    # Filter out empty strings
    property_ids = [pid for pid in property_ids if pid]
    
    # Get available years for all properties
    available_years = []
    for parcel_id in property_ids:
        years = db.session.query(Property.year).filter(
            Property.parcel_id == parcel_id
        ).distinct().all()
        available_years.extend([year[0] for year in years])
    
    # Get unique sorted years
    available_years = sorted(list(set(available_years)), reverse=True)
    
    if not available_years:
        # If no properties selected, get all available years
        years = db.session.query(Property.year).distinct().order_by(desc(Property.year)).all()
        available_years = [year[0] for year in years] or [datetime.now().year]
    
    # Get selected year (default to most recent)
    year = request.args.get('year', available_years[0] if available_years else datetime.now().year, type=int)
    
    # Get properties for the selected year
    properties = []
    for parcel_id in property_ids:
        property = Property.query.filter(
            Property.parcel_id == parcel_id,
            Property.year == year
        ).first()
        
        if property:
            # Get tax code information
            if property.tax_code:
                tax_code = TaxCode.query.filter(
                    TaxCode.tax_code == property.tax_code,
                    TaxCode.year == year
                ).first()
                
                if tax_code:
                    property.tax_code_obj = tax_code
                    
                    # Get historical rate information
                    historical_rate = TaxCodeHistoricalRate.query.filter(
                        TaxCodeHistoricalRate.tax_code_id == tax_code.id,
                        TaxCodeHistoricalRate.year == year
                    ).first()
                    
                    if historical_rate and historical_rate.levy_rate and property.assessed_value:
                        property.historical_rate = historical_rate
                        property.tax_amount = property.assessed_value * historical_rate.levy_rate / 1000
            
            properties.append(property)
    
    return render_template(
        'public/compare.html',
        properties=properties,
        property_ids=property_ids,
        available_years=available_years,
        year=year
    )


@public_bp.route('/districts')
def district_list():
    """
    List all tax districts with filtering options.
    
    Returns:
        Rendered template with tax district list
    """
    # Get available years
    available_years = db.session.query(TaxDistrict.year).distinct().order_by(desc(TaxDistrict.year)).all()
    available_years = [year[0] for year in available_years] or [datetime.now().year]
    
    # Get selected year (default to most recent)
    year = request.args.get('year', available_years[0], type=int)
    
    # Get districts for the selected year
    districts = TaxDistrict.query.filter(TaxDistrict.year == year).order_by(TaxDistrict.district_name).all()
    
    return render_template(
        'public/district_list.html',
        districts=districts,
        available_years=available_years,
        year=year
    )


@public_bp.route('/district/<int:district_id>')
def district_detail(district_id):
    """
    Show detailed information for a specific tax district.
    
    Args:
        district_id: The unique district identifier
        
    Returns:
        Rendered template with district details
    """
    # Get district
    district = TaxDistrict.query.get_or_404(district_id)
    
    # Get tax codes that include this district
    tax_codes = TaxCode.query.filter(
        TaxCode.district_codes.contains(district.district_code),
        TaxCode.year == district.year
    ).all()
    
    # Get property count for this district
    property_count = Property.query.join(
        TaxCode, Property.tax_code == TaxCode.tax_code
    ).filter(
        TaxCode.district_codes.contains(district.district_code),
        Property.year == district.year,
        TaxCode.year == district.year
    ).count()
    
    # Get historical rate information for each tax code
    historical_rates = {}
    for tax_code in tax_codes:
        historical_rate = TaxCodeHistoricalRate.query.filter(
            TaxCodeHistoricalRate.tax_code_id == tax_code.id,
            TaxCodeHistoricalRate.year == district.year
        ).first()
        
        if historical_rate:
            historical_rates[tax_code.id] = historical_rate
    
    return render_template(
        'public/district_detail.html',
        district=district,
        tax_codes=tax_codes,
        property_count=property_count,
        historical_rates=historical_rates
    )