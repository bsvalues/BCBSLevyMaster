"""
Levy Export Parser for the Levy Calculation System.

This module provides parsers for various levy export file formats
including CSV, TXT, XLS, XLSX, and XML. These parsers are used
to import levy data from county assessor's office.
"""

import os
import io
import csv
import logging
import re
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Tuple, Any, Optional, Union

logger = logging.getLogger(__name__)

class LevyExportFormat(Enum):
    """Enum for supported levy export file formats."""
    TXT = auto()
    CSV = auto()
    XLS = auto()
    XLSX = auto()
    XML = auto()
    UNKNOWN = auto()


class LevyExportData:
    """Class representing parsed levy export data."""
    
    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {
            'file_format': None,
            'imported_at': datetime.utcnow(),
            'total_records': 0,
            'years': set(),
            'tax_districts': set(),
            'levy_codes': set()
        }
    
    def add_record(self, record: Dict[str, Any]) -> None:
        """Add a record to the levy export data."""
        self.records.append(record)
        self.metadata['total_records'] += 1
        
        if 'year' in record:
            self.metadata['years'].add(record['year'])
        
        if 'tax_district_id' in record:
            self.metadata['tax_districts'].add(record['tax_district_id'])
        
        if 'levy_cd' in record:
            self.metadata['levy_codes'].add(record['levy_cd'])
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert the levy export data to a pandas DataFrame."""
        return pd.DataFrame(self.records)
    
    def get_years(self) -> List[int]:
        """Get a sorted list of unique years in the levy export data."""
        return sorted(list(self.metadata['years']))
    
    def get_tax_districts(self) -> List[str]:
        """Get a sorted list of unique tax districts in the levy export data."""
        return sorted(list(self.metadata['tax_districts']))
    
    def get_levy_codes(self) -> List[str]:
        """Get a sorted list of unique levy codes in the levy export data."""
        return sorted(list(self.metadata['levy_codes']))
    
    def __len__(self) -> int:
        """Return the number of records in the levy export data."""
        return len(self.records)


class LevyExportParser:
    """Base class for levy export file parsers."""
    
    def __init__(self):
        self.data = LevyExportData()
    
    def parse(self, file_path: str) -> LevyExportData:
        """Parse the levy export file."""
        raise NotImplementedError("Subclasses must implement parse method.")
    
    @staticmethod
    def detect_format(file_path: str) -> LevyExportFormat:
        """Detect the format of the levy export file."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.txt':
            return LevyExportFormat.TXT
        elif ext == '.csv':
            return LevyExportFormat.CSV
        elif ext == '.xls':
            return LevyExportFormat.XLS
        elif ext == '.xlsx':
            return LevyExportFormat.XLSX
        elif ext == '.xml':
            return LevyExportFormat.XML
        else:
            return LevyExportFormat.UNKNOWN
    
    @staticmethod
    def create_parser(file_format: LevyExportFormat) -> 'LevyExportParser':
        """Create a parser for the specified file format."""
        if file_format == LevyExportFormat.TXT:
            return TextLevyExportParser()
        elif file_format == LevyExportFormat.CSV:
            return CsvLevyExportParser()
        elif file_format == LevyExportFormat.XLS:
            return ExcelLevyExportParser()
        elif file_format == LevyExportFormat.XLSX:
            return ExcelLevyExportParser()
        elif file_format == LevyExportFormat.XML:
            return XmlLevyExportParser()
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
    
    @staticmethod
    def parse_file(file_path: str) -> LevyExportData:
        """Parse a levy export file, automatically detecting the format."""
        file_format = LevyExportParser.detect_format(file_path)
        if file_format == LevyExportFormat.UNKNOWN:
            raise ValueError(f"Unable to detect format for file: {file_path}")
        
        parser = LevyExportParser.create_parser(file_format)
        return parser.parse(file_path)


class TextLevyExportParser(LevyExportParser):
    """Parser for text/CSV levy export files."""
    
    def parse(self, file_path: str) -> LevyExportData:
        """Parse a text levy export file."""
        self.data = LevyExportData()
        self.data.metadata['file_format'] = LevyExportFormat.TXT
        
        try:
            with open(file_path, 'r') as f:
                # Read the first line to get the headers
                header_line = f.readline().strip()
                headers = [h.strip() for h in re.split(r'\s+', header_line)]
                
                # Read the rest of the lines
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Split the line by whitespace
                    values = [v.strip() for v in re.split(r'\s+', line)]
                    
                    # Create a record dictionary
                    record = {}
                    for i, header in enumerate(headers):
                        if i < len(values):
                            # Convert to appropriate type (int for tax_district_id and year)
                            if header == 'tax_district_id' or header == 'year':
                                try:
                                    record[header] = int(values[i])
                                except ValueError:
                                    record[header] = values[i]
                            else:
                                record[header] = values[i]
                    
                    self.data.add_record(record)
            
            logger.info(f"Parsed {len(self.data)} records from text file: {file_path}")
            return self.data
        
        except Exception as e:
            logger.error(f"Error parsing text file: {str(e)}")
            raise


class CsvLevyExportParser(LevyExportParser):
    """Parser for CSV levy export files."""
    
    def parse(self, file_path: str) -> LevyExportData:
        """Parse a CSV levy export file."""
        self.data = LevyExportData()
        self.data.metadata['file_format'] = LevyExportFormat.CSV
        
        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    record = {}
                    for key, value in row.items():
                        # Convert to appropriate type (int for tax_district_id and year)
                        if key == 'tax_district_id' or key == 'year':
                            try:
                                record[key] = int(value)
                            except ValueError:
                                record[key] = value
                        else:
                            record[key] = value
                    
                    self.data.add_record(record)
            
            logger.info(f"Parsed {len(self.data)} records from CSV file: {file_path}")
            return self.data
        
        except Exception as e:
            logger.error(f"Error parsing CSV file: {str(e)}")
            raise


class ExcelLevyExportParser(LevyExportParser):
    """Parser for Excel (XLS/XLSX) levy export files."""
    
    def parse(self, file_path: str) -> LevyExportData:
        """Parse an Excel levy export file."""
        self.data = LevyExportData()
        
        # Determine file format
        _, ext = os.path.splitext(file_path)
        if ext.lower() == '.xls':
            self.data.metadata['file_format'] = LevyExportFormat.XLS
        else:
            self.data.metadata['file_format'] = LevyExportFormat.XLSX
        
        try:
            # Read the Excel file
            df = pd.read_excel(file_path)
            
            # Convert the DataFrame to records
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    # Convert to appropriate type (int for tax_district_id and year)
                    if col == 'tax_district_id' or col == 'year':
                        try:
                            record[col] = int(row[col])
                        except (ValueError, TypeError):
                            record[col] = row[col]
                    else:
                        record[col] = row[col]
                
                self.data.add_record(record)
            
            logger.info(f"Parsed {len(self.data)} records from Excel file: {file_path}")
            return self.data
        
        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise


class XmlLevyExportParser(LevyExportParser):
    """Parser for XML levy export files."""
    
    def parse(self, file_path: str) -> LevyExportData:
        """Parse an XML levy export file."""
        self.data = LevyExportData()
        self.data.metadata['file_format'] = LevyExportFormat.XML
        
        try:
            # Parse the XML file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # For Excel-generated XML files, look for the Worksheet and Rows
            # Excel XML namespace
            namespaces = {
                'ss': 'urn:schemas-microsoft-com:office:spreadsheet'
            }
            
            # Find worksheet containing data (usually named __levy_link)
            worksheet = root.find('.//ss:Worksheet[@ss:Name="__levy_link"]', namespaces)
            if worksheet is None:
                # Try finding any worksheet
                worksheet = root.find('.//ss:Worksheet', namespaces)
            
            if worksheet is None:
                raise ValueError("Could not find worksheet in XML file")
            
            # Find table in worksheet
            table = worksheet.find('.//ss:Table', namespaces)
            if table is None:
                raise ValueError("Could not find table in worksheet")
            
            # Get all rows in the table
            rows = table.findall('.//ss:Row', namespaces)
            if not rows:
                raise ValueError("No rows found in table")
            
            # Extract headers from the first row
            header_row = rows[0]
            header_cells = header_row.findall('.//ss:Cell', namespaces)
            headers = []
            
            for cell in header_cells:
                data = cell.find('.//ss:Data', namespaces)
                if data is not None:
                    headers.append(data.text)
            
            # Process data rows
            for row_idx, row in enumerate(rows[1:], start=1):
                record = {}
                cells = row.findall('.//ss:Cell', namespaces)
                
                for cell_idx, cell in enumerate(cells):
                    if cell_idx < len(headers):
                        data = cell.find('.//ss:Data', namespaces)
                        if data is not None:
                            header = headers[cell_idx]
                            value = data.text
                            
                            # Convert to appropriate type (int for tax_district_id and year)
                            if header == 'tax_district_id' or header == 'year':
                                try:
                                    record[header] = int(value)
                                except ValueError:
                                    record[header] = value
                            else:
                                record[header] = value
                
                if record:  # Only add non-empty records
                    self.data.add_record(record)
            
            logger.info(f"Parsed {len(self.data)} records from XML file: {file_path}")
            return self.data
        
        except Exception as e:
            logger.error(f"Error parsing XML file: {str(e)}")
            raise


# Utility functions for working with levy export data
def merge_levy_export_data(data_list: List[LevyExportData]) -> LevyExportData:
    """Merge multiple levy export data objects into one."""
    merged_data = LevyExportData()
    
    for data in data_list:
        for record in data.records:
            merged_data.add_record(record.copy())
    
    return merged_data


def filter_levy_export_data_by_year(data: LevyExportData, year: int) -> LevyExportData:
    """Filter levy export data to only include records for a specific year."""
    filtered_data = LevyExportData()
    
    for record in data.records:
        if record.get('year') == year:
            filtered_data.add_record(record.copy())
    
    return filtered_data


def get_levy_data_summary(data: LevyExportData) -> Dict[str, Any]:
    """Generate a summary of levy export data."""
    summary = {
        'total_records': len(data),
        'years': sorted(list(data.metadata['years'])),
        'tax_districts': len(data.metadata['tax_districts']),
        'levy_codes': len(data.metadata['levy_codes']),
        'file_format': data.metadata['file_format'].name if data.metadata['file_format'] else 'Unknown',
        'imported_at': data.metadata['imported_at']
    }
    
    return summary