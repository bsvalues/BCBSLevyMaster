"""
Routes for the public-facing portal.

This module includes routes that are accessible to the general public:
- Public property lookup
- Property tax information
- General tax resources
"""

import logging
from datetime import datetime
from flask import render_template, request, flash, jsonify
from app import app, db
from models import Property, TaxCode, TaxDistrict, TaxCodeHistoricalRate
from utils.district_utils import get_linked_levy_codes
from utils.tooltip_utils import get_glossary_terms, get_glossary_by_category, get_all_terms_alphabetical

# Configure logger
logger = logging.getLogger(__name__)

# Register context processor for all templates 
@app.context_processor
def inject_now():
    """Add the current datetime to all template contexts"""
    return {'now': datetime.now()}

@app.route('/public', methods=['GET'])
def public_portal_home():
    """
    Public-facing home page for property lookup portal.
    """
    # Get some basic statistics to display
    property_count = Property.query.count()
    tax_code_count = TaxCode.query.count()
    
    # Get glossary terms for tooltips
    glossary_terms = get_glossary_terms()
    
    return render_template('public/home.html', 
                          property_count=property_count,
                          tax_code_count=tax_code_count,
                          glossary_terms=glossary_terms)

@app.route('/public/lookup', methods=['GET', 'POST'])
def public_property_lookup():
    """
    Public-facing property lookup page.
    """
    property_data = None
    
    if request.method == 'POST':
        property_id = request.form.get('property_id')
        if property_id:
            # Find the property in the database
            property_obj = Property.query.filter_by(property_id=property_id).first()
            
            if property_obj:
                # Get the tax code information
                tax_code_obj = TaxCode.query.filter_by(code=property_obj.tax_code).first()
                
                if tax_code_obj and tax_code_obj.levy_rate:
                    # Calculate property tax
                    calculated_tax = (property_obj.assessed_value / 1000) * tax_code_obj.levy_rate
                    
                    # Get linked levy codes if available
                    linked_levy_codes = get_linked_levy_codes(property_obj.tax_code)
                    
                    # Get historical rates if available
                    historical_rates = []
                    if hasattr(tax_code_obj, 'historical_rates') and tax_code_obj.historical_rates:
                        historical_rates = tax_code_obj.historical_rates.order_by(
                            TaxCodeHistoricalRate.year.desc()
                        ).limit(3).all()
                    
                    property_data = {
                        'property_id': property_obj.property_id,
                        'assessed_value': property_obj.assessed_value,
                        'tax_code': property_obj.tax_code,
                        'levy_rate': tax_code_obj.levy_rate,
                        'calculated_tax': calculated_tax,
                        'linked_levy_codes': linked_levy_codes,
                        'historical_rates': historical_rates
                    }
                else:
                    flash("Tax information is not available for this property at this time.", 'warning')
            else:
                flash("We couldn't find that property ID in our records. Please check the ID and try again.", 'danger')
    
    # Get glossary terms for tooltips
    glossary_terms = get_glossary_terms()
    
    return render_template('public/property_lookup.html', 
                          property_data=property_data,
                          glossary_terms=glossary_terms)

@app.route('/public/resources', methods=['GET'])
def public_tax_resources():
    """
    Public-facing tax resources and information page.
    """
    # Get glossary terms for tooltips
    glossary_terms = get_glossary_terms()
    
    return render_template('public/resources.html', 
                          glossary_terms=glossary_terms)

@app.route('/public/glossary', methods=['GET'])
def public_glossary():
    """
    Public-facing glossary of tax terms.
    """
    # Get glossary terms organized by category
    glossary_by_category = get_glossary_by_category()
    
    # Get alphabetical listing
    terms_alphabetical = get_all_terms_alphabetical()
    
    return render_template('public/glossary.html', 
                          glossary_by_category=glossary_by_category,
                          terms_alphabetical=terms_alphabetical)

@app.route('/api/public/property-search', methods=['GET'])
def api_public_property_search():
    """
    API endpoint for searching properties by partial property ID.
    
    Used for autocomplete functionality on the public lookup page.
    """
    search_term = request.args.get('term', '')
    if not search_term or len(search_term) < 3:
        return jsonify([])
    
    # Search for properties with the given term
    properties = Property.query.filter(
        Property.property_id.ilike(f'%{search_term}%')
    ).limit(10).all()
    
    results = [{'id': p.property_id, 'text': p.property_id} for p in properties]
    return jsonify(results)

def init_public_routes():
    """
    Initialize public portal routes with the Flask app.
    """
    # Nothing to do here currently as routes are registered via decorators
    pass