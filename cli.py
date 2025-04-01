"""
Command-line interface extensions for the Levy Calculation Application.

This module provides custom CLI commands for the Flask application to help
with database management, migrations, and other administrative tasks.
"""

import os
import sys
import click
import logging
from datetime import datetime
from flask import current_app
from flask.cli import with_appcontext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@click.group()
def db_utils():
    """Database utilities for the Levy Calculation Application."""
    pass

@db_utils.command()
@with_appcontext
def backup():
    """Backup the database to a file."""
    from app import db
    
    # Create backups directory if it doesn't exist
    if not os.path.exists('backups'):
        os.makedirs('backups')
        logger.info("Created backups directory")
    
    # Get the current timestamp for the backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backups/database_backup_{timestamp}.sql"
    
    # Get database connection parameters from environment
    pg_host = os.environ.get('PGHOST')
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('PGPASSWORD')
    pg_database = os.environ.get('PGDATABASE')
    
    if not all([pg_host, pg_user, pg_password, pg_database]):
        logger.error("Database environment variables not set")
        sys.exit(1)
    
    # Build the pg_dump command
    pg_dump_cmd = f"PGPASSWORD='{pg_password}' pg_dump -h {pg_host} -U {pg_user} -d {pg_database} -f {backup_filename}"
    
    # Run the backup command
    try:
        logger.info("Starting database backup")
        os.system(pg_dump_cmd)
        logger.info(f"Database backup created successfully: {backup_filename}")
    except Exception as e:
        logger.error(f"Failed to create database backup: {str(e)}")
        sys.exit(1)

@db_utils.command()
@click.argument('backup_file', type=click.Path(exists=True))
@with_appcontext
def restore(backup_file):
    """Restore the database from a backup file."""
    from app import db
    
    # Get database connection parameters from environment
    pg_host = os.environ.get('PGHOST')
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('PGPASSWORD')
    pg_database = os.environ.get('PGDATABASE')
    
    if not all([pg_host, pg_user, pg_password, pg_database]):
        logger.error("Database environment variables not set")
        sys.exit(1)
    
    # Confirm with user
    click.confirm(f"This will overwrite the current database with {backup_file}. Do you want to continue?", abort=True)
    
    # Build the psql command for restoration
    psql_cmd = f"PGPASSWORD='{pg_password}' psql -h {pg_host} -U {pg_user} -d {pg_database} -f {backup_file}"
    
    # Run the restore command
    try:
        logger.info(f"Restoring database from {backup_file}")
        os.system(psql_cmd)
        logger.info("Database restored successfully")
    except Exception as e:
        logger.error(f"Failed to restore database: {str(e)}")
        sys.exit(1)

@db_utils.command()
@with_appcontext
def health_check():
    """Check the health of the database connection."""
    from app import db
    from sqlalchemy import text
    
    try:
        # Execute a simple query to check the connection
        result = db.session.execute(text("SELECT version()"))
        version = result.scalar()
        logger.info(f"Database connection successful. PostgreSQL version: {version}")
        
        # Get table counts for key tables
        tables = [
            "user", "tax_district", "tax_code", "property", 
            "import_log", "export_log", "tax_code_historical_rate"
        ]
        
        logger.info("Table counts:")
        for table in tables:
            try:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"  {table}: {count} rows")
            except Exception as e:
                logger.warning(f"  {table}: Unable to count rows - {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False

@db_utils.command()
@with_appcontext
def prune_logs():
    """Prune old database logs beyond specified retention period."""
    from app import db
    from sqlalchemy import text
    
    # Default to 90 days retention
    retention_days = int(os.environ.get('LOG_RETENTION_DAYS', 90))
    
    try:
        # Prune import logs
        result = db.session.execute(
            text(f"DELETE FROM import_log WHERE created_at < NOW() - INTERVAL '{retention_days} days'")
        )
        import_deleted = result.rowcount
        
        # Prune export logs
        result = db.session.execute(
            text(f"DELETE FROM export_log WHERE created_at < NOW() - INTERVAL '{retention_days} days'")
        )
        export_deleted = result.rowcount
        
        db.session.commit()
        
        logger.info(f"Pruned {import_deleted} import logs and {export_deleted} export logs older than {retention_days} days")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to prune logs: {str(e)}")
        sys.exit(1)

# Register the commands with Flask
def register_commands(app):
    """Register custom commands with the Flask application."""
    app.cli.add_command(db_utils)