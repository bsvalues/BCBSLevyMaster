"""
Migration script to add UserActionLog and LevyOverrideLog tables for user activity tracking.

This script adds two tables:
1. UserActionLog - For tracking detailed user interactions with the system
2. LevyOverrideLog - For tracking levy calculation overrides specifically
"""

import os
import sys
import logging
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, 
    ForeignKey, Text, UniqueConstraint, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from sqlalchemy.sql import func

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the declarative base
Base = declarative_base()

class UserActionLog(Base):
    """
    Model for tracking detailed user interactions with the system.
    
    This table provides comprehensive logging of user activities including:
    - Page views and navigation
    - Feature usage
    - Form submissions
    - Data exports
    - System settings changes
    
    It complements the existing AuditLog table which focuses on data changes,
    while this focuses on user behaviors and interactions.
    """
    __tablename__ = 'user_action_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    action_type = Column(String(64), nullable=False, index=True)  # VIEW, SEARCH, EXPORT, CALCULATE, etc.
    module = Column(String(64), nullable=False, index=True)  # levy_calculator, reports, admin, etc.
    submodule = Column(String(64), nullable=True)  # Specific feature within module
    action_details = Column(JSON, nullable=True)  # Details specific to the action
    entity_type = Column(String(64), nullable=True)  # Type of entity being acted upon (tax_district, property, etc.)
    entity_id = Column(Integer, nullable=True)  # ID of the entity being acted upon
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(256), nullable=True)
    session_id = Column(String(128), nullable=True, index=True)
    success = Column(Boolean, default=True, nullable=False, index=True)  # Did the action succeed?
    error_message = Column(Text, nullable=True)  # Error message if action failed
    duration_ms = Column(Float, nullable=True)  # How long the action took
    
    __table_args__ = (
        Index('idx_user_action_type_module', 'action_type', 'module'),
        Index('idx_user_timestamp_action', 'timestamp', 'action_type'),
        Index('idx_user_entity_action', 'entity_type', 'entity_id', 'action_type'),
    )

class LevyOverrideLog(Base):
    """
    Model for tracking levy calculation overrides.
    
    This table specifically tracks instances where users override
    calculated levy values, providing an audit trail for compliance
    and training purposes.
    """
    __tablename__ = 'levy_override_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    tax_district_id = Column(Integer, ForeignKey('tax_district.id'), nullable=True, index=True)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=True, index=True) 
    year = Column(Integer, nullable=False, index=True)
    
    # Fields that can be overridden
    field_name = Column(String(64), nullable=False)  # The field that was overridden
    original_value = Column(Float, nullable=False)  # The calculated value
    override_value = Column(Float, nullable=False)  # The user-provided value
    percent_change = Column(Float, nullable=True)  # Percentage difference
    
    # Approval information
    justification = Column(Text, nullable=True)  # User's reason for override
    requires_approval = Column(Boolean, default=False)  # Whether override requires approval
    approved = Column(Boolean, nullable=True)  # NULL=pending, True=approved, False=rejected
    approver_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    approval_timestamp = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Related data
    calculation_params = Column(JSON, nullable=True)  # Parameters used in original calculation
    
    __table_args__ = (
        Index('idx_override_district_year', 'tax_district_id', 'year'),
        Index('idx_override_approval_status', 'requires_approval', 'approved'),
        Index('idx_override_user_field', 'user_id', 'field_name'),
    )
    
    # Relationships
    user = relationship('User', foreign_keys=[user_id], backref=backref('levy_overrides', lazy='dynamic'))
    approver = relationship('User', foreign_keys=[approver_id], backref=backref('approved_overrides', lazy='dynamic'))


def run_migration():
    """
    Create the UserActionLog and LevyOverrideLog tables if they don't exist.
    """
    try:
        # Get database URL from environment or use default
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///levy.db')
        
        # Create engine
        engine = create_engine(database_url)
        
        # Create tables if they don't exist
        Base.metadata.create_all(engine, checkfirst=True)
        
        logger.info("Migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)