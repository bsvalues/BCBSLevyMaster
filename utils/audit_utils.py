"""
Audit Trail Utilities

This module provides functionality for tracking and managing audit logs.
It implements:
- Methods for recording data changes
- Audit log retrieval and formatting
- Audit summary generation
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Type

from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session

from app import db
from models import AuditLog

# Set up logger
logger = logging.getLogger(__name__)

def record_audit_log(
    table_name: str,
    record_id: int,
    action: str,
    changes: Optional[List[Dict[str, Any]]] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Record an audit log entry.
    
    Args:
        table_name: Name of the table being modified
        record_id: ID of the record being modified
        action: Action taken (CREATE, UPDATE, DELETE)
        changes: Optional list of changes made (field, old_value, new_value)
        user_id: Optional ID of the user making the change
        ip_address: Optional IP address of the user
        
    Returns:
        Created AuditLog instance
    """
    log = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        changes=json.dumps(changes) if changes else None,
        user_id=user_id,
        ip_address=ip_address
    )
    
    db.session.add(log)
    db.session.commit()
    
    logger.info(f"Recorded audit log for {action} on {table_name} #{record_id}")
    return log

def get_audit_logs_for_record(table_name: str, record_id: int) -> List[AuditLog]:
    """
    Get all audit logs for a specific record.
    
    Args:
        table_name: Name of the table
        record_id: ID of the record
        
    Returns:
        List of AuditLog instances
    """
    return AuditLog.query.filter_by(
        table_name=table_name,
        record_id=record_id
    ).order_by(AuditLog.timestamp.desc()).all()

def get_audit_logs_by_action(action: str, limit: int = 100) -> List[AuditLog]:
    """
    Get audit logs for a specific action.
    
    Args:
        action: Action to filter by (CREATE, UPDATE, DELETE)
        limit: Maximum number of logs to return
        
    Returns:
        List of AuditLog instances
    """
    return AuditLog.query.filter_by(
        action=action
    ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

def get_recent_audit_logs(days: int = 7, limit: int = 100) -> List[AuditLog]:
    """
    Get recent audit logs.
    
    Args:
        days: Number of past days to include
        limit: Maximum number of logs to return
        
    Returns:
        List of AuditLog instances
    """
    since_date = datetime.utcnow() - timedelta(days=days)
    
    return AuditLog.query.filter(
        AuditLog.timestamp >= since_date
    ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

def get_audit_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get a summary of audit activity.
    
    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        
    Returns:
        Dictionary with audit summary statistics
    """
    query = AuditLog.query
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    # Get total count
    total_logs = query.count()
    
    # Get count by action
    create_count = query.filter_by(action='CREATE').count()
    update_count = query.filter_by(action='UPDATE').count()
    delete_count = query.filter_by(action='DELETE').count()
    
    # Get count by table
    table_counts = {}
    table_query = db.session.query(
        AuditLog.table_name,
        func.count(AuditLog.id)
    ).group_by(AuditLog.table_name)
    
    if start_date:
        table_query = table_query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        table_query = table_query.filter(AuditLog.timestamp <= end_date)
    
    table_results = table_query.all()
    
    for table_name, count in table_results:
        table_counts[table_name] = count
    
    # Get recent activity
    recent_logs = query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    return {
        'total_logs': total_logs,
        'create_count': create_count,
        'update_count': update_count,
        'delete_count': delete_count,
        'tables': table_counts,
        'recent_logs': [format_audit_log_for_display(log) for log in recent_logs]
    }

def format_audit_log_for_display(log: AuditLog) -> Dict[str, Any]:
    """
    Format an audit log for display.
    
    Args:
        log: AuditLog instance
        
    Returns:
        Dictionary with formatted audit log data
    """
    result = {
        'id': log.id,
        'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'table': log.table_name,
        'record_id': log.record_id,
        'action': log.action,
        'user_id': log.user_id,
        'ip_address': log.ip_address
    }
    
    # Parse changes if available
    if log.changes:
        try:
            changes = json.loads(log.changes)
            result['changes'] = changes
        except (json.JSONDecodeError, TypeError):
            result['changes'] = []
    else:
        result['changes'] = []
    
    return result

def track_model_changes(model, table_name: str, record_id: int, action: str, user_id: Optional[int] = None) -> None:
    """
    Track changes to a model instance.
    This should be called from before_update, after_insert, and before_delete events.
    
    Args:
        model: SQLAlchemy model instance
        table_name: Name of the table
        record_id: ID of the record
        action: Action (CREATE, UPDATE, DELETE)
        user_id: Optional ID of the user making the change
    """
    # For updates, get the changes
    changes = []
    
    if action == 'UPDATE':
        # Get the changed attributes
        for attr in model.__mapper__.attrs.keys():
            if hasattr(model, f'_{attr}_previous_value'):
                old_value = getattr(model, f'_{attr}_previous_value')
                new_value = getattr(model, attr)
                
                # Skip if values are the same
                if old_value == new_value:
                    continue
                
                # Handle datetime objects
                if isinstance(old_value, datetime):
                    old_value = old_value.isoformat()
                if isinstance(new_value, datetime):
                    new_value = new_value.isoformat()
                
                changes.append({
                    'field': attr,
                    'old_value': old_value,
                    'new_value': new_value
                })
    
    # Record the audit log
    record_audit_log(
        table_name=table_name,
        record_id=record_id,
        action=action,
        changes=changes if changes else None,
        user_id=user_id
    )

def setup_model_audit_hooks(model_class: Type, table_name: Optional[str] = None) -> None:
    """
    Set up audit hooks for a model class.
    
    Args:
        model_class: SQLAlchemy model class
        table_name: Optional table name override (defaults to model's __tablename__)
    """
    from sqlalchemy import event
    
    if not table_name:
        table_name = model_class.__tablename__
    
    # Before update, capture the original values
    @event.listens_for(model_class, 'before_update')
    def before_update(mapper, connection, target):
        state = db.inspect(target)
        
        # Store original values for changed fields
        for attr in state.attrs:
            if not state.attrs[attr.key].history.has_changes():
                continue
            
            # Store the previous value as a "private" attribute
            old_value = state.attrs[attr.key].value
            setattr(target, f'_{attr.key}_previous_value', old_value)
    
    # After update, record the changes
    @event.listens_for(model_class, 'after_update')
    def after_update(mapper, connection, target):
        track_model_changes(target, table_name, target.id, 'UPDATE')
    
    # After insert, record the creation
    @event.listens_for(model_class, 'after_insert')
    def after_insert(mapper, connection, target):
        track_model_changes(target, table_name, target.id, 'CREATE')
    
    # Before delete, record the deletion
    @event.listens_for(model_class, 'before_delete')
    def before_delete(mapper, connection, target):
        track_model_changes(target, table_name, target.id, 'DELETE')