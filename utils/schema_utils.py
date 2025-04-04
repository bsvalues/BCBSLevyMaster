"""
Schema compatibility utilities for database interactions.

This module provides functions for interacting with database tables
that might have schema discrepancies between the ORM models and
the actual database structure.
"""

import logging
from sqlalchemy import text
from app import db

logger = logging.getLogger(__name__)

def get_recent_import_logs(limit=5):
    """
    Get recent import logs using raw SQL that's compatible with the actual schema.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of dictionaries representing import logs
    """
    try:
        query = """
        SELECT id, filename, status, import_type, 
               record_count, success_count, error_count, 
               import_date, notes 
        FROM import_log 
        ORDER BY id DESC 
        LIMIT :limit
        """
        result = db.session.execute(text(query), {"limit": limit})
        
        import_logs = []
        for row in result:
            # Convert row to dictionary
            log = {}
            for i, column in enumerate(result.keys()):
                log[column] = row[i]
            import_logs.append(log)
            
        return import_logs
    except Exception as e:
        logger.error(f"Error getting recent import logs: {str(e)}")
        return []

def get_recent_export_logs(limit=5):
    """
    Get recent export logs using raw SQL that's compatible with the actual schema.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of dictionaries representing export logs
    """
    try:
        query = """
        SELECT id, filename, status, export_type, 
               rows_exported, export_date, notes 
        FROM export_log 
        ORDER BY export_date DESC 
        LIMIT :limit
        """
        result = db.session.execute(text(query), {"limit": limit})
        
        export_logs = []
        for row in result:
            # Convert row to dictionary
            log = {}
            for i, column in enumerate(result.keys()):
                log[column] = row[i]
            export_logs.append(log)
            
        return export_logs
    except Exception as e:
        logger.error(f"Error getting recent export logs: {str(e)}")
        return []

def get_tax_code_summary(limit=10):
    """
    Get tax code summary information for visualization.
    
    Args:
        limit: Maximum number of tax codes to return
        
    Returns:
        List of dictionaries with tax code summary data
    """
    try:
        # Get all tax codes with assessed values
        query = """
        SELECT tax_code, total_assessed_value 
        FROM tax_code 
        WHERE total_assessed_value > 0
        ORDER BY total_assessed_value DESC
        LIMIT :limit
        """
        result = db.session.execute(text(query), {"limit": limit})
        
        tax_codes = []
        for row in result:
            tax_codes.append({
                "code": row[0],
                "assessed_value": row[1]
            })
        
        # Calculate total assessed value and percentages
        total_assessed_value = sum(tc["assessed_value"] for tc in tax_codes)
        
        tax_summary = []
        if total_assessed_value > 0:
            for tc in tax_codes:
                percent = (tc["assessed_value"] / total_assessed_value) * 100
                tax_summary.append({
                    "code": tc["code"],
                    "assessed_value": tc["assessed_value"],
                    "percent_of_total": percent
                })
                
        return tax_summary
    except Exception as e:
        logger.error(f"Error getting tax code summary: {str(e)}")
        return []

def get_table_counts():
    """
    Get counts of key tables in the database.
    
    Returns:
        Dictionary with table counts
    """
    try:
        tables = {
            "property": "property",
            "tax_code": "tax_code",
            "tax_district": "tax_district"
        }
        
        counts = {}
        for key, table in tables.items():
            query = f"SELECT COUNT(*) FROM {table}"
            result = db.session.execute(text(query))
            counts[key] = result.scalar() or 0
            
        return counts
    except Exception as e:
        logger.error(f"Error getting table counts: {str(e)}")
        return {
            "property": 0,
            "tax_code": 0,
            "tax_district": 0
        }

def get_property_assessed_value_avg():
    """
    Get average assessed value of properties.
    
    Returns:
        Average assessed value or None if error
    """
    try:
        query = "SELECT AVG(assessed_value) FROM property"
        result = db.session.execute(text(query))
        return result.scalar()
    except Exception as e:
        logger.error(f"Error getting average assessed value: {str(e)}")
        return None