"""
Data Archiving Utilities

This module provides functionality for archiving data with retention policies.
It implements:
- Methods for creating data snapshots
- Automatic archiving of historical data
- Retention policy enforcement
- Data restore capabilities
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Type

from sqlalchemy import inspect
from sqlalchemy.orm import Query

from app import db
from models import (
    DataArchive, Property, TaxCode, TaxDistrict, 
    TaxCodeHistoricalRate, ImportLog, ExportLog,
    BillImpactEvaluation, BillImpactTaxCode
)

# Set up logger
logger = logging.getLogger(__name__)

# Define model mappings for convenience
MODEL_MAP = {
    'property': Property,
    'tax_code': TaxCode,
    'tax_district': TaxDistrict,
    'tax_code_historical_rate': TaxCodeHistoricalRate,
    'import_log': ImportLog,
    'export_log': ExportLog,
    'bill_impact_evaluation': BillImpactEvaluation,
    'bill_impact_tax_code': BillImpactTaxCode
}

def _convert_model_to_dict(model_instance) -> Dict[str, Any]:
    """
    Convert a model instance to a dictionary.
    
    Args:
        model_instance: SQLAlchemy model instance
        
    Returns:
        Dictionary representation of the model
    """
    data = {}
    for column in inspect(model_instance.__class__).columns:
        value = getattr(model_instance, column.name)
        
        # Handle datetime objects
        if isinstance(value, datetime):
            value = value.isoformat()
        
        data[column.name] = value
    return data

def create_table_archive(table_name: str, 
                        archive_type: str = 'backup', 
                        filter_criteria: Optional[Dict[str, Any]] = None,
                        retention_days: Optional[int] = None,
                        description: Optional[str] = None,
                        created_by: Optional[int] = None) -> DataArchive:
    """
    Create an archive of a table or filtered subset.
    
    Args:
        table_name: Name of the table to archive
        archive_type: Type of archive (backup, year_end, quarterly, etc.)
        filter_criteria: Optional dictionary of filter criteria
        retention_days: Optional number of days to retain the archive
        description: Optional description
        created_by: Optional ID of user creating the archive
        
    Returns:
        Created DataArchive instance
    """
    # Get the model class for the table
    model_class = MODEL_MAP.get(table_name.lower())
    if not model_class:
        raise ValueError(f"Unknown table: {table_name}")
    
    # Build query with filters
    query = model_class.query
    if filter_criteria:
        for key, value in filter_criteria.items():
            if hasattr(model_class, key):
                query = query.filter(getattr(model_class, key) == value)
    
    # Retrieve data
    records = query.all()
    
    # Convert to dictionaries
    data = [_convert_model_to_dict(record) for record in records]
    
    # Create archive
    archive = DataArchive.create_archive(
        table_name=table_name,
        data=data,
        archive_type=archive_type,
        retention_days=retention_days,
        created_by=created_by,
        description=description
    )
    
    logger.info(f"Created archive of {len(data)} records from {table_name}")
    return archive

def create_year_end_archives(year: int, 
                           retention_days: Optional[int] = 365 * 5,  # 5 years default retention
                           created_by: Optional[int] = None) -> List[DataArchive]:
    """
    Create year-end archives for all relevant tables.
    
    Args:
        year: The year to archive
        retention_days: Optional number of days to retain the archives
        created_by: Optional ID of user creating the archives
        
    Returns:
        List of created DataArchive instances
    """
    archives = []
    description = f"Year-end archive for {year}"
    
    # Archive properties
    try:
        archives.append(create_table_archive(
            'property',
            archive_type='year_end',
            retention_days=retention_days,
            description=description,
            created_by=created_by
        ))
    except Exception as e:
        logger.error(f"Error archiving properties: {str(e)}")
    
    # Archive tax codes
    try:
        archives.append(create_table_archive(
            'tax_code',
            archive_type='year_end',
            retention_days=retention_days,
            description=description,
            created_by=created_by
        ))
    except Exception as e:
        logger.error(f"Error archiving tax codes: {str(e)}")
    
    # Archive tax districts for the specific year
    try:
        archives.append(create_table_archive(
            'tax_district',
            archive_type='year_end',
            filter_criteria={'year': year},
            retention_days=retention_days,
            description=description,
            created_by=created_by
        ))
    except Exception as e:
        logger.error(f"Error archiving tax districts: {str(e)}")
    
    # Archive historical rates for the specific year
    try:
        archives.append(create_table_archive(
            'tax_code_historical_rate',
            archive_type='year_end',
            filter_criteria={'year': year},
            retention_days=retention_days,
            description=description,
            created_by=created_by
        ))
    except Exception as e:
        logger.error(f"Error archiving historical rates: {str(e)}")
    
    logger.info(f"Created {len(archives)} year-end archives for {year}")
    return archives

def apply_retention_policies() -> int:
    """
    Apply retention policies to expired archives.
    
    This should be run periodically (e.g., daily) to enforce retention policies.
    
    Returns:
        Number of archives expired
    """
    now = datetime.utcnow()
    expired_archives = DataArchive.query.filter(
        DataArchive.status == 'active',
        DataArchive.retention_date.isnot(None),
        DataArchive.retention_date <= now
    ).all()
    
    count = 0
    for archive in expired_archives:
        archive.status = 'expired'
        count += 1
    
    if count > 0:
        db.session.commit()
        logger.info(f"Expired {count} archives based on retention policies")
    
    return count

def get_available_archives(table_name: Optional[str] = None, 
                         archive_type: Optional[str] = None, 
                         limit: int = 100) -> List[DataArchive]:
    """
    Get available archives with optional filters.
    
    Args:
        table_name: Optional table name to filter by
        archive_type: Optional archive type to filter by
        limit: Maximum number of archives to return
        
    Returns:
        List of DataArchive instances
    """
    query = DataArchive.query.filter_by(status='active')
    
    if table_name:
        query = query.filter_by(table_name=table_name)
    
    if archive_type:
        query = query.filter_by(archive_type=archive_type)
    
    return query.order_by(DataArchive.archive_date.desc()).limit(limit).all()

def restore_archive(archive_id: int, 
                   restore_type: str = 'merge',
                   created_by: Optional[int] = None) -> Dict[str, Any]:
    """
    Restore data from an archive.
    
    Args:
        archive_id: ID of the archive to restore
        restore_type: 'merge' to update existing records and add new ones
                      'replace' to delete existing data and replace with archived data
                      'preview' to return what would be restored without making changes
        created_by: Optional ID of user requesting the restore
        
    Returns:
        Dictionary with restore results
    """
    # Get the archive
    archive = DataArchive.query.get(archive_id)
    if not archive:
        raise ValueError(f"Archive with ID {archive_id} not found")
    
    # Check if the archive is active
    if archive.status != 'active':
        raise ValueError(f"Cannot restore from expired archive")
    
    # Get the model class for the table
    model_class = MODEL_MAP.get(archive.table_name.lower())
    if not model_class:
        raise ValueError(f"Unknown table: {archive.table_name}")
    
    # Get archived data
    data = archive.get_data()
    
    # Track restore statistics
    stats = {
        'total_records': len(data),
        'updated': 0,
        'created': 0,
        'skipped': 0,
        'deleted': 0,
        'errors': []
    }
    
    # If this is just a preview, return stats without making changes
    if restore_type == 'preview':
        return {
            'archive': {
                'id': archive.id,
                'table_name': archive.table_name,
                'archive_date': archive.archive_date,
                'record_count': archive.record_count,
                'description': archive.description
            },
            'stats': stats
        }
    
    # If replacing, delete existing data first
    if restore_type == 'replace':
        try:
            delete_count = model_class.query.delete()
            db.session.commit()
            stats['deleted'] = delete_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting existing data: {str(e)}")
            stats['errors'].append(f"Error deleting existing data: {str(e)}")
            return {'archive': archive, 'stats': stats}
    
    # Process each record
    for record_data in data:
        try:
            # Get primary key value
            pk_col = inspect(model_class).primary_key[0].name
            pk_val = record_data.get(pk_col)
            
            # Look for existing record
            existing = None
            if pk_val:
                existing = model_class.query.get(pk_val)
            
            if existing and restore_type == 'merge':
                # Update existing record
                for key, value in record_data.items():
                    if key != pk_col and hasattr(existing, key):
                        setattr(existing, key, value)
                stats['updated'] += 1
            else:
                # Create new record
                # Skip primary key to let the database assign it
                if pk_col in record_data:
                    del record_data[pk_col]
                
                new_record = model_class(**record_data)
                db.session.add(new_record)
                stats['created'] += 1
        except Exception as e:
            logger.error(f"Error restoring record: {str(e)}")
            stats['errors'].append(f"Error restoring record: {str(e)}")
            stats['skipped'] += 1
    
    # Commit changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error committing restored data: {str(e)}")
        stats['errors'].append(f"Error committing restored data: {str(e)}")
    
    # Log the restore
    logger.info(f"Restored archive {archive_id}: updated={stats['updated']}, " + 
               f"created={stats['created']}, skipped={stats['skipped']}")
    
    return {
        'archive': {
            'id': archive.id,
            'table_name': archive.table_name,
            'archive_date': archive.archive_date,
            'record_count': archive.record_count,
            'description': archive.description
        },
        'stats': stats
    }