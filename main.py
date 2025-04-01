"""
Entry point for the Levy Calculation System application.

This module serves as the main entry point for running the Flask
application locally with Gunicorn or directly with the Flask development server.
"""

import os
import logging

from flask import Flask
from sqlalchemy.orm import DeclarativeBase

from app import app


if __name__ == "__main__":
    # Configure logging 
    logging.basicConfig(level=logging.DEBUG)
    
    # Run the application
    app.run(host="0.0.0.0", port=5000, debug=True)