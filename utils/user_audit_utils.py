"""
User Audit Utilities

This module provides functions for tracking and managing user actions and levy overrides.
It includes:
- Functions for recording user actions
- Functions for tracking and validating levy overrides
- Helper functions for user audit analytics
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from functools import wraps

from flask import request, g, session, current_app
from flask_login import current_user
from sqlalchemy import func, desc, and_, or_

from app import db
from models import UserActionLog, LevyOverrideLog, User

# Set up logger
logger = logging.getLogger(__name__)

def log_user_action(
    action_type: str,
    module: str,
    submodule: Optional[str] = None,
    action_details: Optional[Dict[str, Any]] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    duration_ms: Optional[float] = None
) -> Optional[UserActionLog]:
    """
    Log a user action to the database.
    
    Args:
        action_type: Type of action (VIEW, SEARCH, EXPORT, CALCULATE, etc.)
        module: Module where action occurred (levy_calculator, reports, admin, etc.)
        submodule: Specific feature within module (optional)
        action_details: Additional details about the action (optional)
        entity_type: Type of entity being acted upon (tax_district, property, etc.)
        entity_id: ID of the entity being acted upon (optional)
        success: Whether the action succeeded (default: True)
        error_message: Error message if action failed (optional)
        duration_ms: How long the action took in milliseconds (optional)
        
    Returns:
        The created UserActionLog instance or None if creation failed
    """
    try:
        # Get user ID if available
        user_id = getattr(current_user, 'id', None) if current_user and current_user.is_authenticated else None
        
        # Create log entry
        log_entry = UserActionLog(
            user_id=user_id,
            action_type=action_type,
            module=module,
            submodule=submodule,
            action_details=action_details,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request and request.user_agent else None,
            session_id=session.get('_id') if session else None,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        # Add to database
        db.session.add(log_entry)
        db.session.commit()
        
        return log_entry
    except Exception as e:
        logger.error(f"Error logging user action: {str(e)}")
        db.session.rollback()
        return None

def track_action(action_type: str, module: str, submodule: Optional[str] = None):
    """
    Decorator to track a function call as a user action.
    
    Args:
        action_type: Type of action (VIEW, SEARCH, EXPORT, CALCULATE, etc.)
        module: Module where action occurred (levy_calculator, reports, admin, etc.)
        submodule: Specific feature within module (optional)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Get entity information from kwargs if available
                entity_type = kwargs.get('entity_type')
                entity_id = kwargs.get('entity_id')
                
                # For common patterns, try to extract entity info from positional args
                if not entity_type and not entity_id and len(args) > 0:
                    if 'tax_district' in func.__name__ and 'district_id' in kwargs:
                        entity_type = 'tax_district'
                        entity_id = kwargs.get('district_id')
                    elif 'tax_code' in func.__name__ and 'code_id' in kwargs:
                        entity_type = 'tax_code'
                        entity_id = kwargs.get('code_id')
                    elif 'property' in func.__name__ and 'property_id' in kwargs:
                        entity_type = 'property'
                        entity_id = kwargs.get('property_id')
                
                # Log the action
                log_user_action(
                    action_type=action_type,
                    module=module,
                    submodule=submodule,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    success=success,
                    error_message=error_message,
                    duration_ms=duration_ms
                )
        
        return wrapper
    
    return decorator

def log_levy_override(
    user_id: int,
    tax_district_id: Optional[int] = None,
    tax_code_id: Optional[int] = None,
    year: Optional[int] = None,
    field_name: Optional[str] = None,
    original_value: Optional[float] = None,
    override_value: Optional[float] = None,
    justification: Optional[str] = None,
    requires_approval: bool = False,
    calculation_params: Optional[Dict[str, Any]] = None
) -> Optional[LevyOverrideLog]:
    """
    Log a levy override to the database.
    
    Args:
        user_id: ID of the user making the override
        tax_district_id: ID of the tax district (optional if tax_code_id provided)
        tax_code_id: ID of the tax code (optional if tax_district_id provided)
        year: Year of the levy data
        field_name: The field that was overridden
        original_value: The calculated value
        override_value: The user-provided value
        justification: User's reason for override (optional)
        requires_approval: Whether override requires approval (default: False)
        calculation_params: Parameters used in original calculation (optional)
        
    Returns:
        The created LevyOverrideLog instance or None if creation failed
    """
    try:
        # Calculate percentage change
        if original_value is not None and override_value is not None and original_value != 0:
            percent_change = ((override_value - original_value) / original_value) * 100
        else:
            percent_change = None
        
        # Auto-determine if approval is required based on percentage change
        if not requires_approval and percent_change is not None:
            # If change is more than 5%, require approval
            if abs(percent_change) > 5:
                requires_approval = True
        
        # Create override log
        override_log = LevyOverrideLog(
            user_id=user_id,
            tax_district_id=tax_district_id,
            tax_code_id=tax_code_id,
            year=year,
            field_name=field_name,
            original_value=original_value,
            override_value=override_value,
            percent_change=percent_change,
            justification=justification,
            requires_approval=requires_approval,
            calculation_params=calculation_params
        )
        
        # Add to database
        db.session.add(override_log)
        db.session.commit()
        
        return override_log
    except Exception as e:
        logger.error(f"Error logging levy override: {str(e)}")
        db.session.rollback()
        return None

def get_user_activity_summary(user_id: int, days: int = 30) -> Dict[str, Any]:
    """
    Get a summary of a user's activity over the specified period.
    
    Args:
        user_id: ID of the user
        days: Number of days to include in summary (default: 30)
        
    Returns:
        Dictionary with activity summary
    """
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Total actions
    total_actions = UserActionLog.query.filter_by(
        user_id=user_id
    ).filter(
        UserActionLog.timestamp >= since_date
    ).count()
    
    # Actions by module
    module_counts = db.session.query(
        UserActionLog.module,
        func.count(UserActionLog.id).label("count")
    ).filter(
        UserActionLog.user_id == user_id,
        UserActionLog.timestamp >= since_date
    ).group_by(
        UserActionLog.module
    ).order_by(
        func.count(UserActionLog.id).desc()
    ).all()
    
    # Actions by type
    action_counts = db.session.query(
        UserActionLog.action_type,
        func.count(UserActionLog.id).label("count")
    ).filter(
        UserActionLog.user_id == user_id,
        UserActionLog.timestamp >= since_date
    ).group_by(
        UserActionLog.action_type
    ).order_by(
        func.count(UserActionLog.id).desc()
    ).all()
    
    # Error rate
    error_count = UserActionLog.query.filter_by(
        user_id=user_id,
        success=False
    ).filter(
        UserActionLog.timestamp >= since_date
    ).count()
    
    error_rate = (error_count / total_actions) * 100 if total_actions > 0 else 0
    
    # Recent overrides
    overrides = LevyOverrideLog.query.filter_by(
        user_id=user_id
    ).filter(
        LevyOverrideLog.timestamp >= since_date
    ).count()
    
    return {
        "total_actions": total_actions,
        "modules": {m.module: m.count for m in module_counts},
        "action_types": {a.action_type: a.count for a in action_counts},
        "error_count": error_count,
        "error_rate": error_rate,
        "override_count": overrides
    }

def get_pending_levy_overrides(limit: int = 10) -> List[LevyOverrideLog]:
    """
    Get pending levy overrides that require approval.
    
    Args:
        limit: Maximum number of overrides to return (default: 10)
        
    Returns:
        List of LevyOverrideLog instances
    """
    return LevyOverrideLog.query.filter_by(
        requires_approval=True,
        approved=None
    ).order_by(
        LevyOverrideLog.timestamp.desc()
    ).limit(limit).all()

def get_system_activity_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get a summary of system activity over the specified period.
    
    Args:
        days: Number of days to include in summary (default: 7)
        
    Returns:
        Dictionary with activity summary
    """
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Total actions
    total_actions = UserActionLog.query.filter(
        UserActionLog.timestamp >= since_date
    ).count()
    
    # Active users
    active_users = db.session.query(
        UserActionLog.user_id
    ).distinct().filter(
        UserActionLog.timestamp >= since_date,
        UserActionLog.user_id != None
    ).count()
    
    # Actions by module
    module_counts = db.session.query(
        UserActionLog.module,
        func.count(UserActionLog.id).label("count")
    ).filter(
        UserActionLog.timestamp >= since_date
    ).group_by(
        UserActionLog.module
    ).order_by(
        func.count(UserActionLog.id).desc()
    ).all()
    
    # Top users
    top_users = db.session.query(
        UserActionLog.user_id,
        User.username,
        func.count(UserActionLog.id).label("count")
    ).join(
        User, UserActionLog.user_id == User.id
    ).filter(
        UserActionLog.timestamp >= since_date,
        UserActionLog.user_id != None
    ).group_by(
        UserActionLog.user_id, User.username
    ).order_by(
        func.count(UserActionLog.id).desc()
    ).limit(5).all()
    
    # Error rate
    error_count = UserActionLog.query.filter_by(
        success=False
    ).filter(
        UserActionLog.timestamp >= since_date
    ).count()
    
    error_rate = (error_count / total_actions) * 100 if total_actions > 0 else 0
    
    # Override summary
    overrides = LevyOverrideLog.query.filter(
        LevyOverrideLog.timestamp >= since_date
    ).count()
    
    pending_overrides = LevyOverrideLog.query.filter_by(
        requires_approval=True,
        approved=None
    ).filter(
        LevyOverrideLog.timestamp >= since_date
    ).count()
    
    return {
        "total_actions": total_actions,
        "active_users": active_users,
        "modules": {m.module: m.count for m in module_counts},
        "top_users": [{"id": u.user_id, "username": u.username, "count": u.count} for u in top_users],
        "error_count": error_count,
        "error_rate": error_rate,
        "override_count": overrides,
        "pending_overrides": pending_overrides
    }