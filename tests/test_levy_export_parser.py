"""
Tests for levy export parser.

This module tests the levy export parser to ensure it correctly parses
different file formats and extracts the required data.
"""

import os
import pytest
from utils.levy_export_parser import LevyExportParser


def test_levy_export_parser_initialization():
    """Test parser initialization with different file types."""
    # Test with TXT file
    txt_parser = LevyExportParser("attached_assets/Levy Expot.txt")
    assert txt_parser.file_path == "attached_assets/Levy Expot.txt"
    assert txt_parser.file_type == "txt"
    
    # Test with XLSX file
    xlsx_parser = LevyExportParser("attached_assets/Levy Expot.xlsx")
    assert xlsx_parser.file_path == "attached_assets/Levy Expot.xlsx"
    assert xlsx_parser.file_type == "xlsx"
    
    # Test with XLS file
    xls_parser = LevyExportParser("attached_assets/Levy Expot.xls")
    assert xls_parser.file_path == "attached_assets/Levy Expot.xls"
    assert xls_parser.file_type == "xls"
    
    # Test with XML file (if available)
    xml_path = "attached_assets/Levy Expot.xml"
    if os.path.exists(xml_path):
        xml_parser = LevyExportParser(xml_path)
        assert xml_parser.file_path == xml_path
        assert xml_parser.file_type == "xml"


def test_levy_export_parser_txt():
    """Test parsing of TXT format levy export files."""
    parser = LevyExportParser("attached_assets/Levy Expot.txt")
    data = parser.parse()
    
    # Verify data structure
    assert isinstance(data, dict)
    assert "districts" in data
    assert "tax_codes" in data
    assert "properties" in data
    
    # Verify districts
    districts = data.get("districts", [])
    assert len(districts) > 0
    for district in districts:
        assert "district_id" in district
        assert "name" in district
        assert "year" in district
    
    # Verify tax codes
    tax_codes = data.get("tax_codes", [])
    assert len(tax_codes) > 0
    for tax_code in tax_codes:
        assert "code" in tax_code
        assert "levy_amount" in tax_code or "total_assessed_value" in tax_code
    
    # Verify properties
    properties = data.get("properties", [])
    assert len(properties) > 0
    for property in properties:
        assert "property_id" in property or "parcel_id" in property


def test_levy_export_parser_xlsx():
    """Test parsing of XLSX format levy export files."""
    parser = LevyExportParser("attached_assets/Levy Expot.xlsx")
    data = parser.parse()
    
    # Verify data structure
    assert isinstance(data, dict)
    assert "districts" in data or "tax_codes" in data or "properties" in data
    
    # Check for expected data types
    if "districts" in data:
        assert isinstance(data["districts"], list)
    
    if "tax_codes" in data:
        assert isinstance(data["tax_codes"], list)
    
    if "properties" in data:
        assert isinstance(data["properties"], list)


def test_levy_export_parser_xls():
    """Test parsing of XLS format levy export files."""
    parser = LevyExportParser("attached_assets/Levy Expot.xls")
    data = parser.parse()
    
    # Verify data structure
    assert isinstance(data, dict)
    assert "districts" in data or "tax_codes" in data or "properties" in data
    
    # Check for expected data types
    if "districts" in data:
        assert isinstance(data["districts"], list)
    
    if "tax_codes" in data:
        assert isinstance(data["tax_codes"], list)
    
    if "properties" in data:
        assert isinstance(data["properties"], list)


def test_levy_export_parser_xml():
    """Test parsing of XML format levy export files."""
    xml_path = "attached_assets/Levy Expot.xml"
    if not os.path.exists(xml_path):
        pytest.skip(f"XML file not found at {xml_path}")
    
    parser = LevyExportParser(xml_path)
    data = parser.parse()
    
    # Verify data structure
    assert isinstance(data, dict)
    assert "districts" in data or "tax_codes" in data or "properties" in data
    
    # Check for expected data types
    if "districts" in data:
        assert isinstance(data["districts"], list)
    
    if "tax_codes" in data:
        assert isinstance(data["tax_codes"], list)
    
    if "properties" in data:
        assert isinstance(data["properties"], list)


def test_levy_export_parser_nonexistent_file():
    """Test parser behavior with nonexistent file."""
    with pytest.raises(FileNotFoundError):
        parser = LevyExportParser("nonexistent_file.txt")
        parser.parse()


def test_levy_export_parser_unsupported_file_type():
    """Test parser behavior with unsupported file type."""
    # Create a temporary file with unsupported extension
    unsupported_file = "temp_test_file.unsupported"
    with open(unsupported_file, "w") as f:
        f.write("test data")
    
    try:
        with pytest.raises(ValueError):
            parser = LevyExportParser(unsupported_file)
            parser.parse()
    finally:
        # Clean up
        if os.path.exists(unsupported_file):
            os.remove(unsupported_file)


def test_levy_export_parser_extract_year():
    """Test year extraction from file content."""
    parser = LevyExportParser("attached_assets/Levy Expot.txt")
    year = parser._extract_year_from_content("Tax Year: 2023\nOther content")
    assert year == 2023
    
    year = parser._extract_year_from_content("No year here")
    assert year is None