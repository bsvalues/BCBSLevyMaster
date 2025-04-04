"""
Migration script to add the APICallLog table for API call tracking.

This script adds a table to store historical API call records for monitoring
and analytics purposes. It provides data for:
- API usage statistics and trends
- Performance monitoring and troubleshooting
- Error rate tracking
- Service dependency analysis
"""

import logging
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, MetaData, Table, create_engine, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment or use default
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    exit(1)

# Create engine and metadata
engine = create_engine(DATABASE_URL)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Define the APICallLog model (similar to the one in models.py)
class APICallLog(Base):
    """
    Model for logging historical API calls for monitoring and analytics.
    Stores permanent record of API calls for trend analysis and auditing.
    """
    __tablename__ = 'api_call_log'
    
    id = Column(Integer, primary_key=True)
    service = Column(String(64), nullable=False, index=True)  # e.g. "anthropic", "openai", etc.
    endpoint = Column(String(128), nullable=False, index=True)
    method = Column(String(16), nullable=False)  # HTTP method
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    duration_ms = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, default=False, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    params = Column(JSON, nullable=True)  # Redacted parameters
    response_summary = Column(JSON, nullable=True)  # Summarized response
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_api_call_service_success', 'service', 'success'),
        Index('idx_api_call_timestamp_service', 'timestamp', 'service'),
    )

def run_migration():
    """
    Create the APICallLog table if it doesn't exist.
    """
    try:
        # Check if table exists
        if not engine.dialect.has_table(engine.connect(), 'api_call_log'):
            # Create the table
            metadata.create_all(engine, tables=[APICallLog.__table__])
            logger.info("APICallLog table created successfully")
        else:
            logger.info("APICallLog table already exists")
            
        # Verify the table was created
        if engine.dialect.has_table(engine.connect(), 'api_call_log'):
            logger.info("Verified APICallLog table exists")
            return True
        else:
            logger.error("Failed to create APICallLog table")
            return False
            
    except Exception as e:
        logger.error(f"Error creating APICallLog table: {str(e)}")
        return False
        
if __name__ == "__main__":
    logger.info("Running migration to add APICallLog table")
    success = run_migration()
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        exit(1)