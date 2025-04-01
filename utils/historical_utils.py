"""
Utility functions for managing historical levy rate data for multi-year comparisons.

This module provides functionality to:
1. Store historical rates from past years
2. Retrieve historical data for trend analysis
3. Compare rates across multiple years
4. Calculate year-over-year changes
5. Visualize historical trends
6. Import/export historical rate data from/to CSV files
"""

import csv
import io
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional, BinaryIO, TextIO

from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import TaxCode, TaxCodeHistoricalRate
from models import ExportLog, ImportLog

# Set up logging
logger = logging.getLogger(__name__)

def store_current_rates_as_historical(year: int) -> Tuple[bool, str]:
    """
    Store current tax code rates as historical rates for the specified year.
    
    Args:
        year: The year to associate with the current rates
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Get all tax codes with rates
        tax_codes = TaxCode.query.filter(TaxCode.levy_rate.isnot(None)).all()
        
        # Track counters for result message
        added_count = 0
        updated_count = 0
        
        for tax_code in tax_codes:
            # Check if historical rate already exists for this tax code and year
            existing = TaxCodeHistoricalRate.query.filter_by(
                tax_code_id=tax_code.id, 
                year=year
            ).first()
            
            if existing:
                # Update existing record
                existing.levy_rate = tax_code.levy_rate
                existing.levy_amount = tax_code.levy_amount
                existing.total_assessed_value = tax_code.total_assessed_value
                existing.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new historical record
                historical_rate = TaxCodeHistoricalRate(
                    tax_code_id=tax_code.id,
                    year=year,
                    levy_rate=tax_code.levy_rate,
                    levy_amount=tax_code.levy_amount,
                    total_assessed_value=tax_code.total_assessed_value
                )
                db.session.add(historical_rate)
                added_count += 1
        
        # Commit changes
        db.session.commit()
        
        message = f"Successfully stored historical rates for {year}: {added_count} added, {updated_count} updated"
        logger.info(message)
        return True, message
        
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = f"Failed to store historical rates: {str(e)}"
        logger.error(error_message)
        return False, error_message

def get_available_years() -> List[int]:
    """
    Get a list of years available in the historical data.
    
    Returns:
        List of years in descending order (newest first)
    """
    # Query distinct years from historical rates
    years = db.session.query(TaxCodeHistoricalRate.year)\
        .distinct()\
        .order_by(desc(TaxCodeHistoricalRate.year))\
        .all()
    
    # Extract years from result tuples
    return [year[0] for year in years]

def get_historical_rates(tax_code_id: int, years: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Get historical rates for a specific tax code across multiple years.
    
    Args:
        tax_code_id: ID of the tax code to get historical data for
        years: Optional list of specific years to retrieve (if None, get all years)
        
    Returns:
        List of historical rate data dictionaries
    """
    query = TaxCodeHistoricalRate.query.filter_by(tax_code_id=tax_code_id)
    
    if years:
        query = query.filter(TaxCodeHistoricalRate.year.in_(years))
    
    historical_rates = query.order_by(desc(TaxCodeHistoricalRate.year)).all()
    
    return [
        {
            'year': rate.year,
            'levy_rate': rate.levy_rate,
            'levy_amount': rate.levy_amount,
            'total_assessed_value': rate.total_assessed_value,
        }
        for rate in historical_rates
    ]

def get_historical_rates_by_code(tax_code: str, years: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Get historical rates for a tax code (by code string) across multiple years.
    
    Args:
        tax_code: String code of the tax code to get historical data for
        years: Optional list of specific years to retrieve (if None, get all years)
        
    Returns:
        List of historical rate data dictionaries
    """
    # Find the tax code first
    tax_code_obj = TaxCode.query.filter_by(code=tax_code).first()
    
    if not tax_code_obj:
        logger.warning(f"Tax code {tax_code} not found")
        return []
    
    return get_historical_rates(tax_code_obj.id, years)

def calculate_multi_year_changes(tax_code: str, years: Optional[List[int]] = None, base_year: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate multi-year changes in levy rates for a specific tax code.
    
    Args:
        tax_code: The tax code to analyze
        years: Optional list of specific years to analyze (if None, use all available years)
        base_year: Optional base year for comparisons (if None, use most recent year)
        
    Returns:
        Dictionary with multi-year change analysis
    """
    # Get historical rates for this tax code with optional year filter
    historical_data = get_historical_rates_by_code(tax_code, years)
    
    if not historical_data:
        return {
            'tax_code': tax_code,
            'base_year': None,
            'years_available': [],
            'base_rate': None,
            'yearly_rates': [],
            'yearly_changes': [],
            'yearly_percent_changes': [],
            'cumulative_change': None,
            'cumulative_percent_change': None,
        }
    
    # Get available years
    years_available = [data['year'] for data in historical_data]
    
    # If base_year not provided or not in available years, use most recent
    if not base_year or base_year not in years_available:
        base_year = years_available[0]  # Most recent year (list is in desc order)
    
    # Find base rate
    base_data = next((data for data in historical_data if data['year'] == base_year), None)
    
    if not base_data:
        return {
            'tax_code': tax_code,
            'base_year': base_year,
            'years_available': years_available,
            'base_rate': None,
            'yearly_rates': [],
            'yearly_changes': [],
            'yearly_percent_changes': [],
            'cumulative_change': None,
            'cumulative_percent_change': None,
        }
    
    base_rate = base_data['levy_rate']
    
    # Calculate yearly changes
    yearly_rates = []
    yearly_changes = []
    yearly_percent_changes = []
    
    # Sort historical data by year (ascending)
    sorted_data = sorted(historical_data, key=lambda x: x['year'])
    
    for data in sorted_data:
        year = data['year']
        rate = data['levy_rate']
        
        yearly_rates.append({
            'year': year,
            'rate': rate
        })
        
        # Calculate change from base year
        change = rate - base_rate
        yearly_changes.append({
            'year': year,
            'change': change
        })
        
        # Calculate percent change from base year
        if base_rate:  # Avoid division by zero
            percent_change = (change / base_rate) * 100
        else:
            percent_change = 0
            
        yearly_percent_changes.append({
            'year': year,
            'percent_change': percent_change
        })
    
    # Calculate cumulative change (from oldest to newest)
    if len(sorted_data) >= 2:
        oldest_rate = sorted_data[0]['levy_rate']
        newest_rate = sorted_data[-1]['levy_rate']
        
        cumulative_change = newest_rate - oldest_rate
        
        if oldest_rate:  # Avoid division by zero
            cumulative_percent_change = (cumulative_change / oldest_rate) * 100
        else:
            cumulative_percent_change = 0
    else:
        cumulative_change = 0
        cumulative_percent_change = 0
    
    return {
        'tax_code': tax_code,
        'base_year': base_year,
        'years_available': years_available,
        'base_rate': base_rate,
        'yearly_rates': yearly_rates,
        'yearly_changes': yearly_changes,
        'yearly_percent_changes': yearly_percent_changes,
        'cumulative_change': cumulative_change,
        'cumulative_percent_change': cumulative_percent_change,
    }

def calculate_average_rate_change_by_year(start_year: int, end_year: int) -> Dict[str, Any]:
    """
    Calculate average rate changes across all tax codes by year.
    
    Args:
        start_year: Starting year for analysis
        end_year: Ending year for analysis
        
    Returns:
        Dictionary with average change analysis by year
    """
    # Query all tax codes that have historical data for both years
    start_year_rates = TaxCodeHistoricalRate.query.filter_by(year=start_year).all()
    
    if not start_year_rates:
        return {
            'start_year': start_year,
            'end_year': end_year,
            'tax_codes_analyzed': 0,
            'average_change': 0,
            'average_percent_change': 0,
            'median_change': 0,
            'median_percent_change': 0,
            'max_increase': {'tax_code': None, 'change': 0, 'percent': 0},
            'max_decrease': {'tax_code': None, 'change': 0, 'percent': 0},
        }
    
    results = []
    for start_rate in start_year_rates:
        # Find matching end year rate for this tax code
        end_rate = TaxCodeHistoricalRate.query.filter_by(
            tax_code_id=start_rate.tax_code_id,
            year=end_year
        ).first()
        
        if end_rate:
            # Get tax code for reference
            tax_code = TaxCode.query.get(start_rate.tax_code_id)
            
            # Calculate changes
            change = end_rate.levy_rate - start_rate.levy_rate
            
            if start_rate.levy_rate:  # Avoid division by zero
                percent_change = (change / start_rate.levy_rate) * 100
            else:
                percent_change = 0
                
            results.append({
                'tax_code': tax_code.code if tax_code else str(start_rate.tax_code_id),
                'start_rate': start_rate.levy_rate,
                'end_rate': end_rate.levy_rate,
                'change': change,
                'percent_change': percent_change
            })
    
    # Calculate statistics
    if results:
        # Average changes
        changes = [r['change'] for r in results]
        percent_changes = [r['percent_change'] for r in results]
        
        average_change = sum(changes) / len(changes)
        average_percent_change = sum(percent_changes) / len(percent_changes)
        
        # Median changes
        sorted_changes = sorted(changes)
        sorted_percent_changes = sorted(percent_changes)
        
        middle_idx = len(sorted_changes) // 2
        
        if len(sorted_changes) % 2 == 0:
            median_change = (sorted_changes[middle_idx - 1] + sorted_changes[middle_idx]) / 2
            median_percent_change = (sorted_percent_changes[middle_idx - 1] + 
                                    sorted_percent_changes[middle_idx]) / 2
        else:
            median_change = sorted_changes[middle_idx]
            median_percent_change = sorted_percent_changes[middle_idx]
        
        # Find max increase and decrease
        max_increase = max(results, key=lambda x: x['change'])
        max_decrease = min(results, key=lambda x: x['change'])
        
        return {
            'start_year': start_year,
            'end_year': end_year,
            'tax_codes_analyzed': len(results),
            'average_change': average_change,
            'average_percent_change': average_percent_change,
            'median_change': median_change,
            'median_percent_change': median_percent_change,
            'max_increase': {
                'tax_code': max_increase['tax_code'],
                'change': max_increase['change'],
                'percent': max_increase['percent_change']
            },
            'max_decrease': {
                'tax_code': max_decrease['tax_code'],
                'change': max_decrease['change'],
                'percent': max_decrease['percent_change']
            },
        }
    else:
        return {
            'start_year': start_year,
            'end_year': end_year,
            'tax_codes_analyzed': 0,
            'average_change': 0,
            'average_percent_change': 0,
            'median_change': 0,
            'median_percent_change': 0,
            'max_increase': {'tax_code': None, 'change': 0, 'percent': 0},
            'max_decrease': {'tax_code': None, 'change': 0, 'percent': 0},
        }

def export_historical_rates_to_csv(year: Optional[int] = None, 
                           tax_code: Optional[str] = None) -> Tuple[bool, str, Optional[io.StringIO]]:
    """
    Export historical rate data to CSV format.

    Args:
        year: Optional year to filter data for (if None, exports all years)
        tax_code: Optional tax code to filter data for (if None, exports all tax codes)
        
    Returns:
        Tuple of (success, message, csv_data)
    """
    try:
        # Build the query based on filters
        query = TaxCodeHistoricalRate.query.join(TaxCode)
        
        if year:
            query = query.filter(TaxCodeHistoricalRate.year == year)
        
        if tax_code:
            query = query.filter(TaxCode.code == tax_code)
        
        # Order the results
        historical_rates = query.order_by(TaxCode.code, TaxCodeHistoricalRate.year).all()
        
        if not historical_rates:
            return False, "No historical rate data matching the specified filters.", None
        
        # Create CSV data in memory
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)
        
        # Write header
        csv_writer.writerow([
            'Tax Code', 'Year', 'Levy Rate', 'Levy Amount', 'Total Assessed Value'
        ])
        
        # Write data rows
        for rate in historical_rates:
            tax_code_obj = TaxCode.query.get(rate.tax_code_id)
            csv_writer.writerow([
                tax_code_obj.code if tax_code_obj else f"Unknown ({rate.tax_code_id})",
                rate.year,
                rate.levy_rate,
                rate.levy_amount if rate.levy_amount is not None else '',
                rate.total_assessed_value if rate.total_assessed_value is not None else ''
            ])
        
        # Create export log
        export_log = ExportLog(
            filename=f"historical_rates_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            rows_exported=len(historical_rates)
        )
        db.session.add(export_log)
        db.session.commit()
        
        # Reset the StringIO object's position to beginning
        csv_data.seek(0)
        
        return True, f"Successfully exported {len(historical_rates)} historical rate records.", csv_data
        
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = f"Failed to export historical rates: {str(e)}"
        logger.error(error_message)
        return False, error_message, None


def import_historical_rates_from_csv(csv_file: BinaryIO) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Import historical rate data from a CSV file.

    Expected CSV format:
    Tax Code, Year, Levy Rate, Levy Amount, Total Assessed Value

    Args:
        csv_file: A file-like object containing CSV data
        
    Returns:
        Tuple of (success, message, statistics dictionary)
    """
    try:
        # Statistics for tracking results
        stats = {
            'processed': 0,
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'warnings': []
        }
        
        # Parse CSV data
        csv_data = csv_file.read().decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_data))
        
        # Get header row
        headers = next(csv_reader, None)
        expected_headers = ['Tax Code', 'Year', 'Levy Rate', 'Levy Amount', 'Total Assessed Value']
        
        # Validate headers
        if not headers or not all(h in headers for h in expected_headers):
            message = f"Invalid CSV format. Expected headers: {', '.join(expected_headers)}"
            stats['warnings'].append(message)
            return False, message, stats
        
        # Process each row
        for row_idx, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header
            if len(row) < 3:  # Minimum: tax code, year, levy rate
                stats['warnings'].append(f"Row {row_idx}: Invalid row format, skipping.")
                stats['skipped'] += 1
                continue
                
            stats['processed'] += 1
            
            try:
                # Extract data
                tax_code_str = row[0].strip()
                year_str = row[1].strip()
                levy_rate_str = row[2].strip()
                
                # Validate required fields
                if not tax_code_str or not year_str or not levy_rate_str:
                    stats['warnings'].append(f"Row {row_idx}: Missing required field(s), skipping.")
                    stats['skipped'] += 1
                    continue
                
                # Convert values
                try:
                    year = int(year_str)
                except ValueError:
                    stats['warnings'].append(f"Row {row_idx}: Invalid year format, skipping.")
                    stats['skipped'] += 1
                    continue
                    
                try:
                    levy_rate = float(levy_rate_str)
                except ValueError:
                    stats['warnings'].append(f"Row {row_idx}: Invalid levy rate format, skipping.")
                    stats['skipped'] += 1
                    continue
                
                # Optional fields
                levy_amount = None
                if len(row) > 3 and row[3].strip():
                    try:
                        levy_amount = float(row[3].strip())
                    except ValueError:
                        stats['warnings'].append(f"Row {row_idx}: Invalid levy amount format, using null.")
                
                total_assessed_value = None
                if len(row) > 4 and row[4].strip():
                    try:
                        total_assessed_value = float(row[4].strip())
                    except ValueError:
                        stats['warnings'].append(f"Row {row_idx}: Invalid assessed value format, using null.")
                
                # Look up the tax code
                tax_code = TaxCode.query.filter_by(code=tax_code_str).first()
                if not tax_code:
                    stats['warnings'].append(f"Row {row_idx}: Tax code '{tax_code_str}' not found, skipping.")
                    stats['skipped'] += 1
                    continue
                
                # Check if historical record already exists
                existing = TaxCodeHistoricalRate.query.filter_by(
                    tax_code_id=tax_code.id,
                    year=year
                ).first()
                
                if existing:
                    # Update existing record
                    existing.levy_rate = levy_rate
                    existing.levy_amount = levy_amount
                    existing.total_assessed_value = total_assessed_value
                    existing.updated_at = datetime.utcnow()
                    stats['updated'] += 1
                else:
                    # Create new historical record
                    historical_rate = TaxCodeHistoricalRate(
                        tax_code_id=tax_code.id,
                        year=year,
                        levy_rate=levy_rate,
                        levy_amount=levy_amount,
                        total_assessed_value=total_assessed_value
                    )
                    db.session.add(historical_rate)
                    stats['imported'] += 1
                    
            except Exception as e:
                stats['errors'] += 1
                stats['warnings'].append(f"Row {row_idx}: Error processing: {str(e)}")
                logger.error(f"Error processing row {row_idx}: {str(e)}")
                continue
        
        # Commit changes
        db.session.commit()
        
        # Create import log
        warnings_text = "\n".join(stats['warnings']) if stats['warnings'] else None
        import_log = ImportLog(
            filename=f"historical_rates_import_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            rows_imported=stats['imported'] + stats['updated'],
            rows_skipped=stats['skipped'] + stats['errors'],
            warnings=warnings_text,
            import_type='historical_rates'
        )
        db.session.add(import_log)
        db.session.commit()
        
        # Build result message
        message = (f"Import completed: {stats['imported']} records imported, {stats['updated']} updated, "
                   f"{stats['skipped']} skipped, {stats['errors']} errors.")
        
        logger.info(message)
        return True, message, stats
        
    except Exception as e:
        db.session.rollback()
        error_message = f"Failed to import historical rates: {str(e)}"
        logger.error(error_message)
        return False, error_message, {'errors': 1, 'warnings': [error_message]}


def seed_historical_rates(base_year: int = 2024, num_years: int = 5) -> Tuple[bool, str]:
    """
    Seed historical rates for testing and development.
    
    Args:
        base_year: The most recent year to use as a base
        num_years: Number of past years to generate
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Get all tax codes
        tax_codes = TaxCode.query.all()
        
        if not tax_codes:
            return False, "No tax codes found to seed historical data"
        
        total_records = 0
        
        # Generate historical data for each year
        for year in range(base_year, base_year - num_years, -1):
            for tax_code in tax_codes:
                # Skip tax codes without rates
                if tax_code.levy_rate is None:
                    continue
                
                # Check if historical record already exists
                existing = TaxCodeHistoricalRate.query.filter_by(
                    tax_code_id=tax_code.id,
                    year=year
                ).first()
                
                if existing:
                    continue
                
                # Create historical record with slight variations per year
                # More recent years have slightly higher rates (trend up ~2-3% per year)
                # Random variation factor based on year distance from base
                year_factor = (base_year - year) * 0.025  # 2.5% decrease per year back
                
                historical_rate = TaxCodeHistoricalRate(
                    tax_code_id=tax_code.id,
                    year=year,
                    levy_rate=tax_code.levy_rate / (1 + year_factor),  # Lower rate in past
                    levy_amount=tax_code.levy_amount / (1 + year_factor) if tax_code.levy_amount else None,
                    total_assessed_value=tax_code.total_assessed_value / (1 + year_factor/2) 
                        if tax_code.total_assessed_value else None  # Assessed values grow slower
                )
                
                db.session.add(historical_rate)
                total_records += 1
        
        db.session.commit()
        message = f"Successfully seeded {total_records} historical records across {num_years} years"
        logger.info(message)
        return True, message
        
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = f"Failed to seed historical rates: {str(e)}"
        logger.error(error_message)
        return False, error_message