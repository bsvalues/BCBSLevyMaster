#!/usr/bin/env python3
"""
Test script for the Levy Export Parser.

This script tests the enhanced Levy Export Parser by parsing the sample
files in the attached_assets directory.
"""

import os
import sys
import logging
from pathlib import Path

from utils.levy_export_parser import LevyExportParser, LevyExportFormat

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample files to test
SAMPLE_FILES = [
    "attached_assets/Levy Expot.txt",
    "attached_assets/Levy Expot.xls",
    "attached_assets/Levy Expot.xlsx",
    "attached_assets/Levy Expot.xml",
]

def test_format_detection():
    """Test the format detection functionality."""
    logger.info("Testing format detection...")
    
    for file_path in SAMPLE_FILES:
        if not os.path.exists(file_path):
            logger.warning(f"Sample file not found: {file_path}")
            continue
            
        format = LevyExportParser.detect_format(file_path)
        logger.info(f"Detected format for {file_path}: {format.name}")
        
        # Check if the detected format matches the file extension
        extension = Path(file_path).suffix.lower().lstrip('.')
        expected_format = LevyExportFormat[extension.upper()] if hasattr(LevyExportFormat, extension.upper()) else LevyExportFormat.UNKNOWN
        
        if format == expected_format:
            logger.info(f"✅ Format detection successful for {file_path}")
        else:
            logger.warning(f"❌ Format detection failed for {file_path}. Expected {expected_format.name}, got {format.name}")

def test_file_parsing():
    """Test the file parsing functionality."""
    logger.info("Testing file parsing...")
    
    for file_path in SAMPLE_FILES:
        if not os.path.exists(file_path):
            logger.warning(f"Sample file not found: {file_path}")
            continue
            
        try:
            data = LevyExportParser.parse_file(file_path)
            logger.info(f"✅ Successfully parsed {file_path}")
            logger.info(f"Found {len(data)} records")
            logger.info(f"Years: {data.get_years()}")
            logger.info(f"Districts: {data.get_tax_districts()[:5]}...")
            logger.info(f"Levy codes: {data.get_levy_codes()[:5]}...")
            
            # Print a sample record
            if len(data.records) > 0:
                sample_record = data.records[0]
                logger.info(f"Sample record: {sample_record.data}")
                
        except Exception as e:
            logger.error(f"❌ Failed to parse {file_path}: {str(e)}")

def main():
    """Main function."""
    logger.info("Starting Levy Export Parser tests...")
    
    test_format_detection()
    print()
    test_file_parsing()
    
    logger.info("Tests completed.")

if __name__ == "__main__":
    main()