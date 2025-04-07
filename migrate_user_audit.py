"""
Migration script to add UserActionLog and LevyOverrideLog tables
using the Flask application context.
"""

import os
import sys
import logging
from datetime import datetime

from app import create_app, db
from models import UserActionLog, LevyOverrideLog

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """
    Create the UserActionLog and LevyOverrideLog tables if they don't exist.
    """
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Create tables
            db.create_all()
            
            logger.info("Migration completed successfully")
            return True
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)