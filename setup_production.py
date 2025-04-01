#!/usr/bin/env python3
"""
Production environment setup script.

This script prepares the application for production deployment by:
1. Creating the migrations directory if it doesn't exist
2. Setting up the production database if needed
3. Applying database migrations
4. Creating a logs directory for production logging

Usage:
    python setup_production.py
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment to production
os.environ['FLASK_ENV'] = 'production'

def run_command(command, description):
    """Run a shell command and log the result."""
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Command successful: {description}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {description}")
        logger.error(f"Error: {e.stderr}")
        return False, e.stderr

def create_directory(path, description):
    """Create a directory if it doesn't exist."""
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created {description} directory: {path}")
        else:
            logger.info(f"{description} directory already exists: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create {description} directory: {e}")
        return False

def check_database_connection():
    """Check if the database connection is properly configured."""
    logger.info("Checking database connection...")
    
    # Import within a function to ensure the app context is properly set up
    from app import create_app
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy import text
    
    try:
        app = create_app('production')
        with app.app_context():
            from app import db
            # Execute a simple query to check the connection
            db.session.execute(text("SELECT 1"))
            db.session.commit()
        logger.info("Database connection successful")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to connect to database: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking database connection: {e}")
        return False

def setup_migrations():
    """Initialize and apply database migrations."""
    # Check if migrations directory exists, if not initialize it
    if not os.path.exists('migrations'):
        success, output = run_command(
            "python migrate.py init",
            "Initialize migrations repository"
        )
        if not success:
            return False
    
    # Apply any pending migrations
    success, output = run_command(
        "python migrate.py upgrade",
        "Apply database migrations"
    )
    return success

def main():
    """Run the production setup process."""
    logger.info("Starting production environment setup")
    
    # Create logs directory
    if not create_directory('logs', 'logs'):
        return False
    
    # Check database connection
    if not check_database_connection():
        logger.error("Database connection check failed. Please check your DATABASE_URL environment variable.")
        return False
    
    # Set up migrations
    if not setup_migrations():
        logger.error("Failed to set up database migrations.")
        return False
    
    logger.info("Production environment setup completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)