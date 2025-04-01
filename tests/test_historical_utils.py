"""
Tests for historical utility functions.
"""
import os
import io
import pytest
from datetime import datetime

from app import app, db
from models import TaxCode, TaxCodeHistoricalRate, ImportLog, ExportLog
from utils.historical_utils import (
    store_current_rates_as_historical,
    get_available_years,
    get_historical_rates,
    get_historical_rates_by_code,
    calculate_multi_year_changes,
    calculate_average_rate_change_by_year,
    export_historical_rates_to_csv,
    import_historical_rates_from_csv,
    seed_historical_rates
)


def test_export_historical_rates_to_csv(db):
    """Test exporting historical rates to CSV."""
    # Create test data
    tax_code = TaxCode(code="1234", levy_rate=0.01, levy_amount=100000, total_assessed_value=10000000)
    db.session.add(tax_code)
    db.session.commit()
    
    # Add historical rates
    historical_rate = TaxCodeHistoricalRate(
        tax_code_id=tax_code.id,
        year=2023,
        levy_rate=0.0095,
        levy_amount=95000,
        total_assessed_value=9500000
    )
    db.session.add(historical_rate)
    db.session.commit()
    
    # Test export all
    success, message, csv_data = export_historical_rates_to_csv()
    assert success
    assert "Successfully exported" in message
    assert csv_data is not None
    
    # Verify CSV content
    csv_content = csv_data.getvalue()
    assert "Tax Code,Year,Levy Rate,Levy Amount,Total Assessed Value" in csv_content
    assert "1234,2023,0.0095,95000.0,9500000.0" in csv_content
    
    # Test export filtered by year
    success, message, csv_data = export_historical_rates_to_csv(year=2023)
    assert success
    assert csv_data is not None
    
    # Test export filtered by tax code
    success, message, csv_data = export_historical_rates_to_csv(tax_code="1234")
    assert success
    assert csv_data is not None
    
    # Test export with both filters
    success, message, csv_data = export_historical_rates_to_csv(year=2023, tax_code="1234")
    assert success
    assert csv_data is not None
    
    # Test export with no matching data
    success, message, csv_data = export_historical_rates_to_csv(year=2022)
    assert not success
    assert "No historical rate data matching" in message
    assert csv_data is None


def test_import_historical_rates_from_csv(db):
    """Test importing historical rates from CSV."""
    # Create a tax code for the import
    tax_code = TaxCode(code="5678", levy_rate=0.015, levy_amount=150000, total_assessed_value=10000000)
    db.session.add(tax_code)
    db.session.commit()
    
    # Create a CSV file in memory
    csv_content = io.BytesIO(b"Tax Code,Year,Levy Rate,Levy Amount,Total Assessed Value\n"
                           b"5678,2022,0.014,140000,9500000\n"
                           b"5678,2021,0.013,130000,9200000\n")
    
    # Test import
    success, message, stats = import_historical_rates_from_csv(csv_content)
    assert success
    assert "Import completed" in message
    assert stats['imported'] == 2
    assert stats['errors'] == 0
    
    # Verify data was imported
    rates = TaxCodeHistoricalRate.query.filter_by(tax_code_id=tax_code.id).all()
    assert len(rates) == 2
    
    # Check import log was created
    log = ImportLog.query.filter_by(import_type='historical_rates').first()
    assert log is not None
    assert log.rows_imported == 2
    
    # Test importing with an invalid tax code
    csv_content = io.BytesIO(b"Tax Code,Year,Levy Rate,Levy Amount,Total Assessed Value\n"
                           b"9999,2022,0.014,140000,9500000\n")
    success, message, stats = import_historical_rates_from_csv(csv_content)
    assert success  # The import process still succeeds
    assert stats['imported'] == 0
    assert stats['skipped'] == 1
    assert len(stats['warnings']) == 1
    assert "not found" in stats['warnings'][0]
    
    # Test importing with invalid data format
    csv_content = io.BytesIO(b"Tax Code,Year,Levy Rate,Levy Amount,Total Assessed Value\n"
                           b"5678,invalid,0.014,140000,9500000\n")
    success, message, stats = import_historical_rates_from_csv(csv_content)
    assert success  # The import process still succeeds
    assert stats['imported'] == 0
    assert stats['skipped'] == 1
    assert len(stats['warnings']) == 1
    assert "Invalid year format" in stats['warnings'][0]
    
    # Test updating existing record
    csv_content = io.BytesIO(b"Tax Code,Year,Levy Rate,Levy Amount,Total Assessed Value\n"
                           b"5678,2022,0.0145,145000,9600000\n")
    success, message, stats = import_historical_rates_from_csv(csv_content)
    assert success
    assert stats['updated'] == 1
    
    # Verify the record was updated
    updated_rate = TaxCodeHistoricalRate.query.filter_by(tax_code_id=tax_code.id, year=2022).first()
    assert updated_rate.levy_rate == 0.0145
    assert updated_rate.levy_amount == 145000
    assert updated_rate.total_assessed_value == 9600000


def test_calculate_multi_year_changes(db):
    """Test calculating multi-year changes for a tax code."""
    # Create test data
    tax_code = TaxCode(code="ABC", levy_rate=0.020, levy_amount=200000, total_assessed_value=10000000)
    db.session.add(tax_code)
    db.session.commit()
    
    # Add historical rates for multiple years
    years = [2024, 2023, 2022, 2021, 2020]
    rates = [0.020, 0.019, 0.018, 0.017, 0.016]
    
    for year, rate in zip(years, rates):
        historical_rate = TaxCodeHistoricalRate(
            tax_code_id=tax_code.id,
            year=year,
            levy_rate=rate,
            levy_amount=rate * 10000000,
            total_assessed_value=10000000
        )
        db.session.add(historical_rate)
    db.session.commit()
    
    # Test calculating changes with default base year (latest)
    result = calculate_multi_year_changes("ABC")
    assert result['tax_code'] == "ABC"
    assert result['base_year'] == 2024
    assert result['base_rate'] == 0.020
    assert len(result['yearly_rates']) == 5
    assert len(result['yearly_changes']) == 5
    assert len(result['yearly_percent_changes']) == 5
    
    # Verify cumulative change calculation (from oldest to newest)
    assert result['cumulative_change'] == 0.004  # 0.020 - 0.016
    assert result['cumulative_percent_change'] == 25.0  # (0.004 / 0.016) * 100
    
    # Test with a specific base year
    result = calculate_multi_year_changes("ABC", base_year=2022)
    assert result['base_year'] == 2022
    assert result['base_rate'] == 0.018


def test_seed_historical_rates(db):
    """Test seeding historical rate data."""
    # Create test tax codes
    tax_code1 = TaxCode(code="TEST1", levy_rate=0.025, levy_amount=250000, total_assessed_value=10000000)
    tax_code2 = TaxCode(code="TEST2", levy_rate=0.030, levy_amount=300000, total_assessed_value=10000000)
    db.session.add_all([tax_code1, tax_code2])
    db.session.commit()
    
    # Test seeding data
    success, message = seed_historical_rates(base_year=2024, num_years=3)
    assert success
    assert "Successfully seeded" in message
    
    # Verify the data was created
    rates = TaxCodeHistoricalRate.query.all()
    assert len(rates) >= 6  # 2 tax codes * 3 years
    
    # Check years
    years = set(rate.year for rate in rates)
    assert 2024 in years
    assert 2023 in years
    assert 2022 in years
    
    # Test seeding with no tax codes
    db.session.query(TaxCode).delete()
    db.session.commit()
    
    success, message = seed_historical_rates()
    assert not success
    assert "No tax codes found" in message