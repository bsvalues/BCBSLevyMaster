"""
Custom Jinja filters for formatting data in templates.
"""

import locale
from functools import wraps


def setup_jinja_filters(app):
    """
    Register custom Jinja filters with the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Set locale for number formatting
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        # Fallback if the locale is not available
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, 'C')
    
    # Register filters
    app.jinja_env.filters['number_format'] = number_format
    app.jinja_env.filters['currency_format'] = currency_format
    app.jinja_env.filters['percent_format'] = percent_format
    
    app.logger.info("Custom Jinja filters initialized")


def safe_filter(func):
    """
    Decorator to make filters safe by handling None values and exceptions.
    """
    @wraps(func)
    def wrapper(value, *args, **kwargs):
        if value is None:
            return ''
        try:
            return func(value, *args, **kwargs)
        except (ValueError, TypeError):
            return value
    return wrapper


@safe_filter
def number_format(value, decimal_places=0):
    """
    Format a number with thousands separators.
    
    Args:
        value: The number to format
        decimal_places: Number of decimal places to display
        
    Returns:
        Formatted number string
    """
    try:
        value = float(value)
        return locale.format_string(f'%.{decimal_places}f', value, grouping=True)
    except (ValueError, TypeError):
        return value


@safe_filter
def currency_format(value, symbol='$', decimal_places=2):
    """
    Format a number as currency.
    
    Args:
        value: The number to format
        symbol: Currency symbol to use
        decimal_places: Number of decimal places to display
        
    Returns:
        Formatted currency string
    """
    try:
        value = float(value)
        formatted = locale.format_string(f'%.{decimal_places}f', value, grouping=True)
        return f"{symbol}{formatted}"
    except (ValueError, TypeError):
        return value


@safe_filter
def percent_format(value, decimal_places=2):
    """
    Format a number as a percentage.
    
    Args:
        value: The number to format (0.01 = 1%)
        decimal_places: Number of decimal places to display
        
    Returns:
        Formatted percentage string
    """
    try:
        value = float(value) * 100  # Convert to percentage
        formatted = locale.format_string(f'%.{decimal_places}f', value, grouping=True)
        return f"{formatted}%"
    except (ValueError, TypeError):
        return value