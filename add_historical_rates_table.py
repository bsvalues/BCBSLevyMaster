"""
Migration script to add the TaxCodeHistoricalRate table for multi-year support.
"""

import os
import sys
import logging
from datetime import datetime

from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey, UniqueConstraint
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy Base
Base = declarative_base()

class TaxCodeHistoricalRate(Base):
    """
    Model for storing historical tax rates for each tax code over multiple years.
    """
    __tablename__ = 'tax_code_historical_rate'
    
    id = Column(Integer, primary_key=True)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    levy_rate = Column(Float, nullable=False)
    levy_amount = Column(Float, nullable=True)
    total_assessed_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Ensure uniqueness of tax_code_id and year combination
    __table_args__ = (
        UniqueConstraint('tax_code_id', 'year', name='uix_tax_code_year'),
    )

def run_migration():
    """
    Create the TaxCodeHistoricalRate table if it doesn't exist.
    """
    # Get database URL from environment variable
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        sys.exit(1)
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        # Import SQLAlchemy inspector
        from sqlalchemy import inspect
        
        # Check if the table already exists
        inspector = inspect(engine)
        if 'tax_code_historical_rate' not in inspector.get_table_names():
            # Create the table
            TaxCodeHistoricalRate.__table__.create(engine)
            logger.info("Created tax_code_historical_rate table")
        else:
            logger.info("tax_code_historical_rate table already exists")
            
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    logger.info("Running migration to add TaxCodeHistoricalRate table...")
    success = run_migration()
    
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)