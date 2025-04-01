"""
Test script for the levy export parser with attached sample files.
"""
import os
import logging
import pandas as pd
from utils.levy_export_parser import LevyExportParser, LevyExportFormat

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_parse_txt_file():
    """Test parsing a TXT levy export file."""
    file_path = os.path.join('attached_assets', 'Levy Expot.txt')
    if not os.path.exists(file_path):
        logger.error(f"Sample TXT file not found: {file_path}")
        return False
    
    try:
        # Detect the file format
        file_format = LevyExportParser.detect_format(file_path)
        logger.info(f"Detected format: {file_format.name}")
        
        # Parse the file
        levy_data = LevyExportParser.parse_file(file_path)
        
        # Print summary information
        logger.info(f"Parsed {len(levy_data)} records")
        logger.info(f"Years: {levy_data.get_years()}")
        logger.info(f"Tax Districts: {len(levy_data.get_tax_districts())}")
        logger.info(f"Levy Codes: {len(levy_data.get_levy_codes())}")
        
        # Print the first few records
        logger.info("First 5 records:")
        df = levy_data.to_dataframe()
        logger.info("\n" + str(df.head()))
        
        return True
    except Exception as e:
        logger.error(f"Error parsing TXT file: {str(e)}", exc_info=True)
        return False

def test_parse_excel_file():
    """Test parsing an Excel levy export file."""
    for ext in ['.xlsx', '.xls']:
        file_path = os.path.join('attached_assets', f'Levy Expot{ext}')
        if not os.path.exists(file_path):
            logger.warning(f"Sample Excel file not found: {file_path}")
            continue
        
        try:
            # Detect the file format
            file_format = LevyExportParser.detect_format(file_path)
            logger.info(f"Detected format: {file_format.name}")
            
            # Parse the file
            levy_data = LevyExportParser.parse_file(file_path)
            
            # Print summary information
            logger.info(f"Parsed {len(levy_data)} records")
            logger.info(f"Years: {levy_data.get_years()}")
            logger.info(f"Tax Districts: {len(levy_data.get_tax_districts())}")
            logger.info(f"Levy Codes: {len(levy_data.get_levy_codes())}")
            
            # Print the first few records
            logger.info("First 5 records:")
            df = levy_data.to_dataframe()
            logger.info("\n" + str(df.head()))
            
            return True
        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}", exc_info=True)
            return False
    
    logger.warning("No Excel files found for testing")
    return False

def manual_parse_txt_file():
    """Manually parse the TXT file using pandas for validation."""
    file_path = os.path.join('attached_assets', 'Levy Expot.txt')
    if not os.path.exists(file_path):
        logger.error(f"Sample TXT file not found: {file_path}")
        return False
    
    try:
        # Use pandas to read the file
        df = pd.read_csv(file_path, sep=r'\s+')
        
        # Print summary information
        logger.info(f"Manually parsed {len(df)} records")
        logger.info(f"Columns: {list(df.columns)}")
        logger.info("First 5 records:")
        logger.info("\n" + str(df.head()))
        
        return True
    except Exception as e:
        logger.error(f"Error manually parsing TXT file: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Testing levy export parser with sample files...")
    
    # Test TXT file parsing
    logger.info("\n===== TESTING TXT FILE PARSING =====")
    if test_parse_txt_file():
        logger.info("TXT file parsing test passed")
    else:
        logger.error("TXT file parsing test failed")
        logger.info("\n===== TRYING MANUAL PARSE FOR VALIDATION =====")
        manual_parse_txt_file()
    
    # Test Excel file parsing
    logger.info("\n===== TESTING EXCEL FILE PARSING =====")
    if test_parse_excel_file():
        logger.info("Excel file parsing test passed")
    else:
        logger.error("Excel file parsing test failed")
    
    logger.info("Levy export parser testing completed")