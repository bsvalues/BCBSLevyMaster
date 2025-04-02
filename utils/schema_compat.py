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
            text("SELECT id, filename, import_type, records_imported, records_skipped, status, import_date, notes FROM import_log ORDER BY import_date DESC LIMIT :limit"),
            {"limit": limit}
        )
        
        return [
            {
                "id": row[0],
                "filename": row[1],
                "import_type": row[2],
                "records_imported": row[3],  # Keep original field name
                "record_count": row[3],      # Map records_imported to record_count for ORM compatibility
                "records_skipped": row[4],   # Keep original field name
                "status": row[5],
                "import_date": row[6],       # Keep original field name
                "created_at": row[6],        # Map import_date to created_at for ORM compatibility
                "notes": row[7] if len(row) > 7 else None,  # Notes field from DB
                "description": row[7] if len(row) > 7 else None  # Map notes to description for backward compatibility
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
            query = text("SELECT id, code, levy_amount, levy_rate, total_assessed_value, year, district_name FROM tax_code WHERE year = :year LIMIT :limit")
            params = {"year": year, "limit": limit}
        else:
            query = text("SELECT id, code, levy_amount, levy_rate, total_assessed_value, year, district_name FROM tax_code LIMIT :limit")
            params = {"limit": limit}
            
        result = db.session.execute(query, params)
        
        return [
            {
                "id": row[0],
                "code": row[1],  # Keep original field name
                "tax_code": row[1],  # Map code to tax_code for ORM compatibility
                "levy_amount": row[2],
                "levy_rate": row[3],
                "total_assessed_value": row[4],
                "year": row[5],
                "district_name": row[6] if len(row) > 6 else None  # Include district_name field
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
                "property_id": row[1],  # Keep original field name
                "parcel_id": row[1],    # Map property_id to parcel_id for ORM compatibility
                "assessed_value": row[2],
                "tax_code": row[3],
                "owner_name": row[4],
                "address": row[5],      # Keep original field name
                "property_address": row[5]  # Map address to property_address for ORM compatibility
            }
            for row in result
        ]
    except Exception as e:
        logger.error(f"Error getting properties: {str(e)}")
        return []

def get_total_assessed_value(tax_code=None):
    """
    Get total assessed value for a specific tax code or across all tax codes.
    
    Args:
        tax_code: Filter by tax code (optional)
        
    Returns:
        Float total assessed value or 0 if error
    """
    try:
        if tax_code:
            # Sum the assessed values of all properties with this tax code
            result = db.session.execute(
                text("SELECT SUM(assessed_value) FROM property WHERE tax_code = :tax_code"),
                {"tax_code": tax_code}
            ).scalar()
        else:
            # Get the total from the tax_code table
            result = db.session.execute(
                text("SELECT SUM(total_assessed_value) FROM tax_code")
            ).scalar()
        return float(result) if result else 0
    except Exception as e:
        logger.error(f"Error getting total assessed value: {str(e)}")
        return 0

def get_total_levy_amount(tax_code=None, year=None):
    """
    Get total levy amount for a specific tax code/year or across all tax codes.
    
    Args:
        tax_code: Filter by tax code (optional)
        year: Filter by year (optional)
        
    Returns:
        Float total levy amount or 0 if error
    """
    try:
        if tax_code and year:
            # Get levy amount for a specific tax code and year
            result = db.session.execute(
                text("SELECT levy_amount FROM tax_code WHERE code = :code AND year = :year"),
                {"code": tax_code, "year": year}
            ).scalar()
        elif tax_code:
            # Get levy amount for a specific tax code (latest year)
            result = db.session.execute(
                text("SELECT levy_amount FROM tax_code WHERE code = :code ORDER BY year DESC LIMIT 1"),
                {"code": tax_code}
            ).scalar()
        else:
            # Get the total from all tax codes
            result = db.session.execute(
                text("SELECT SUM(levy_amount) FROM tax_code")
            ).scalar()
        return float(result) if result else 0
    except Exception as e:
        logger.error(f"Error getting total levy amount: {str(e)}")
        return 0

def create_import_log(filename, import_type, record_count=None, records_imported=None, 
                  records_skipped=0, status="COMPLETED", description=None):
    """
    Create an import log entry using raw SQL compatible with the actual schema.
    
    Args:
        filename: Name of the imported file
        import_type: Type of import (e.g., 'TAX_DISTRICT', 'PROPERTY')
        record_count: Number of records imported (ORM model field)
        records_imported: Number of records imported (actual DB field)
        records_skipped: Number of records skipped during import
        status: Import status
        description: Additional description of the import (will be stored in notes)
        
    Returns:
        ID of the created record or None if error
    """
    try:
        # Handle both naming conventions (ORM vs actual DB)
        if records_imported is None and record_count is not None:
            records_imported = record_count
        elif records_imported is None and record_count is None:
            records_imported = 0
            
        if description:
            result = db.session.execute(
                text("""
                INSERT INTO import_log (filename, import_type, records_imported, records_skipped, status, import_date, notes)
                VALUES (:filename, :import_type, :records_imported, :records_skipped, :status, CURRENT_TIMESTAMP, :notes)
                RETURNING id
                """),
                {
                    "filename": filename,
                    "import_type": import_type,
                    "records_imported": records_imported,
                    "records_skipped": records_skipped,
                    "status": status,
                    "notes": description  # Map description to notes for DB compatibility
                }
            )
        else:
            result = db.session.execute(
                text("""
                INSERT INTO import_log (filename, import_type, records_imported, records_skipped, status, import_date)
                VALUES (:filename, :import_type, :records_imported, :records_skipped, :status, CURRENT_TIMESTAMP)
                RETURNING id
                """),
                {
                    "filename": filename,
                    "import_type": import_type,
                    "records_imported": records_imported,
                    "records_skipped": records_skipped,
                    "status": status
                }
            )
        db.session.commit()
        
        return result.scalar()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating import log: {str(e)}")
        return None