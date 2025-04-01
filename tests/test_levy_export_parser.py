"""
Unit tests for the levy export parser.
"""

import os
import tempfile
import unittest

from utils.levy_export_parser import (
    LevyExportParser, LevyExportFormat, LevyExportData,
    TextLevyExportParser, CsvLevyExportParser, 
    ExcelLevyExportParser, XmlLevyExportParser
)


class TestLevyExportData(unittest.TestCase):
    """Test cases for the LevyExportData class."""

    def test_add_record(self):
        """Test adding records to LevyExportData."""
        data = LevyExportData()
        
        # Add a record
        record = {
            'tax_district_id': 123,
            'year': 2022,
            'levy_cd': 'ABC',
            'levy_cd_linked': 'XYZ'
        }
        data.add_record(record)
        
        # Verify record was added
        self.assertEqual(len(data), 1)
        self.assertEqual(data.records[0], record)
        
        # Verify metadata was updated
        self.assertEqual(data.metadata['total_records'], 1)
        self.assertIn(123, data.metadata['tax_districts'])
        self.assertIn(2022, data.metadata['years'])
        self.assertIn('ABC', data.metadata['levy_codes'])
        
        # Add another record
        record2 = {
            'tax_district_id': 456,
            'year': 2023,
            'levy_cd': 'DEF',
            'levy_cd_linked': 'UVW'
        }
        data.add_record(record2)
        
        # Verify record was added
        self.assertEqual(len(data), 2)
        
        # Verify getters work
        self.assertEqual(data.get_years(), [2022, 2023])
        self.assertEqual(data.get_tax_districts(), [123, 456])
        self.assertEqual(data.get_levy_codes(), ['ABC', 'DEF'])


class TestLevyExportParser(unittest.TestCase):
    """Test cases for the LevyExportParser class."""

    def test_detect_format(self):
        """Test format detection based on file extension."""
        # Create temporary files with different extensions
        with tempfile.NamedTemporaryFile(suffix='.txt') as txt_file, \
             tempfile.NamedTemporaryFile(suffix='.csv') as csv_file, \
             tempfile.NamedTemporaryFile(suffix='.xls') as xls_file, \
             tempfile.NamedTemporaryFile(suffix='.xlsx') as xlsx_file, \
             tempfile.NamedTemporaryFile(suffix='.xml') as xml_file, \
             tempfile.NamedTemporaryFile(suffix='.unknown') as unknown_file:
            
            # Test format detection
            self.assertEqual(LevyExportParser.detect_format(txt_file.name), LevyExportFormat.TXT)
            self.assertEqual(LevyExportParser.detect_format(csv_file.name), LevyExportFormat.CSV)
            self.assertEqual(LevyExportParser.detect_format(xls_file.name), LevyExportFormat.XLS)
            self.assertEqual(LevyExportParser.detect_format(xlsx_file.name), LevyExportFormat.XLSX)
            self.assertEqual(LevyExportParser.detect_format(xml_file.name), LevyExportFormat.XML)
            self.assertEqual(LevyExportParser.detect_format(unknown_file.name), LevyExportFormat.UNKNOWN)
    
    def test_create_parser(self):
        """Test parser creation based on file format."""
        # Test parser creation for each format
        self.assertIsInstance(LevyExportParser.create_parser(LevyExportFormat.TXT), TextLevyExportParser)
        self.assertIsInstance(LevyExportParser.create_parser(LevyExportFormat.CSV), CsvLevyExportParser)
        self.assertIsInstance(LevyExportParser.create_parser(LevyExportFormat.XLS), ExcelLevyExportParser)
        self.assertIsInstance(LevyExportParser.create_parser(LevyExportFormat.XLSX), ExcelLevyExportParser)
        self.assertIsInstance(LevyExportParser.create_parser(LevyExportFormat.XML), XmlLevyExportParser)
        
        # Test invalid format
        with self.assertRaises(ValueError):
            LevyExportParser.create_parser(LevyExportFormat.UNKNOWN)


if __name__ == '__main__':
    unittest.main()