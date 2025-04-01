"""
Tooltip utility functions for tax terminology explanations.

This module provides:
1. A comprehensive dictionary of tax terminology
2. Jinja2 filters to apply tooltips in templates
3. Functions to generate HTML tooltip markup
4. Functions to get glossary terms for display
"""

import re
import logging
from markupsafe import Markup

# Logger setup
logger = logging.getLogger(__name__)

# Comprehensive dictionary of tax terminology
TAX_TERMINOLOGY = {
    # Levy terms
    "Levy": "A tax imposed on property by a local government, calculated by multiplying the assessed value by the levy rate.",
    "Levy Rate": "The tax rate applied to property values, typically expressed per $1,000 of assessed value.",
    "Levy Lid": "A statutory limitation that restricts the annual percentage increase in regular property tax levies.",
    "Levy Capacity": "The maximum amount a taxing district can legally levy under statutory limitations.",
    "Banked Capacity": "Unused levy capacity that a taxing district can 'save' or 'bank' for future use.",
    "Statutory Limit": "Legal maximum levy rates or amounts established by state law.",
    "Special Levy": "A levy outside the regular property tax limitations, often requiring voter approval.",
    "Regular Levy": "The primary property tax levy subject to statutory limitations.",
    "Excess Levy": "A voter-approved levy that exceeds the statutory rate limits.",
    "Bond Levy": "A voter-approved levy to pay principal and interest on bonds issued by a taxing district.",
    "Maintenance & Operations (M&O) Levy": "A special levy used to fund maintenance and operations expenses, often for schools.",
    "Enhancement Levy": "A supplemental levy to enhance funding for specific services.",
    
    # Assessment terms
    "Assessed Value": "The dollar value assigned to taxable property by the county assessor, used to calculate property taxes.",
    "Market Value": "The estimated amount for which a property would sell on the open market.",
    "Fair Market Value": "The price at which property would change hands between a willing buyer and seller.",
    "Collection Year": "The calendar year in which property taxes are collected, following the assessment year.",
    "Assessment Year": "The calendar year in which property values are established for tax purposes.",
    "Assessment Ratio": "The ratio of assessed value to market value, often expressed as a percentage.",
    
    # Administrative terms
    "Tax Roll": "The official list of all property subject to taxation, including assessed values and tax amounts.",
    "Tax District": "A geographical area established for property tax purposes, such as a county, city, or school district.",
    "Tax Code": "A unique identifier assigned to a specific geographical area with uniform levy rates.",
    "Tax Code Area": "A geographical area where all properties are subject to the same combination of taxing districts.",
    "Millage": "Another term for the tax rate, with one mill representing one-tenth of a cent ($0.001) per dollar.",
    "Mill": "One-thousandth of a dollar ($0.001) used in expressing property tax rates.",
    "Abatement": "A reduction or forgiveness of property taxes, often granted as an economic incentive.",
    "Tax Increment Financing (TIF)": "A public financing method used to subsidize development projects by diverting future property tax revenue increases.",
    "Property Tax Exemption": "A reduction or elimination of property tax for qualifying property owners or properties.",
    "Tax Deferral": "A temporary delay in payment of property taxes, often for elderly or disabled taxpayers.",
    "Property Tax Appeal": "A formal process for contesting a property's assessed value or tax classification.",
    
    # Statistical terms
    "Mean": "The arithmetic average of a data set, calculated by dividing the sum of values by the number of values.",
    "Median": "The middle value in a sorted list of numbers, representing the central tendency of the data.",
    "Variance": "A statistical measure of the spread or dispersion of a data set from its mean.",
    "Standard Deviation": "A measure of the amount of variation or dispersion in a data set, equal to the square root of the variance.",
    "Coefficient of Variation": "A standardized measure of dispersion, calculated as the ratio of the standard deviation to the mean, often expressed as a percentage.",
    "Z-Score": "A statistical measurement that indicates how many standard deviations a data point is from the mean.",
    "Moving Average": "A calculation used to analyze data points by creating a series of averages of different subsets of the full data set.",
    
    # Advanced terms
    "Bill Impact": "The change in property tax amounts resulting from changes in levy rates, assessed values, or tax laws.",
    "Trend Forecasting": "Statistical methods used to predict future levy rates or property values based on historical patterns.",
    "Confidence Interval": "A range of values that is likely to contain the true value of an unknown parameter with a specified probability.",
    "Multi-year levy data analysis": "Examining levy rates, amounts, and assessed values across multiple years to identify patterns and trends.",
    "Anomaly Detection": "Statistical methods used to identify unusual patterns or outliers in levy data that deviate from expected behavior.",
    "Tax Distribution": "The allocation of property tax revenue among various taxing districts within a jurisdiction.",
    "Assessed Value Threshold": "A minimum property value below which certain tax rules or exemptions may apply.",
    "Scatter Plot": "A type of chart that shows the relationship between two variables, often used to visualize data distribution.",
    "Correlation Analysis": "Statistical method to measure and interpret the relationship between two or more variables.",
    "Regression Model": "A statistical model that examines the relationship between dependent and independent variables, often used for forecasting.",
    
    # UI elements
    "Tooltips": "Interactive help text that appears when hovering over terms, providing definitions and explanations.",
}

def find_terms_in_text(text):
    """
    Find tax terminology terms within a given text.
    
    Args:
        text (str): The text to search for terminology terms
        
    Returns:
        list: List of tuples containing (term, definition, start_pos, end_pos)
    """
    matches = []
    
    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Sort terms by length (descending) to prioritize longer matches
    sorted_terms = sorted(TAX_TERMINOLOGY.keys(), key=len, reverse=True)
    
    for term in sorted_terms:
        term_lower = term.lower()
        
        # Find all occurrences of the term
        start_pos = 0
        while start_pos < len(text_lower):
            pos = text_lower.find(term_lower, start_pos)
            if pos == -1:
                break
                
            # Check if this is a word boundary match to avoid partial matches
            is_word_boundary = True
            
            # Check character before term (if not at beginning)
            if pos > 0 and text_lower[pos-1].isalnum():
                is_word_boundary = False
                
            # Check character after term (if not at end)
            end_pos = pos + len(term_lower)
            if end_pos < len(text_lower) and text_lower[end_pos].isalnum():
                is_word_boundary = False
                
            if is_word_boundary:
                # Use the actual case from original text
                actual_term = text[pos:pos+len(term_lower)]
                matches.append((term, TAX_TERMINOLOGY[term], pos, pos+len(term_lower)))
                
            start_pos = pos + 1
    
    # Sort matches by position
    matches.sort(key=lambda x: x[2])
    
    return matches

def generate_tooltip_html(term, definition):
    """
    Generate HTML markup for a tooltip.
    
    Args:
        term (str): The term to be displayed
        definition (str): The tooltip definition
        
    Returns:
        str: HTML markup for the tooltip
    """
    # Clean the definition to prevent any HTML injection
    definition = definition.replace('"', '&quot;')
    
    # Create the tooltip HTML
    tooltip_html = f'<span class="tooltip-term" data-bs-toggle="tooltip" data-bs-placement="top" title="{definition}">{term}</span>'
    
    return tooltip_html

def add_tooltips_to_text(text):
    """
    Add tooltip HTML to tax terminology in a given text.
    
    Args:
        text (str): The text to enhance with tooltips
        
    Returns:
        str: HTML markup with tooltips added
    """
    if not text:
        return ""
        
    try:
        # Find all terms in the text
        matches = find_terms_in_text(text)
        
        # If no matches, return original text
        if not matches:
            return text
            
        # Build result with tooltips
        result = ""
        last_end = 0
        
        for term, definition, start, end in matches:
            # Add text before match
            result += text[last_end:start]
            
            # Add tooltip for term (using actual text from original with original case)
            actual_term = text[start:end]
            result += generate_tooltip_html(actual_term, definition)
            
            last_end = end
            
        # Add remaining text
        result += text[last_end:]
        
        return result
    except Exception as e:
        logger.error(f"Error adding tooltips to text: {str(e)}")
        # Return original text if any error occurs
        return text

def tooltip_filter(text):
    """
    Jinja2 filter to generate a single tooltip for a term.
    
    Args:
        text (str): The term to convert to a tooltip
        
    Returns:
        Markup: HTML markup for the tooltip
    """
    if not text:
        return Markup("")
        
    try:
        # Look up term in dictionary (case-insensitive)
        for term, definition in TAX_TERMINOLOGY.items():
            if term.lower() == text.lower():
                return Markup(generate_tooltip_html(text, definition))
                
        # Term not found, return original text
        return Markup(text)
    except Exception as e:
        logger.error(f"Error in tooltip filter: {str(e)}")
        # Return original text if any error occurs
        return Markup(text)

def add_tooltips_filter(text):
    """
    Jinja2 filter to add tooltips to all tax terms in a text.
    
    Args:
        text (str): The text to enhance with tooltips
        
    Returns:
        Markup: HTML markup with tooltips added
    """
    if not text:
        return Markup("")
        
    try:
        result = add_tooltips_to_text(text)
        return Markup(result)
    except Exception as e:
        logger.error(f"Error in add_tooltips filter: {str(e)}")
        # Return original text if any error occurs
        return Markup(text)

def initialize_tooltip_jinja_filters(app):
    """
    Initialize Jinja2 filters for tooltips.
    
    Args:
        app: Flask application instance
    """
    app.jinja_env.filters['tooltip'] = tooltip_filter
    app.jinja_env.filters['add_tooltips'] = add_tooltips_filter
    
    logger.info("Tooltip Jinja2 filters initialized")


def get_glossary_terms():
    """
    Get all tax terminology as a dictionary.
    
    Returns:
        dict: Dictionary of tax terms and their definitions
    """
    return TAX_TERMINOLOGY


def get_glossary_by_category():
    """
    Get tax terminology organized by category.
    
    Returns:
        list: List of category dictionaries with id, name, description, and terms
    """
    # Define categories with ID, name, and descriptions
    categories = [
        {
            "id": "levy-terms",
            "name": "Levy Terms",
            "description": "Terms related to property tax levies, rates, and statutory limitations.",
            "keywords": ["Levy", "Capacity", "Statutory", "Enhancement"]
        },
        {
            "id": "assessment-terms",
            "name": "Assessment Terms",
            "description": "Terms related to property valuation and assessment processes.",
            "keywords": ["Assessed", "Market", "Fair", "Collection", "Assessment"]
        },
        {
            "id": "administrative-terms",
            "name": "Administrative Terms",
            "description": "Terms related to tax administration, districts, and governance.",
            "keywords": ["Tax Roll", "Tax District", "Tax Code", "Millage", "Mill", "Abatement", "TIF", "Exemption", "Deferral", "Appeal"]
        },
        {
            "id": "statistical-terms",
            "name": "Statistical Terms",
            "description": "Terms related to statistical analysis and data interpretation.",
            "keywords": ["Mean", "Median", "Variance", "Standard Deviation", "Coefficient", "Z-Score", "Moving Average"]
        },
        {
            "id": "advanced-terms",
            "name": "Advanced Terms",
            "description": "Advanced concepts in property tax analysis and forecasting.",
            "keywords": ["Bill Impact", "Trend", "Confidence", "Multi-year", "Anomaly", "Distribution", "Threshold", "Scatter", "Correlation", "Regression"]
        }
    ]
    
    # Initialize terms arrays for each category
    for category in categories:
        category["terms"] = []
    
    # Add a miscellaneous category
    miscellaneous = {
        "id": "miscellaneous",
        "name": "Miscellaneous Terms",
        "description": "Other property tax related terminology.",
        "terms": []
    }
    
    # Categorize terms
    for term, definition in TAX_TERMINOLOGY.items():
        # Create term object with definition and optional example
        term_obj = {
            "term": term,
            "definition": definition
        }
        
        # Check if definition contains an example (indicated by "Example:" or similar)
        if "example:" in definition.lower() or "e.g.," in definition.lower():
            # Split definition and example
            parts = re.split(r'(example:|e\.g\.,)', definition.lower(), 1, re.IGNORECASE)
            if len(parts) >= 3:
                term_obj["definition"] = parts[0].strip()
                term_obj["example"] = parts[1] + parts[2].strip()
        
        # Find appropriate category
        assigned = False
        for category in categories:
            for keyword in category["keywords"]:
                if keyword.lower() in term.lower():
                    category["terms"].append(term_obj)
                    assigned = True
                    break
            if assigned:
                break
                
        # If term doesn't match any category, put in "Miscellaneous"
        if not assigned:
            miscellaneous["terms"].append(term_obj)
    
    # Sort terms alphabetically within each category
    for category in categories:
        category["terms"].sort(key=lambda x: x["term"])
    
    miscellaneous["terms"].sort(key=lambda x: x["term"])
    
    # Remove empty categories and add miscellaneous if it has terms
    result = [category for category in categories if category["terms"]]
    if miscellaneous["terms"]:
        result.append(miscellaneous)
    
    return result


def get_all_terms_alphabetical():
    """
    Get all tax terminology organized alphabetically by first letter.
    
    Returns:
        dict: Dictionary with letter keys, each containing a list of term objects
    """
    result = {}
    
    for term, definition in sorted(TAX_TERMINOLOGY.items()):
        first_letter = term[0].upper()
        
        if first_letter not in result:
            result[first_letter] = []
        
        # Create term object
        term_obj = {
            "term": term,
            "definition": definition
        }
        
        # Check if definition contains an example
        if "example:" in definition.lower() or "e.g.," in definition.lower():
            # Split definition and example
            parts = re.split(r'(example:|e\.g\.,)', definition.lower(), 1, re.IGNORECASE)
            if len(parts) >= 3:
                term_obj["definition"] = parts[0].strip()
                term_obj["example"] = parts[1] + parts[2].strip()
        
        result[first_letter].append(term_obj)
    
    return result