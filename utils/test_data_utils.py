"""
Utility functions for managing test data files.
"""
import os
import shutil
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def copy_sample_files_to_temp():
    """
    Copy sample data files from attached_assets to a temporary directory for testing.
    
    Returns:
        dict: Dictionary mapping file types to their paths
    """
    # Create temp directory if it doesn't exist
    temp_dir = Path('/tmp/levy_test_data')
    if not temp_dir.exists():
        temp_dir.mkdir(parents=True)
    
    # Define source and destination paths
    source_files = {
        'txt': Path('attached_assets/Levy Expot.txt'),
        'xls': Path('attached_assets/Levy Expot.xls'),
        'xlsx': Path('attached_assets/Levy Expot.xlsx'),
        'xml': Path('attached_assets/Levy Expot.xml'),
    }
    
    # Copy files and build result dictionary
    result = {}
    for file_type, source_path in source_files.items():
        if source_path.exists():
            dest_path = temp_dir / f"sample_levy_export.{file_type}"
            try:
                shutil.copy2(source_path, dest_path)
                logger.info(f"Copied {file_type} sample file to {dest_path}")
                result[file_type] = str(dest_path)
            except Exception as e:
                logger.error(f"Error copying {file_type} file: {str(e)}")
        else:
            logger.warning(f"Sample file not found: {source_path}")
    
    return result

def get_sample_file_path(file_type='txt'):
    """
    Get the path to a sample file of the specified type.
    
    Args:
        file_type: Type of file to return ('txt', 'xls', 'xlsx', 'xml')
        
    Returns:
        Path object to the sample file or None if not available
    """
    temp_dir = Path('/tmp/levy_test_data')
    sample_path = temp_dir / f"sample_levy_export.{file_type}"
    
    # Copy files if they don't exist
    if not sample_path.exists():
        copy_sample_files_to_temp()
    
    return sample_path if sample_path.exists() else None