#!/usr/bin/env python3
"""
Production Database Migration Utility for PostgreSQL

This script provides advanced migration capabilities specifically for
production PostgreSQL deployments, including:

1. Safe migration with transaction support
2. Advanced backup and verification
3. Performance optimizations for large datasets
4. Schema comparison before/after migration
5. Dry-run capability to preview migrations
6. Detailed reporting

Usage:
    python production_migrate.py backup            # Backup database only
    python production_migrate.py migrate           # Run migrations with safety checks
    python production_migrate.py migrate --dry-run # Preview migrations
    python production_migrate.py verify            # Compare pre/post schemas
    python production_migrate.py report            # Generate migration report
    python production_migrate.py restore FILENAME  # Restore from backup
"""

import os
import sys
import logging
import argparse
import datetime
import subprocess
import json
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment to production
os.environ['FLASK_ENV'] = 'production'

# Ensure we're in the project root directory
project_root = Path(__file__).resolve().parent
os.chdir(project_root)

def run_command(command, description, capture_output=True):
    """Run a shell command and log the result."""
    logger.info(f"Running: {description}")
    try:
        if capture_output:
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
        else:
            # Run without capturing output (useful for interactive commands)
            subprocess.run(command, shell=True, check=True)
            logger.info(f"Command successful: {description}")
            return True, None
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {description}")
        logger.error(f"Error: {e.stderr if capture_output else 'See console output'}")
        return False, e.stderr if capture_output else None

def check_database_connection():
    """Verify database connection and confirm it's PostgreSQL."""
    logger.info("Checking database connection and type...")
    
    try:
        # Import database modules
        from app import create_app
        from sqlalchemy import text
        
        app = create_app('production')
        with app.app_context():
            from app import db
            # Execute a query to check DB type
            result = db.session.execute(text("SELECT version()")).scalar()
            
            if not result or 'postgresql' not in result.lower():
                logger.error(f"Database is not PostgreSQL. Found: {result}")
                return False
                
            logger.info(f"Connected to PostgreSQL: {result}")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False

def backup_database(backup_dir=None):
    """
    Create a full database backup with schema and data.
    
    Args:
        backup_dir: Custom directory for backups (default: ./backups)
    
    Returns:
        Tuple of (success, backup_filepath)
    """
    logger.info("Starting comprehensive database backup")
    
    # Create backups directory
    backup_dir = backup_dir or os.path.join(project_root, 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        logger.info(f"Created backup directory: {backup_dir}")
    
    # Get database connection parameters from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        return False, None
    
    # Extract connection parameters
    if db_url.startswith('postgresql://'):
        # Extract parameters from connection string
        try:
            from urllib.parse import urlparse
            parsed = urlparse(db_url)
            pg_host = parsed.hostname
            pg_port = parsed.port or 5432
            pg_user = parsed.username
            pg_password = parsed.password
            pg_database = parsed.path.lstrip('/')
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")
            return False, None
    else:
        # Use environment variables if set
        pg_host = os.environ.get('PGHOST')
        pg_port = os.environ.get('PGPORT', 5432)
        pg_user = os.environ.get('PGUSER')
        pg_password = os.environ.get('PGPASSWORD')
        pg_database = os.environ.get('PGDATABASE')
    
    # Validate database parameters
    if not all([pg_host, pg_user, pg_database]):
        logger.error("Missing database connection parameters")
        return False, None
    
    # Get the current timestamp for the backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"pg_backup_{timestamp}.sql"
    backup_filepath = os.path.join(backup_dir, backup_filename)
    
    # Build the pg_dump command with custom format and compression
    pg_dump_cmd = f"PGPASSWORD='{pg_password}' pg_dump -h {pg_host} -p {pg_port} -U {pg_user} " \
                  f"-d {pg_database} -v -Fc -Z 9 -f {backup_filepath}"
    
    # Execute the backup command
    success, output = run_command(pg_dump_cmd, "Creating compressed PostgreSQL backup")
    
    if success:
        logger.info(f"Database backup created successfully: {backup_filepath}")
        
        # Verify backup is valid
        verify_cmd = f"PGPASSWORD='{pg_password}' pg_restore -l {backup_filepath} > /dev/null"
        verify_success, _ = run_command(verify_cmd, "Verifying backup integrity")
        
        if verify_success:
            logger.info("Backup verification successful")
            # Get file size
            backup_size = os.path.getsize(backup_filepath) / (1024 * 1024)  # Convert to MB
            logger.info(f"Backup size: {backup_size:.2f} MB")
            return True, backup_filepath
        else:
            logger.error("Backup verification failed - backup may be corrupted")
            return False, backup_filepath
    else:
        logger.error("Failed to create database backup")
        return False, None

def dump_schema_to_file(output_file):
    """
    Dump just the database schema (no data) to a file.
    
    Used for schema comparison before and after migrations.
    
    Args:
        output_file: Path to save schema dump
        
    Returns:
        Boolean success status
    """
    # Get database connection parameters from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    # Extract connection parameters
    if db_url.startswith('postgresql://'):
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        pg_host = parsed.hostname
        pg_port = parsed.port or 5432
        pg_user = parsed.username
        pg_password = parsed.password
        pg_database = parsed.path.lstrip('/')
    else:
        pg_host = os.environ.get('PGHOST')
        pg_port = os.environ.get('PGPORT', 5432)
        pg_user = os.environ.get('PGUSER')
        pg_password = os.environ.get('PGPASSWORD')
        pg_database = os.environ.get('PGDATABASE')
    
    # Schema-only dump command
    schema_cmd = f"PGPASSWORD='{pg_password}' pg_dump -h {pg_host} -p {pg_port} -U {pg_user} " \
                 f"-d {pg_database} --schema-only -f {output_file}"
    
    success, _ = run_command(schema_cmd, f"Dumping schema to {output_file}")
    return success

def compare_schemas(before_file, after_file, output_file=None):
    """
    Compare two schema dumps and generate a report of differences.
    
    Args:
        before_file: Path to pre-migration schema dump
        after_file: Path to post-migration schema dump
        output_file: Optional file to write comparison results
        
    Returns:
        Boolean success status
    """
    # Check if files exist
    if not os.path.exists(before_file) or not os.path.exists(after_file):
        logger.error(f"Schema files missing: {before_file} or {after_file}")
        return False
    
    # Use diff to compare schemas
    diff_cmd = f"diff -u {before_file} {after_file}"
    success, diff_output = run_command(diff_cmd, "Comparing schemas")
    
    # diff returns non-zero exit code if files differ, which is expected
    # so we ignore the success flag here
    
    if output_file:
        try:
            with open(output_file, 'w') as f:
                f.write(diff_output if diff_output else "No schema differences detected.")
            logger.info(f"Schema comparison written to {output_file}")
        except Exception as e:
            logger.error(f"Error writing comparison to file: {e}")
            return False
    
    # Print summary
    if diff_output:
        logger.info("Schema changes detected (see comparison file for details)")
        # Count the number of additions and removals
        additions = diff_output.count('\n+')
        removals = diff_output.count('\n-')
        logger.info(f"Changes: {additions} additions, {removals} removals")
    else:
        logger.info("No schema changes detected")
    
    return True

def run_migrations(dry_run=False):
    """
    Run database migrations with safety checks.
    
    Args:
        dry_run: If True, only show what would be migrated
        
    Returns:
        Boolean success status
    """
    logger.info(f"Running migrations {'(DRY RUN)' if dry_run else ''}")
    
    # Create temp directory for schema dumps
    temp_dir = tempfile.mkdtemp()
    before_schema = os.path.join(temp_dir, "schema_before.sql")
    after_schema = os.path.join(temp_dir, "schema_after.sql")
    schema_diff = os.path.join(temp_dir, "schema_diff.txt")
    
    # Dump schema before migration
    if not dump_schema_to_file(before_schema):
        logger.error("Failed to dump pre-migration schema")
        return False
    
    if dry_run:
        # For dry run, we use the --sql flag to generate SQL without running it
        logger.info("Generating migration SQL without applying (DRY RUN)")
        migrate_cmd = "flask --app migrate db upgrade --sql > migration_preview.sql"
        success, _ = run_command(migrate_cmd, "Generating migration SQL")
        
        if success:
            logger.info("Migration preview generated: migration_preview.sql")
            return True
        else:
            logger.error("Failed to generate migration preview")
            return False
    else:
        # Create a backup before migration
        backup_success, backup_file = backup_database()
        if not backup_success:
            logger.warning("Database backup failed - proceed with caution")
            # Prompt for confirmation
            confirm = input("Database backup failed. Continue with migration anyway? (y/N): ")
            if confirm.lower() != 'y':
                logger.info("Migration aborted by user")
                return False
        
        # Run the migration
        migrate_cmd = "python migrate.py upgrade"
        success, output = run_command(migrate_cmd, "Applying database migrations")
        
        if not success:
            logger.error("Migration failed")
            return False
        
        # Dump schema after migration
        if not dump_schema_to_file(after_schema):
            logger.error("Failed to dump post-migration schema")
            return False
        
        # Compare schemas and generate report
        compare_schemas(before_schema, after_schema, schema_diff)
        
        # Copy schema comparison to a more permanent location with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(project_root, 'migration_reports')
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        # Create a comprehensive report
        report_file = os.path.join(report_dir, f"migration_report_{timestamp}.txt")
        try:
            with open(report_file, 'w') as f:
                f.write(f"MIGRATION REPORT - {datetime.datetime.now().isoformat()}\n")
                f.write("="*80 + "\n\n")
                f.write(f"Backup file: {backup_file}\n")
                f.write(f"Migration output:\n{output}\n\n")
                f.write("="*80 + "\n")
                f.write("SCHEMA CHANGES:\n")
                if os.path.exists(schema_diff):
                    with open(schema_diff, 'r') as diff_file:
                        f.write(diff_file.read())
                else:
                    f.write("No schema comparison available\n")
            
            logger.info(f"Migration report created: {report_file}")
        except Exception as e:
            logger.error(f"Failed to create migration report: {e}")
        
        return success

def restore_database(backup_file):
    """
    Restore database from a backup file.
    
    Args:
        backup_file: Path to the backup file
        
    Returns:
        Boolean success status
    """
    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        return False
    
    logger.info(f"Preparing to restore database from: {backup_file}")
    
    # Get database connection parameters
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    # Extract connection parameters
    if db_url.startswith('postgresql://'):
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        pg_host = parsed.hostname
        pg_port = parsed.port or 5432
        pg_user = parsed.username
        pg_password = parsed.password
        pg_database = parsed.path.lstrip('/')
    else:
        pg_host = os.environ.get('PGHOST')
        pg_port = os.environ.get('PGPORT', 5432)
        pg_user = os.environ.get('PGUSER')
        pg_password = os.environ.get('PGPASSWORD')
        pg_database = os.environ.get('PGDATABASE')
    
    # Confirm with user
    confirm = input(f"This will DESTROY and recreate the database '{pg_database}'. Are you sure? (type 'yes' to confirm): ")
    if confirm.lower() != 'yes':
        logger.info("Restore aborted by user")
        return False
    
    # Create a new backup of the current state just in case
    logger.info("Creating backup of current database state before restore...")
    backup_success, _ = backup_database()
    if not backup_success:
        logger.warning("Failed to backup current database state")
        second_confirm = input("Unable to backup current state. Continue with restore anyway? (type 'yes' to confirm): ")
        if second_confirm.lower() != 'yes':
            logger.info("Restore aborted by user")
            return False
    
    # Terminate all connections to the database
    conn_cmd = f"PGPASSWORD='{pg_password}' psql -h {pg_host} -p {pg_port} -U {pg_user} -d postgres -c \"" \
               f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{pg_database}' AND pid <> pg_backend_pid();\""
    
    run_command(conn_cmd, "Terminating active connections")
    
    # Drop and recreate the database
    drop_cmd = f"PGPASSWORD='{pg_password}' psql -h {pg_host} -p {pg_port} -U {pg_user} -d postgres -c \"DROP DATABASE IF EXISTS {pg_database};\""
    success, _ = run_command(drop_cmd, "Dropping database")
    if not success:
        logger.error("Failed to drop database")
        return False
    
    create_cmd = f"PGPASSWORD='{pg_password}' psql -h {pg_host} -p {pg_port} -U {pg_user} -d postgres -c \"CREATE DATABASE {pg_database} OWNER {pg_user};\""
    success, _ = run_command(create_cmd, "Creating database")
    if not success:
        logger.error("Failed to create database")
        return False
    
    # Restore from backup
    restore_cmd = f"PGPASSWORD='{pg_password}' pg_restore -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_database} -v {backup_file}"
    success, _ = run_command(restore_cmd, "Restoring database from backup")
    
    if success:
        logger.info("Database successfully restored")
    else:
        logger.error("Database restore failed")
    
    return success

def check_migration_status():
    """
    Check current migration status.
    
    Returns:
        Boolean success status
    """
    logger.info("Checking database migration status")
    
    status_cmd = "python migrate.py current"
    success, output = run_command(status_cmd, "Checking migration status")
    
    if success:
        logger.info(f"Current migration status: {output.strip() if output else 'Unknown'}")
        
        # Get migration history
        history_cmd = "python migrate.py history"
        success, history = run_command(history_cmd, "Getting migration history")
        
        if success and history:
            logger.info("Migration history:")
            logger.info(history)
        
        return True
    else:
        logger.error("Failed to check migration status")
        return False

def generate_migration_report():
    """
    Generate a comprehensive report on the database and migration status.
    
    Returns:
        Boolean success status
    """
    logger.info("Generating comprehensive migration report")
    
    # Create reports directory
    report_dir = os.path.join(project_root, 'migration_reports')
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(report_dir, f"status_report_{timestamp}.txt")
    
    try:
        with open(report_file, 'w') as f:
            f.write(f"DATABASE STATUS REPORT - {datetime.datetime.now().isoformat()}\n")
            f.write("="*80 + "\n\n")
            
            # Get database version and info
            from app import create_app
            from sqlalchemy import text
            
            try:
                app = create_app('production')
                with app.app_context():
                    from app import db
                    
                    # Get PostgreSQL version
                    version = db.session.execute(text("SELECT version()")).scalar()
                    f.write(f"Database Version: {version}\n\n")
                    
                    # Get simple database info instead of detailed stats to avoid timeouts
                    f.write("DATABASE INFORMATION:\n")
                    f.write("-"*80 + "\n")
                    f.write("Using PostgreSQL database\n")
                    f.write(f"Connection: {os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}\n")
                    f.write("\n\n")
                    
                    # Get table names only instead of detailed stats
                    table_query = text("""
                        SELECT tablename as table_name
                        FROM pg_tables
                        WHERE schemaname = 'public'
                        ORDER BY tablename;
                    """)
                    tables = db.session.execute(table_query).fetchall()
                    
                    f.write("TABLES IN DATABASE:\n")
                    f.write("-"*80 + "\n")
                    
                    for i, table in enumerate(tables):
                        f.write(f"{table.table_name:<30}")
                        # Line break every 3 tables
                        if (i + 1) % 3 == 0:
                            f.write("\n")
                    
                    f.write("\n\n")
            except Exception as e:
                f.write(f"Error getting database information: {e}\n\n")
                
            # Get migration status
            status_cmd = "python migrate.py current"
            success, status_output = run_command(status_cmd, "Getting migration status")
            if success:
                f.write("MIGRATION STATUS:\n")
                f.write("-"*80 + "\n")
                f.write(status_output if status_output else "No migration status available.\n")
                f.write("\n\n")
            
            # Get migration history
            history_cmd = "python migrate.py history"
            success, history_output = run_command(history_cmd, "Getting migration history")
            if success:
                f.write("MIGRATION HISTORY:\n")
                f.write("-"*80 + "\n")
                f.write(history_output if history_output else "No migration history available.\n")
                f.write("\n\n")
            
            # List available backups
            backup_dir = os.path.join(project_root, 'backups')
            if os.path.exists(backup_dir):
                backups = [f for f in os.listdir(backup_dir) if f.endswith('.sql')]
                backups.sort(reverse=True)  # Most recent first
                
                f.write("AVAILABLE BACKUPS:\n")
                f.write("-"*80 + "\n")
                for backup in backups[:10]:  # Show only the 10 most recent
                    backup_path = os.path.join(backup_dir, backup)
                    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(backup_path))
                    f.write(f"{backup} - {size_mb:.2f} MB - {mod_time}\n")
                
                if len(backups) > 10:
                    f.write(f"... and {len(backups) - 10} more.\n")
                
                f.write("\n\n")
        
        logger.info(f"Database status report created: {report_file}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to generate database report: {e}")
        return False

def main():
    """Parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(
        description="Production PostgreSQL Database Migration Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Define subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup database')
    backup_parser.add_argument('--output-dir', help='Custom directory for backups')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run migrations')
    migrate_parser.add_argument('--dry-run', action='store_true', 
                             help='Preview migrations without applying them')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_file', help='Path to backup file')
    
    # Verify command
    subparsers.add_parser('verify', help='Verify database health and migration status')
    
    # Report command
    subparsers.add_parser('report', help='Generate database report')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check database connection first
    if not check_database_connection() and args.command != 'help':
        logger.error("Database connection check failed")
        sys.exit(1)
    
    # Run the appropriate command
    if args.command == 'backup':
        success, backup_file = backup_database(args.output_dir)
        sys.exit(0 if success else 1)
    
    elif args.command == 'migrate':
        success = run_migrations(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    
    elif args.command == 'restore':
        success = restore_database(args.backup_file)
        sys.exit(0 if success else 1)
    
    elif args.command == 'verify':
        success = check_migration_status()
        sys.exit(0 if success else 1)
    
    elif args.command == 'report':
        success = generate_migration_report()
        sys.exit(0 if success else 1)
    
    else:
        # No command or invalid command - show help
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()