"""
Routes for examples and components demonstration.

This module provides routes for showcasing UI components,
interactive elements, and design patterns.
"""

from flask import Blueprint, render_template

examples_bp = Blueprint('examples', __name__, url_prefix='/examples')

@examples_bp.route('/forms')
def forms_demo():
    """Demo page for interactive form elements."""
    return render_template('examples/form_demo.html')