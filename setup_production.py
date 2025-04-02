#!/usr/bin/env python3
"""
Production environment setup script.

This script prepares the application for production deployment by:
1. Creating the migrations directory if it doesn't exist
2. Setting up the production database if needed
3. Backing up the database before applying migrations
4. Applying database migrations
5. Creating logs and backup directories for production use
6. Verifying the application's health after migration

Usage:
    python setup_production.py           # Run all setup steps
    python setup_production.py --backup  # Only backup the database
    python setup_production.py --migrate # Only run migrations
"""

import os
import sys
import logging
import subprocess
import argparse
import datetime
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
    
    # Check if we're using PostgreSQL
    is_postgres = False
    try:
        from app import create_app
        from sqlalchemy import text
        
        app = create_app('production')
        with app.app_context():
            from app import db
            result = db.session.execute(text("SELECT version()")).scalar()
            is_postgres = result and 'postgresql' in result.lower()
    except Exception as e:
        logger.warning(f"Could not determine database type: {e}")
    
    # Use enhanced PostgreSQL migration script if available and appropriate
    if is_postgres and os.path.exists('production_migrate.py'):
        logger.info("Using PostgreSQL-specific migration process")
        success, output = run_command(
            "python production_migrate.py migrate",
            "Apply PostgreSQL database migrations with enhanced safety checks"
        )
    else:
        # Standard migration approach
        success, output = run_command(
            "python migrate.py upgrade",
            "Apply database migrations"
        )
    
    return success

def backup_database():
    """Backup the database to a file."""
    logger.info("Starting database backup")
    
    # Create backups directory
    if not create_directory('backups', 'database backups'):
        return False
    
    # Check if we're using PostgreSQL
    is_postgres = False
    try:
        from app import create_app
        from sqlalchemy import text
        
        app = create_app('production')
        with app.app_context():
            from app import db
            result = db.session.execute(text("SELECT version()")).scalar()
            is_postgres = result and 'postgresql' in result.lower()
    except Exception as e:
        logger.warning(f"Could not determine database type: {e}")
    
    # Use enhanced PostgreSQL backup if available and appropriate
    if is_postgres and os.path.exists('production_migrate.py'):
        logger.info("Using PostgreSQL-specific backup process")
        success, output = run_command(
            "python production_migrate.py backup",
            "Creating compressed PostgreSQL backup"
        )
        
        if success:
            logger.info("Database backup created successfully with enhanced PostgreSQL tools")
            return True
        else:
            logger.error("Enhanced PostgreSQL backup failed, falling back to standard method")
            # Fall through to standard backup method
    
    # Standard PostgreSQL backup approach
    if is_postgres:
        # Get the current timestamp for the backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backups/database_backup_{timestamp}.sql"
        
        # Get database connection parameters from environment
        pg_host = os.environ.get('PGHOST')
        pg_user = os.environ.get('PGUSER')
        pg_password = os.environ.get('PGPASSWORD')
        pg_database = os.environ.get('PGDATABASE')
        
        # Build the pg_dump command
        pg_dump_cmd = f"PGPASSWORD='{pg_password}' pg_dump -h {pg_host} -U {pg_user} -d {pg_database} -f {backup_filename}"
        
        # Run the backup command
        success, output = run_command(pg_dump_cmd, "Backup database")
        
        if success:
            logger.info(f"Database backup created successfully: {backup_filename}")
            return True
        else:
            logger.error("Failed to create database backup")
            return False
    else:
        # SQLite or other non-PostgreSQL database
        logger.info("Non-PostgreSQL database detected, using simple file backup")
        try:
            from app import create_app
            app = create_app('production')
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            if os.path.exists(db_path):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backups/sqlite_backup_{timestamp}.db"
                
                # Simple file copy for SQLite
                import shutil
                shutil.copy2(db_path, backup_path)
                
                logger.info(f"SQLite database backup created successfully: {backup_path}")
                return True
            else:
                logger.error(f"SQLite database file not found at: {db_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to backup non-PostgreSQL database: {e}")
            return False

def verify_application():
    """Perform basic verification of the application."""
    logger.info("Verifying application health")
    
    # Check database connection again after migrations
    if not check_database_connection():
        logger.error("Application verification failed: Database connection issue")
        return False
    
    # Check if the app can be imported and initialized
    try:
        from app import create_app
        app = create_app('production')
        logger.info("Application verified successfully")
        return True
    except Exception as e:
        logger.error(f"Application verification failed: {e}")
        return False

def main(args):
    """Run the production setup process."""
    logger.info("Starting production environment setup")
    
    # Create necessary directories
    if not create_directory('logs', 'logs'):
        return False
    
    # Check database connection
    if not check_database_connection():
        logger.error("Database connection check failed. Please check your DATABASE_URL environment variable.")
        return False
    
    # Only backup if requested or doing full setup
    if args.backup or not (args.backup or args.migrate):
        if not backup_database():
            logger.warning("Database backup failed, but continuing with setup")
    
    # Only run migrations if requested or doing full setup
    if args.migrate or not (args.backup or args.migrate):
        if not setup_migrations():
            logger.error("Failed to set up database migrations.")
            return False
    
    # Verify application health
    if not args.backup:  # Skip verification if only backing up
        if not verify_application():
            logger.warning("Application verification failed, please check the logs")
    
    logger.info("Production environment setup completed successfully")
    return True

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Production environment setup")
    parser.add_argument('--backup', action='store_true', help='Only backup the database')
    parser.add_argument('--migrate', action='store_true', help='Only run migrations')
    args = parser.parse_args()
    
    success = main(args)
    sys.exit(0 if success else 1)