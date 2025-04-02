#!/usr/bin/env python3
"""
Simple PostgreSQL backup tool.

This script creates a backup of the PostgreSQL database in a compressed format.

Usage:
    python pg_backup.py [--output-dir DIRECTORY]

Options:
    --output-dir DIR  Custom directory for backups (default: ./backups)
"""

import os
import sys
import logging
import argparse
import datetime
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            logger.info(f"Created directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    return True

def backup_database(backup_dir=None):
    """
    Create a backup of the PostgreSQL database.
    
    Args:
        backup_dir: Directory to save the backup (default: ./backups)
        
    Returns:
        Tuple of (success, filepath)
    """
    # Use default backup directory if not specified
    backup_dir = backup_dir or os.path.join(os.getcwd(), 'backups')
    
    # Create the backup directory if it doesn't exist
    if not create_directory(backup_dir):
        return False, None
    
    # Get PostgreSQL connection parameters from environment
    pg_host = os.environ.get('PGHOST')
    pg_port = os.environ.get('PGPORT', '5432')
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('PGPASSWORD')
    pg_database = os.environ.get('PGDATABASE')
    
    # Check if we have all required parameters
    if not all([pg_host, pg_user, pg_password, pg_database]):
        logger.error("Missing PostgreSQL connection parameters in environment variables")
        return False, None
    
    # Generate backup filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"pg_backup_{timestamp}.sql"
    backup_filepath = os.path.join(backup_dir, backup_filename)
    
    # Create backup command - using plaintext format to avoid version mismatch issues
    pg_dump_cmd = f"PGPASSWORD='{pg_password}' pg_dump -h {pg_host} -p {pg_port} -U {pg_user} " \
                  f"-d {pg_database} -v -F p -f {backup_filepath}"
    
    # Execute the backup command
    logger.info(f"Creating backup of {pg_database} database...")
    try:
        result = subprocess.run(
            pg_dump_cmd,
            shell=True,
            check=True,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Verify the backup was successful
        if os.path.exists(backup_filepath) and os.path.getsize(backup_filepath) > 0:
            backup_size = os.path.getsize(backup_filepath) / (1024 * 1024)  # Convert to MB
            logger.info(f"Backup created successfully: {backup_filepath} ({backup_size:.2f} MB)")
            return True, backup_filepath
        else:
            logger.error("Backup file is empty or does not exist")
            return False, None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {e.stderr}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error during backup: {e}")
        return False, None

def main():
    """Run the database backup."""
    parser = argparse.ArgumentParser(
        description="Simple PostgreSQL backup tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--output-dir', 
                       help='Custom directory for backups (default: ./backups)')
    
    args = parser.parse_args()
    
    # Perform the backup
    success, backup_file = backup_database(args.output_dir)
    
    if success:
        logger.info("Database backup completed successfully")
        sys.exit(0)
    else:
        logger.error("Database backup failed")
        sys.exit(1)

if __name__ == '__main__':
    main()