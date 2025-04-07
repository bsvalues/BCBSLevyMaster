"""
Migration script to add the LevyAuditRecord table for storing levy audit results.

This script adds a table to store audit records from the Levy Audit AI Agent,
providing historical tracking of levy audits, compliance checks, and recommendations.
"""

import os
import sys
import logging
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

class LevyAuditRecord(Base):
    """
    Model for storing levy audit records from the Levy Audit AI Agent.
    
    This table tracks all interactions with the Levy Audit Agent,
    including compliance audits, recommendations, and calculation verifications.
    """
    __tablename__ = 'levy_audit_record'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    tax_district_id = Column(Integer, ForeignKey('tax_district.id'), nullable=True, index=True)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=True, index=True)
    year = Column(Integer, nullable=True, index=True)
    audit_type = Column(String(32), nullable=False, index=True)  # COMPLIANCE, RECOMMENDATION, VERIFICATION, QUERY
    full_audit = Column(Boolean, default=False)
    compliance_score = Column(Float, nullable=True)
    query = Column(Text, nullable=True)
    results = Column(JSON, nullable=True)
    status = Column(String(32), default='PENDING', nullable=False)  # PENDING, COMPLETED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    error_details = Column(Text, nullable=True)
    
    # Add indexes for common queries
    __table_args__ = (
        Index('idx_audit_district_year', 'tax_district_id', 'year'),
        Index('idx_audit_type_status', 'audit_type', 'status'),
        Index('idx_audit_user_district', 'user_id', 'tax_district_id'),
    )

def run_migration():
    """
    Create the LevyAuditRecord table if it doesn't exist.
    """
    # Get database URL from environment variable
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        sys.exit(1)
    
    # Create database engine
    engine = create_engine(database_url)
    
    # Check if table already exists
    if engine.dialect.has_table(engine, LevyAuditRecord.__tablename__):
        logger.info(f"Table {LevyAuditRecord.__tablename__} already exists")
        return
    
    # Create the table
    try:
        Base.metadata.create_all(engine, tables=[LevyAuditRecord.__table__])
        logger.info(f"Successfully created table {LevyAuditRecord.__tablename__}")
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()