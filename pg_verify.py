#!/usr/bin/env python3
"""
Simple PostgreSQL verification tool.

This script performs a quick check to verify that the PostgreSQL database
is correctly configured and accessible.

Usage:
    python pg_verify.py
"""

import os
import sys
import logging
import argparse
import datetime
import subprocess
import psycopg2
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_connection_params():
    """
    Extract PostgreSQL connection parameters from environment variables.
    
    Returns:
        Dict with connection parameters or None if not available
    """
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        return None
    
    # Extract parameters from connection string
    if db_url.startswith('postgresql://'):
        try:
            parsed = urlparse(db_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'user': parsed.username,
                'password': parsed.password,
                'database': parsed.path.lstrip('/')
            }
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")
            return None
    else:
        # Use environment variables if set
        host = os.environ.get('PGHOST')
        port = os.environ.get('PGPORT', 5432)
        user = os.environ.get('PGUSER')
        password = os.environ.get('PGPASSWORD')
        database = os.environ.get('PGDATABASE')
        
        # Check if all required parameters are available
        if not all([host, user, password, database]):
            logger.error("Missing required PostgreSQL connection parameters")
            return None
            
        return {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }

def check_postgres_connection():
    """
    Check if we can connect to PostgreSQL.
    
    Returns:
        Boolean indicating success
    """
    params = get_connection_params()
    if not params:
        return False
    
    try:
        logger.info("Testing PostgreSQL connection...")
        conn = psycopg2.connect(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            database=params['database']
        )
        
        # Get PostgreSQL version
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")
            
            # Get list of tables
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            tables = cursor.fetchall()
            
            if tables:
                logger.info(f"Found {len(tables)} tables in database:")
                for i, (table,) in enumerate(tables):
                    if i < 10:  # Show only first 10 tables
                        logger.info(f"  - {table}")
                if len(tables) > 10:
                    logger.info(f"  ... and {len(tables) - 10} more")
            else:
                logger.warning("No tables found in database.")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return False

def main():
    """
    Run the PostgreSQL verification.
    """
    parser = argparse.ArgumentParser(
        description="Simple PostgreSQL verification tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    args = parser.parse_args()
    
    # Perform the check
    success = check_postgres_connection()
    
    if success:
        logger.info("PostgreSQL verification completed successfully")
        sys.exit(0)
    else:
        logger.error("PostgreSQL verification failed")
        sys.exit(1)

if __name__ == '__main__':
    main()