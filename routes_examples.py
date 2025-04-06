"""
Example routes for demonstrating various UI features and components.

This module provides routes for showcasing various UI components,
form interactions, and design elements used throughout the application.
"""
import logging
from flask import Blueprint, render_template

# Create blueprint
examples_bp = Blueprint("examples", __name__, url_prefix="/examples")

# Configure logging
logger = logging.getLogger(__name__)


@examples_bp.route("/form-interactions", methods=["GET"])
def form_micro_interactions():
    """Render the form micro-interactions demo page."""
    return render_template("examples/form_micro_interactions.html")


@examples_bp.route("/components", methods=["GET"])
def ui_components():
    """Render the UI components showcase page."""
    return render_template("examples/ui_components.html")
