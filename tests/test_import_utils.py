"""
Tests for the import utilities.

This module tests the data import functionality, including:
1. File type detection
2. Reading data from files
3. Data validation during import
4. Proper database update/insert operations
5. Import logging
"""

import os
import pytest
import pandas as pd
from io import BytesIO
from werkzeug.datastructures import FileStorage

from app import db
from models import Property, TaxCode, TaxDistrict, ImportLog
from utils.import_utils import (
    detect_file_type, read_data_from_file, process_import,
    validate_import_metadata, validate_data_rows, ImportResult
)
from utils.validation_framework import ValidationError


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    content = "property_id,assessed_value,tax_code\nR12345678,450000,12345\nR87654321,550000,12345"
    return FileStorage(
        stream=BytesIO(content.encode('utf-8')),
        filename='test_properties.csv',
        content_type='text/csv'
    )


@pytest.fixture
def sample_excel_file():
    """Create a sample Excel file for testing."""
    data = {
        'code': ['12345', '67890'],
        'levy_rate': [0.154, 0.178],
        'levy_amount': [1495300.0, 1780000.0], 
        'total_assessed_value': [9710000.0, 10000000.0]
    }
    df = pd.DataFrame(data)
    
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    
    return FileStorage(
        stream=buffer,
        filename='test_tax_codes.xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@pytest.fixture
def sample_text_file():
    """Create a sample text file with pipe delimiter for testing."""
    content = "tax_district_id|year|levy_code|linked_levy_code\n101|2024|12345|12345A\n102|2024|67890|67890B"
    return FileStorage(
        stream=BytesIO(content.encode('utf-8')),
        filename='test_districts.txt',
        content_type='text/plain'
    )


class TestFileImport:
    """Tests for file import functionality."""
    
    def test_detect_file_type(self, sample_csv_file, sample_excel_file, sample_text_file):
        """Test file type detection."""
        assert detect_file_type(sample_csv_file) == 'csv'
        assert detect_file_type(sample_excel_file) == 'excel'
        assert detect_file_type(sample_text_file) == 'text'
        
        # Test unsupported file type
        with pytest.raises(ValueError):
            detect_file_type(FileStorage(stream=BytesIO(), filename='test.unsupported'))
    
    def test_read_data_from_file(self, sample_csv_file, sample_excel_file, sample_text_file):
        """Test reading data from different file types."""
        # Test CSV file
        csv_data, file_type = read_data_from_file(sample_csv_file)
        assert file_type == 'csv'
        assert len(csv_data) == 2
        assert csv_data[0]['property_id'] == 'R12345678'
        
        # Test Excel file
        excel_data, file_type = read_data_from_file(sample_excel_file)
        assert file_type == 'excel'
        assert len(excel_data) == 2
        assert excel_data[0]['code'] == '12345'
        
        # Test text file
        text_data, file_type = read_data_from_file(sample_text_file)
        assert file_type == 'text'
        assert len(text_data) == 2
        assert text_data[0]['tax_district_id'] == '101'


class TestDataValidation:
    """Tests for import data validation."""
    
    def test_validate_import_metadata(self, sample_csv_file):
        """Test validation of import metadata."""
        data, _ = read_data_from_file(sample_csv_file)
        
        # Valid import type should pass
        validate_import_metadata(sample_csv_file.filename, data, 'property')
        
        # Invalid import type should fail
        with pytest.raises(ValidationError):
            validate_import_metadata(sample_csv_file.filename, data, 'unknown_type')
    
    def test_validate_data_rows(self, sample_csv_file, sample_excel_file):
        """Test validation of data rows."""
        # Test property data validation
        property_data, _ = read_data_from_file(sample_csv_file)
        # This should not raise an exception
        property_errors = validate_data_rows(property_data, 'property', strict=False)
        assert isinstance(property_errors, (bool, list))
        
        # Test tax code data validation
        tax_code_data, _ = read_data_from_file(sample_excel_file)
        # This should not raise an exception
        tax_code_errors = validate_data_rows(tax_code_data, 'tax_code', strict=False)
        assert isinstance(tax_code_errors, (bool, list))
        
        # Test validation with invalid data type
        with pytest.raises(ValueError):
            validate_data_rows(property_data, 'unknown_type')


class TestImportResult:
    """Tests for ImportResult class."""
    
    def test_import_result(self):
        """Test ImportResult functionality."""
        result = ImportResult()
        assert result.success is True
        assert result.imported_count == 0
        assert result.skipped_count == 0
        
        # Test adding an error
        result.add_error("Test error")
        assert result.success is False
        assert len(result.error_messages) == 1
        
        # Test adding a warning
        result.add_warning("Test warning")
        assert len(result.warning_messages) == 1
        
        # Test as_dict method
        result_dict = result.as_dict()
        assert result_dict['success'] is False
        assert result_dict['imported_count'] == 0
        assert result_dict['errors'] == ["Test error"]
        assert result_dict['warnings'] == ["Test warning"]


@pytest.mark.usefixtures("client")
class TestImportIntegration:
    """Integration tests for import functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear any existing data
        ImportLog.query.delete()
        Property.query.delete()
        TaxCode.query.delete()
        TaxDistrict.query.delete()
        db.session.commit()
    
    def test_property_import(self, sample_csv_file):
        """Test importing property data."""
        # Test with validate_only=True first
        result = process_import(sample_csv_file, 'property', validate_only=True)
        assert result.success is True
        assert result.imported_count == 2
        assert result.skipped_count == 0
        
        # Verify no data was actually imported
        assert Property.query.count() == 0
        
        # Now test actual import
        result = process_import(sample_csv_file, 'property')
        assert result.success is True
        assert result.imported_count == 2
        assert result.skipped_count == 0
        
        # Verify data was imported
        properties = Property.query.all()
        assert len(properties) == 2
        assert properties[0].property_id == 'R12345678'
        assert properties[0].assessed_value == 450000
        assert properties[0].tax_code == '12345'
        
        # Verify import log was created
        logs = ImportLog.query.all()
        assert len(logs) == 1
        assert logs[0].rows_imported == 2
        assert logs[0].import_type == 'property'
    
    def test_tax_code_import(self, sample_excel_file):
        """Test importing tax code data."""
        result = process_import(sample_excel_file, 'tax_code')
        assert result.success is True
        assert result.imported_count == 2
        
        # Verify data was imported
        tax_codes = TaxCode.query.all()
        assert len(tax_codes) == 2
        assert tax_codes[0].code == '12345'
        assert tax_codes[0].levy_rate == 0.154
        assert abs(tax_codes[0].levy_amount - 1495300.0) < 0.1
        
        # Test updating existing tax codes
        updated_content = "code,levy_rate,levy_amount,total_assessed_value\n12345,0.16,1600000,10000000"
        updated_file = FileStorage(
            stream=BytesIO(updated_content.encode('utf-8')),
            filename='updated_tax_codes.csv',
            content_type='text/csv'
        )
        
        result = process_import(updated_file, 'tax_code')
        assert result.success is True
        assert result.imported_count == 1
        
        # Verify data was updated
        updated_code = TaxCode.query.filter_by(code='12345').first()
        assert updated_code.levy_rate == 0.16
        assert updated_code.levy_amount == 1600000
    
    def test_import_with_errors(self):
        """Test import with various error conditions."""
        # Test with empty file
        empty_file = FileStorage(
            stream=BytesIO(b""),
            filename='empty.csv',
            content_type='text/csv'
        )
        result = process_import(empty_file, 'property')
        assert result.success is False
        assert "No data found in file" in result.error_messages
        
        # Test with invalid data
        invalid_content = "property_id,assessed_value,tax_code\nR12345678,invalid,12345"
        invalid_file = FileStorage(
            stream=BytesIO(invalid_content.encode('utf-8')),
            filename='invalid_data.csv',
            content_type='text/csv'
        )
        
        result = process_import(invalid_file, 'property')
        assert result.skipped_count > 0
        
        # Test with invalid import type
        result = process_import(sample_csv_file, 'unknown_type')
        assert result.success is False
        assert any("Unsupported import type" in error for error in result.error_messages)