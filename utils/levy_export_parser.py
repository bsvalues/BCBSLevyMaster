"""
Levy Export Parser.

This module provides utilities for parsing levy export files 
in various formats (TXT, XLS, XLSX, XML).
"""

import os
import csv
import re
import logging
from enum import Enum, auto
import pandas as pd
import xml.etree.ElementTree as ET


class LevyExportFormat(Enum):
    """
    Enumeration of levy export file formats.
    """
    TXT = auto()
    XLS = auto()
    XLSX = auto()
    XML = auto()
    
    @classmethod
    def from_extension(cls, extension):
        """
        Get format from file extension.
        
        Args:
            extension: File extension (with or without leading dot)
            
        Returns:
            LevyExportFormat enum value or None if not supported
        """
        extension = extension.lower().lstrip('.')
        
        if extension == 'txt':
            return cls.TXT
        elif extension == 'xls':
            return cls.XLS
        elif extension == 'xlsx':
            return cls.XLSX
        elif extension == 'xml':
            return cls.XML
        else:
            return None

# Configure logger
logger = logging.getLogger(__name__)


class LevyExportParser:
    """
    Parser for levy export files from tax assessment systems.
    Supports various file formats and extracts structured data.
    """
    
    def __init__(self, file_path):
        """
        Initialize the parser with a file path.
        
        Args:
            file_path: Path to the levy export file
            
        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file type is not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        self.file_path = file_path
        self.file_type = self._determine_file_type(file_path)
        
        if self.file_type not in ["txt", "xls", "xlsx", "xml"]:
            raise ValueError(f"Unsupported file type: {self.file_type}")
    
    def _determine_file_type(self, file_path):
        """
        Determine the file type from the extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            String file type (lowercase extension without dot)
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower().lstrip(".")
    
    def parse(self):
        """
        Parse the file and extract structured data.
        
        Returns:
            Dict containing extracted data with keys:
            - districts: List of tax district data
            - tax_codes: List of tax code data
            - properties: List of property data
            
        Raises:
            ValueError: If parsing fails
        """
        try:
            if self.file_type == "txt":
                return self._parse_txt()
            elif self.file_type == "xls":
                return self._parse_xls()
            elif self.file_type == "xlsx":
                return self._parse_xlsx()
            elif self.file_type == "xml":
                return self._parse_xml()
            else:
                raise ValueError(f"Unsupported file type: {self.file_type}")
        except Exception as e:
            logger.error(f"Error parsing file {self.file_path}: {str(e)}")
            raise
    
    def _parse_txt(self):
        """
        Parse TXT format levy export file.
        
        Returns:
            Dict containing extracted data
        """
        with open(self.file_path, 'r') as file:
            content = file.read()
            
        # Extract year from the content
        year = self._extract_year_from_content(content)
        
        # Split content into sections
        sections = self._split_txt_sections(content)
        
        # Parse districts
        districts = self._parse_txt_districts(sections.get('districts', ''), year)
        
        # Parse tax codes
        tax_codes = self._parse_txt_tax_codes(sections.get('tax_codes', ''), year)
        
        # Parse properties
        properties = self._parse_txt_properties(sections.get('properties', ''))
        
        return {
            'districts': districts,
            'tax_codes': tax_codes,
            'properties': properties,
            'year': year
        }
    
    def _parse_xls(self):
        """
        Parse XLS format levy export file.
        
        Returns:
            Dict containing extracted data
        """
        try:
            # Read the Excel file
            df = pd.read_excel(self.file_path, sheet_name=None)
            
            # Process each sheet
            result = {
                'districts': [],
                'tax_codes': [],
                'properties': []
            }
            
            # Extract year from the file content
            year = None
            
            # Try to find the year in the first sheet
            if len(df) > 0:
                first_sheet = list(df.values())[0]
                year_str = str(first_sheet.iloc[0, 0]) if not first_sheet.empty else ""
                year = self._extract_year_from_content(year_str)
            
            # Process each sheet based on its content
            for sheet_name, sheet_df in df.items():
                if 'district' in sheet_name.lower():
                    districts = self._parse_excel_districts(sheet_df, year)
                    result['districts'].extend(districts)
                elif 'code' in sheet_name.lower() or 'levy' in sheet_name.lower():
                    tax_codes = self._parse_excel_tax_codes(sheet_df, year)
                    result['tax_codes'].extend(tax_codes)
                elif 'property' in sheet_name.lower() or 'parcel' in sheet_name.lower():
                    properties = self._parse_excel_properties(sheet_df)
                    result['properties'].extend(properties)
            
            return result
        except Exception as e:
            logger.error(f"Error parsing XLS file: {str(e)}")
            # Return minimal structure on error
            return {'districts': [], 'tax_codes': [], 'properties': []}
    
    def _parse_xlsx(self):
        """
        Parse XLSX format levy export file.
        
        Returns:
            Dict containing extracted data
        """
        return self._parse_xls()  # Same processing logic as XLS
    
    def _parse_xml(self):
        """
        Parse XML format levy export file.
        
        Returns:
            Dict containing extracted data
        """
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            
            # Initialize result
            result = {
                'districts': [],
                'tax_codes': [],
                'properties': []
            }
            
            # Extract year from XML
            year_element = root.find('.//Year') or root.find('.//year')
            year = int(year_element.text) if year_element is not None else None
            
            # Parse districts
            for district_elem in root.findall('.//District') or root.findall('.//district'):
                district = {
                    'district_id': self._get_xml_text(district_elem, 'ID') or self._get_xml_text(district_elem, 'Id'),
                    'name': self._get_xml_text(district_elem, 'Name') or self._get_xml_text(district_elem, 'name'),
                    'year': year
                }
                result['districts'].append(district)
            
            # Parse tax codes
            for tax_code_elem in root.findall('.//TaxCode') or root.findall('.//taxCode'):
                tax_code = {
                    'code': self._get_xml_text(tax_code_elem, 'Code') or self._get_xml_text(tax_code_elem, 'code'),
                    'levy_amount': float(self._get_xml_text(tax_code_elem, 'LevyAmount') or 
                                        self._get_xml_text(tax_code_elem, 'levyAmount') or 0),
                    'levy_rate': float(self._get_xml_text(tax_code_elem, 'LevyRate') or 
                                      self._get_xml_text(tax_code_elem, 'levyRate') or 0),
                    'total_assessed_value': float(self._get_xml_text(tax_code_elem, 'TotalAssessedValue') or 
                                                 self._get_xml_text(tax_code_elem, 'totalAssessedValue') or 0),
                    'year': year
                }
                result['tax_codes'].append(tax_code)
            
            # Parse properties
            for property_elem in root.findall('.//Property') or root.findall('.//property'):
                prop = {
                    'property_id': self._get_xml_text(property_elem, 'ID') or self._get_xml_text(property_elem, 'Id'),
                    'assessed_value': float(self._get_xml_text(property_elem, 'AssessedValue') or 
                                           self._get_xml_text(property_elem, 'assessedValue') or 0),
                    'tax_code': self._get_xml_text(property_elem, 'TaxCode') or self._get_xml_text(property_elem, 'taxCode'),
                    'address': self._get_xml_text(property_elem, 'Address') or self._get_xml_text(property_elem, 'address'),
                    'owner_name': self._get_xml_text(property_elem, 'OwnerName') or self._get_xml_text(property_elem, 'ownerName')
                }
                result['properties'].append(prop)
            
            return result
        except Exception as e:
            logger.error(f"Error parsing XML file: {str(e)}")
            # Return minimal structure on error
            return {'districts': [], 'tax_codes': [], 'properties': []}
    
    def _extract_year_from_content(self, content):
        """
        Extract year from file content.
        
        Args:
            content: File content string
            
        Returns:
            Integer year or None if not found
        """
        # Try to find a year in format "Year: YYYY" or "Tax Year: YYYY"
        year_match = re.search(r'(?:Tax\s+)?Year:\s*(\d{4})', content)
        if year_match:
            return int(year_match.group(1))
        
        # Try to find any 4-digit number that looks like a year (20xx)
        year_match = re.search(r'\b(20\d{2})\b', content)
        if year_match:
            return int(year_match.group(1))
        
        return None
    
    def _split_txt_sections(self, content):
        """
        Split TXT content into logical sections.
        
        Args:
            content: File content string
            
        Returns:
            Dict of section content by section name
        """
        sections = {}
        
        # Define section markers
        section_markers = {
            'districts': ['DISTRICTS', 'TAX DISTRICTS', 'DISTRICT LIST'],
            'tax_codes': ['TAX CODES', 'LEVY CODES', 'CODE LIST'],
            'properties': ['PROPERTIES', 'PARCELS', 'PROPERTY LIST']
        }
        
        # Find each section in the content
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            # Check if this line is a section header
            found_new_section = False
            for section, markers in section_markers.items():
                if any(marker in line.upper() for marker in markers):
                    # Save the current section
                    if current_section:
                        sections[current_section] = '\n'.join(section_content)
                    
                    # Start new section
                    current_section = section
                    section_content = []
                    found_new_section = True
                    break
            
            if not found_new_section and current_section:
                section_content.append(line)
        
        # Save the last section
        if current_section:
            sections[current_section] = '\n'.join(section_content)
        
        return sections
    
    def _parse_txt_districts(self, content, year):
        """
        Parse districts from TXT content.
        
        Args:
            content: District section content
            year: Tax year
            
        Returns:
            List of district dictionaries
        """
        districts = []
        
        # Simple parsing based on line structure
        lines = content.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
                
            # Try to extract district ID and name
            # Assume format like "123 - District Name" or "District Name (123)"
            id_match = re.search(r'(\d+)\s*-\s*(.*)', line) or re.search(r'(.*)\s*\((\d+)\)', line)
            
            if id_match:
                if len(id_match.groups()) == 2:
                    # First pattern: "123 - District Name"
                    if id_match.group(2).strip():  # If name is not empty
                        district = {
                            'district_id': id_match.group(1).strip(),
                            'name': id_match.group(2).strip(),
                            'year': year
                        }
                        districts.append(district)
                    else:  # Second pattern: "District Name (123)"
                        district = {
                            'district_id': id_match.group(2).strip(),
                            'name': id_match.group(1).strip(),
                            'year': year
                        }
                        districts.append(district)
            else:
                # If no pattern matches, try to split by whitespace and hope for the best
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    district = {
                        'district_id': parts[0],
                        'name': ' '.join(parts[1:]),
                        'year': year
                    }
                    districts.append(district)
        
        return districts
    
    def _parse_txt_tax_codes(self, content, year):
        """
        Parse tax codes from TXT content.
        
        Args:
            content: Tax code section content
            year: Tax year
            
        Returns:
            List of tax code dictionaries
        """
        tax_codes = []
        
        # Simple parsing based on line structure
        lines = content.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
                
            # Try to parse tax code data
            # Assume format with code, levy amount, rate, and value in a structured format
            parts = re.split(r'\s{2,}|\t', line)  # Split by multiple spaces or tabs
            
            # Remove empty parts
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 2:
                tax_code = {'year': year}
                
                # First part is assumed to be the code
                tax_code['code'] = parts[0]
                
                # Try to identify other fields based on values
                for part in parts[1:]:
                    # Look for currency values (levy amount)
                    if '$' in part or (part.replace('.', '', 1).isdigit() and float(part) > 1000):
                        try:
                            tax_code['levy_amount'] = float(part.replace('$', '').replace(',', ''))
                        except:
                            pass
                    
                    # Look for small decimal values (levy rate)
                    elif part.replace('.', '', 1).isdigit() and float(part) < 100:
                        try:
                            tax_code['levy_rate'] = float(part)
                        except:
                            pass
                    
                    # Look for large values (assessed value)
                    elif part.replace(',', '').replace('.', '', 1).isdigit() and float(part.replace(',', '')) > 100000:
                        try:
                            tax_code['total_assessed_value'] = float(part.replace(',', ''))
                        except:
                            pass
                
                # Only add if we have at least one of the key fields
                if 'levy_amount' in tax_code or 'levy_rate' in tax_code or 'total_assessed_value' in tax_code:
                    tax_codes.append(tax_code)
        
        return tax_codes
    
    def _parse_txt_properties(self, content):
        """
        Parse properties from TXT content.
        
        Args:
            content: Property section content
            
        Returns:
            List of property dictionaries
        """
        properties = []
        
        # Simple parsing based on line structure
        lines = content.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
                
            # Try to parse property data
            # Assume format with ID, value, tax code, address
            parts = re.split(r'\s{2,}|\t', line)  # Split by multiple spaces or tabs
            
            # Remove empty parts
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 2:
                property = {}
                
                # First part is assumed to be the property ID
                property['property_id'] = parts[0]
                
                # Try to identify other fields based on values
                for i, part in enumerate(parts[1:], 1):
                    # Look for numeric values (assessed value)
                    if part.replace(',', '').replace('.', '', 1).isdigit():
                        try:
                            property['assessed_value'] = float(part.replace(',', ''))
                        except:
                            pass
                    
                    # Look for tax code (usually alphanumeric with dashes)
                    elif re.match(r'[A-Z0-9\-]+', part) and len(part) < 20 and i == 1:
                        property['tax_code'] = part
                    
                    # Look for address (longer text with spaces)
                    elif len(part.split()) > 2 and i >= 2:
                        property['address'] = part
                
                # Only add if we have at least property_id
                if 'property_id' in property:
                    properties.append(property)
        
        return properties
    
    def _parse_excel_districts(self, df, year):
        """
        Parse districts from Excel dataframe.
        
        Args:
            df: DataFrame containing district data
            year: Tax year
            
        Returns:
            List of district dictionaries
        """
        districts = []
        
        # Skip empty dataframes
        if df.empty:
            return districts
        
        # Try to identify column names by similarity
        id_col = None
        name_col = None
        
        for col in df.columns:
            col_str = str(col).lower()
            if any(key in col_str for key in ['id', 'code', 'number']):
                id_col = col
            elif any(key in col_str for key in ['name', 'district', 'description']):
                name_col = col
        
        # If columns couldn't be identified, use positional
        if id_col is None and len(df.columns) > 0:
            id_col = df.columns[0]
        if name_col is None and len(df.columns) > 1:
            name_col = df.columns[1]
        
        # Extract data
        if id_col is not None and name_col is not None:
            for _, row in df.iterrows():
                # Skip rows with missing ID
                if pd.isna(row[id_col]):
                    continue
                    
                district = {
                    'district_id': str(row[id_col]).strip(),
                    'name': str(row[name_col]).strip() if not pd.isna(row[name_col]) else '',
                    'year': year
                }
                districts.append(district)
        
        return districts
    
    def _parse_excel_tax_codes(self, df, year):
        """
        Parse tax codes from Excel dataframe.
        
        Args:
            df: DataFrame containing tax code data
            year: Tax year
            
        Returns:
            List of tax code dictionaries
        """
        tax_codes = []
        
        # Skip empty dataframes
        if df.empty:
            return tax_codes
        
        # Try to identify column names by similarity
        code_col = None
        levy_amount_col = None
        levy_rate_col = None
        assessed_value_col = None
        
        for col in df.columns:
            col_str = str(col).lower()
            if any(key in col_str for key in ['code', 'tax code', 'levy code']):
                code_col = col
            elif any(key in col_str for key in ['amount', 'levy amount', 'total']):
                levy_amount_col = col
            elif any(key in col_str for key in ['rate', 'levy rate']):
                levy_rate_col = col
            elif any(key in col_str for key in ['assessed', 'value', 'valuation']):
                assessed_value_col = col
        
        # Extract data
        if code_col is not None:
            for _, row in df.iterrows():
                # Skip rows with missing code
                if pd.isna(row[code_col]):
                    continue
                    
                tax_code = {
                    'code': str(row[code_col]).strip(),
                    'year': year
                }
                
                # Add levy amount if available
                if levy_amount_col is not None and not pd.isna(row[levy_amount_col]):
                    try:
                        tax_code['levy_amount'] = float(row[levy_amount_col])
                    except:
                        pass
                
                # Add levy rate if available
                if levy_rate_col is not None and not pd.isna(row[levy_rate_col]):
                    try:
                        tax_code['levy_rate'] = float(row[levy_rate_col])
                    except:
                        pass
                
                # Add assessed value if available
                if assessed_value_col is not None and not pd.isna(row[assessed_value_col]):
                    try:
                        tax_code['total_assessed_value'] = float(row[assessed_value_col])
                    except:
                        pass
                
                # Only add if we have at least one of the key fields
                if 'levy_amount' in tax_code or 'levy_rate' in tax_code or 'total_assessed_value' in tax_code:
                    tax_codes.append(tax_code)
        
        return tax_codes
    
    def _parse_excel_properties(self, df):
        """
        Parse properties from Excel dataframe.
        
        Args:
            df: DataFrame containing property data
            
        Returns:
            List of property dictionaries
        """
        properties = []
        
        # Skip empty dataframes
        if df.empty:
            return properties
        
        # Try to identify column names by similarity
        id_col = None
        assessed_value_col = None
        tax_code_col = None
        address_col = None
        owner_col = None
        
        for col in df.columns:
            col_str = str(col).lower()
            if any(key in col_str for key in ['id', 'property id', 'parcel', 'account']):
                id_col = col
            elif any(key in col_str for key in ['assessed', 'value']):
                assessed_value_col = col
            elif any(key in col_str for key in ['tax code', 'levy code']):
                tax_code_col = col
            elif any(key in col_str for key in ['address', 'location']):
                address_col = col
            elif any(key in col_str for key in ['owner', 'name']):
                owner_col = col
        
        # If id column couldn't be identified, use the first column
        if id_col is None and len(df.columns) > 0:
            id_col = df.columns[0]
        
        # Extract data
        if id_col is not None:
            for _, row in df.iterrows():
                # Skip rows with missing ID
                if pd.isna(row[id_col]):
                    continue
                    
                property = {
                    'property_id': str(row[id_col]).strip()
                }
                
                # Add assessed value if available
                if assessed_value_col is not None and not pd.isna(row[assessed_value_col]):
                    try:
                        property['assessed_value'] = float(row[assessed_value_col])
                    except:
                        pass
                
                # Add tax code if available
                if tax_code_col is not None and not pd.isna(row[tax_code_col]):
                    property['tax_code'] = str(row[tax_code_col]).strip()
                
                # Add address if available
                if address_col is not None and not pd.isna(row[address_col]):
                    property['address'] = str(row[address_col]).strip()
                
                # Add owner if available
                if owner_col is not None and not pd.isna(row[owner_col]):
                    property['owner_name'] = str(row[owner_col]).strip()
                
                properties.append(property)
        
        return properties
    
    def _get_xml_text(self, element, tag):
        """
        Extract text from XML element by tag.
        
        Args:
            element: XML element to search in
            tag: Tag to find
            
        Returns:
            Text content or None if not found
        """
        found = element.find(f'.//{tag}')
        return found.text if found is not None else None