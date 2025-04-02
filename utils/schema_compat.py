"""
Database schema compatibility utilities.

This module provides utilities to work with the actual database schema
when it differs from the ORM models.
"""

from sqlalchemy import text
from app import db
import logging

# Configure logger
logger = logging.getLogger(__name__)

def get_import_log_entries(limit=5):
    """
    Get recent import log entries using raw SQL compatible with the actual schema.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of dictionaries containing import log data
    """
    try:
        result = db.session.execute(
            text("SELECT id, filename, import_type, records_imported, status, import_date FROM import_log ORDER BY import_date DESC LIMIT :limit"),
            {"limit": limit}
        )
        
        return [
            {
                "id": row[0],
                "filename": row[1],
                "import_type": row[2],
                "record_count": row[3],  # Map records_imported to record_count for ORM compatibility
                "status": row[4],
                "created_at": row[5]  # Map import_date to created_at for ORM compatibility
            }
            for row in result
        ]
    except Exception as e:
        logger.error(f"Error getting import log entries: {str(e)}")
        return []

def get_tax_codes(year=None, limit=100):
    """
    Get tax codes using raw SQL compatible with the actual schema.
    
    Args:
        year: Filter by year (optional)
        limit: Maximum number of entries to return
        
    Returns:
        List of dictionaries containing tax code data
    """
    try:
        if year:
            query = text("SELECT id, code, levy_amount, levy_rate, total_assessed_value, year FROM tax_code WHERE year = :year LIMIT :limit")
            params = {"year": year, "limit": limit}
        else:
            query = text("SELECT id, code, levy_amount, levy_rate, total_assessed_value, year FROM tax_code LIMIT :limit")
            params = {"limit": limit}
            
        result = db.session.execute(query, params)
        
        return [
            {
                "id": row[0],
                "tax_code": row[1],  # Map code to tax_code for ORM compatibility
                "levy_amount": row[2],
                "levy_rate": row[3],
                "total_assessed_value": row[4],
                "year": row[5]
            }
            for row in result
        ]
    except Exception as e:
        logger.error(f"Error getting tax codes: {str(e)}")
        return []

def get_properties(tax_code=None, limit=100):
    """
    Get properties using raw SQL compatible with the actual schema.
    
    Args:
        tax_code: Filter by tax code (optional)
        limit: Maximum number of entries to return
        
    Returns:
        List of dictionaries containing property data
    """
    try:
        if tax_code:
            query = text("SELECT id, property_id, assessed_value, tax_code, owner_name, address FROM property WHERE tax_code = :tax_code LIMIT :limit")
            params = {"tax_code": tax_code, "limit": limit}
        else:
            query = text("SELECT id, property_id, assessed_value, tax_code, owner_name, address FROM property LIMIT :limit")
            params = {"limit": limit}
            
        result = db.session.execute(query, params)
        
        return [
            {
                "id": row[0],
                "parcel_id": row[1],  # Map property_id to parcel_id for ORM compatibility
                "assessed_value": row[2],
                "tax_code": row[3],
                "owner_name": row[4],
                "property_address": row[5]  # Map address to property_address for ORM compatibility
            }
            for row in result
        ]
    except Exception as e:
        logger.error(f"Error getting properties: {str(e)}")
        return []

def get_total_assessed_value():
    """
    Get total assessed value across all tax codes.
    
    Returns:
        Float total assessed value or 0 if error
    """
    try:
        result = db.session.execute(
            text("SELECT SUM(total_assessed_value) FROM tax_code")
        ).scalar()
        return float(result) if result else 0
    except Exception as e:
        logger.error(f"Error getting total assessed value: {str(e)}")
        return 0

def get_total_levy_amount():
    """
    Get total levy amount across all tax codes.
    
    Returns:
        Float total levy amount or 0 if error
    """
    try:
        result = db.session.execute(
            text("SELECT SUM(levy_amount) FROM tax_code")
        ).scalar()
        return float(result) if result else 0
    except Exception as e:
        logger.error(f"Error getting total levy amount: {str(e)}")
        return 0

def create_import_log(filename, import_type, records_imported, status="COMPLETED"):
    """
    Create an import log entry using raw SQL compatible with the actual schema.
    
    Args:
        filename: Name of the imported file
        import_type: Type of import (e.g., 'TAX_DISTRICT', 'PROPERTY')
        records_imported: Number of records imported
        status: Import status
        
    Returns:
        ID of the created record or None if error
    """
    try:
        result = db.session.execute(
            text("""
            INSERT INTO import_log (filename, import_type, records_imported, status, import_date)
            VALUES (:filename, :import_type, :records_imported, :status, CURRENT_TIMESTAMP)
            RETURNING id
            """),
            {
                "filename": filename,
                "import_type": import_type,
                "records_imported": records_imported,
                "status": status
            }
        )
        db.session.commit()
        
        return result.scalar()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating import log: {str(e)}")
        return None