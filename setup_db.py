"""
Database setup script for the SaaS Levy Calculation System.

This script:
1. Runs all necessary migrations in the correct order
2. Imports sample levy data if needed
3. Adds historical rate data for analysis features

Usage:
    python setup_db.py [options]

Options:
    --yes, -y             Skip all confirmation prompts and proceed with all operations
    --force, -f           Run all operations even if data already exists
    --migrations-only     Run only migrations, skip data import
    --import-only         Skip migrations, only import data
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from models import User, TaxDistrict, TaxCode, TaxCodeHistoricalRate
import add_missing_columns
import add_import_type_migration
import add_historical_rates_table
import fix_import_log_user_id
import fix_tax_district_table

# Import scripts
import import_sample_levy_data
import seed_historical_rates
import create_admin

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_migrations(auto_confirm=False):
    """
    Run all migrations in the correct order.
    
    Args:
        auto_confirm: Skip confirmation prompts if True
        
    Returns:
        True if migrations were successful, False otherwise
    """
    logger.info("Starting database migrations...")
    
    migrations = [
        {"name": "Add missing columns", "function": add_missing_columns.run_migration},
        {"name": "Add import type", "function": add_import_type_migration.run_migration},
        {"name": "Fix import log user_id", "function": fix_import_log_user_id.run_migration},
        {"name": "Add historical rates table", "function": add_historical_rates_table.run_migration},
        {"name": "Fix tax district table", "function": fix_tax_district_table.run_migration},
    ]
    
    success_count = 0
    
    for migration in migrations:
        name = migration["name"]
        func = migration["function"]
        
        logger.info(f"Running migration: {name}")
        try:
            if callable(func):
                result = func()
                if result and isinstance(result, dict) and result.get("success", False):
                    logger.info(f"Migration successful: {name}")
                    success_count += 1
                else:
                    logger.warning(f"Migration returned unexpected result: {result}")
            else:
                logger.error(f"Migration function is not callable: {name}")
        except Exception as e:
            logger.error(f"Error in migration {name}: {str(e)}")
    
    logger.info(f"Completed {success_count}/{len(migrations)} migrations")
    return success_count == len(migrations)


def import_sample_data(auto_confirm=False, force=False):
    """
    Import sample levy data.
    
    Args:
        auto_confirm: Skip confirmation prompts if True
        force: Import data even if data already exists
        
    Returns:
        True if import was successful, False otherwise
    """
    logger.info("Checking for existing data...")
    
    # Check for existing data
    tax_district_count = TaxDistrict.query.count()
    tax_code_count = TaxCode.query.count()
    
    if tax_district_count > 0 or tax_code_count > 0:
        logger.info(f"Found existing data: {tax_district_count} tax districts, {tax_code_count} tax codes")
        
        if not force and not auto_confirm:
            response = input("Data already exists. Import sample data anyway? [y/N]: ")
            if response.lower() != 'y':
                logger.info("Sample data import skipped")
                return True  # Return true since this is not an error
    
    # Import sample data
    logger.info("Importing sample levy data...")
    results = import_sample_levy_data.import_all_sample_files()
    
    success_count = sum(1 for _, success, _, _ in results if success)
    logger.info(f"Imported data from {success_count}/{len(results)} files")
    
    return success_count > 0


def add_historical_data(auto_confirm=False, force=False):
    """
    Add historical rate data for analysis features.
    
    Args:
        auto_confirm: Skip confirmation prompts if True
        force: Add data even if data already exists
        
    Returns:
        True if operation was successful, False otherwise
    """
    logger.info("Checking for historical rate data...")
    
    # Check for existing historical data
    historical_count = TaxCodeHistoricalRate.query.count()
    
    if historical_count > 0:
        logger.info(f"Found {historical_count} existing historical rate records")
        
        if not force and not auto_confirm:
            response = input("Historical data already exists. Add more sample data anyway? [y/N]: ")
            if response.lower() != 'y':
                logger.info("Historical data addition skipped")
                return True  # Return true since this is not an error
    
    # Add historical data
    logger.info("Adding historical rate data...")
    
    # Temporarily patch the input function to auto-confirm
    if auto_confirm:
        original_input = input
        try:
            __builtins__["input"] = lambda prompt: "y"
            results = seed_historical_rates.seed_historical_rates()
        finally:
            __builtins__["input"] = original_input
    else:
        results = seed_historical_rates.seed_historical_rates()
    
    if "error" in results:
        logger.error(f"Error adding historical data: {results['error']}")
        return False
    
    if "status" in results and results["status"] == "cancelled":
        logger.info("Historical data addition cancelled by user")
        return True
    
    logger.info(f"Added {results.get('total_added', 0)} historical rate records")
    return True


def ensure_admin_user(auto_confirm=False):
    """
    Ensure an admin user exists.
    
    Args:
        auto_confirm: Skip confirmation prompts if True
        
    Returns:
        True if an admin user exists or was created, False otherwise
    """
    logger.info("Checking for admin user...")
    
    # Check if admin exists
    admin_exists, user_count, admin_count = create_admin.check_admin_users()
    
    if admin_exists:
        logger.info(f"Found {admin_count} admin users out of {user_count} total users")
        return True
    
    # Create admin if none exists
    logger.info("No admin user found. Creating default admin user...")
    
    success, message = create_admin.create_admin_user(
        username="admin",
        email="admin@example.com",
        password="admin123",
        first_name="System",
        last_name="Administrator",
        force=True
    )
    
    if success:
        logger.info(f"Admin user created: {message}")
        return True
    else:
        logger.error(f"Failed to create admin user: {message}")
        return False


def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Database setup script for SaaS Levy Calculation System")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip all confirmation prompts")
    parser.add_argument("--force", "-f", action="store_true", help="Run all operations even if data exists")
    parser.add_argument("--migrations-only", action="store_true", help="Run only migrations, skip data import")
    parser.add_argument("--import-only", action="store_true", help="Skip migrations, only import data")
    
    args = parser.parse_args()
    
    # Create the Flask app
    app = create_app()
    
    # Use app context for database operations
    with app.app_context():
        logger.info("Starting database setup...")
        start_time = time.time()
        
        # Step 1: Run migrations
        if not args.import_only:
            migrations_result = run_migrations(args.yes)
            if not migrations_result:
                logger.error("Migrations failed. Setup aborted.")
                return 1
        
        # Step 2: Ensure admin user
        admin_result = ensure_admin_user(args.yes)
        if not admin_result:
            logger.error("Admin user setup failed.")
            return 1
        
        # Step 3: Import sample data
        if not args.migrations_only:
            import_result = import_sample_data(args.yes, args.force)
            if not import_result:
                logger.warning("Sample data import failed or was skipped.")
                # Continue anyway, this is not critical
            
            # Step 4: Add historical data
            historical_result = add_historical_data(args.yes, args.force)
            if not historical_result:
                logger.warning("Historical data addition failed.")
                # Continue anyway, this is not critical
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        logger.info(f"Database setup completed in {elapsed_time:.2f} seconds")
        
        return 0


if __name__ == "__main__":
    sys.exit(main())