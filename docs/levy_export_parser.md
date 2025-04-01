# Levy Export Parser

The Levy Export Parser is a utility for parsing levy export files from county assessor's offices. It supports multiple file formats including:

- Plain text files (.txt)
- CSV files (.csv)
- Excel 97-2003 (.xls)
- Excel 2007+ (.xlsx)
- XML Spreadsheet 2003 (.xml)

## Overview

The parser is designed to handle various file formats and extract standardized data, making it easy to work with levy export data regardless of the source format.

## Key Components

### LevyExportFormat

An enumeration of supported file formats:

- `TXT`: Plain text files
- `CSV`: CSV files
- `XLS`: Excel 97-2003 files
- `XLSX`: Excel 2007+ files
- `XML`: XML files
- `UNKNOWN`: Unsupported or unknown file formats

### LevyExportData

A class that stores parsed levy export data and metadata:

- `records`: List of records extracted from the levy export file
- `metadata`: Dictionary containing metadata about the file and extracted data

Methods:
- `add_record(record)`: Add a record to the levy export data
- `to_dataframe()`: Convert the levy export data to a pandas DataFrame
- `get_years()`: Get a sorted list of unique years in the levy export data
- `get_tax_districts()`: Get a sorted list of unique tax districts in the levy export data
- `get_levy_codes()`: Get a sorted list of unique levy codes in the levy export data

### LevyExportParser

The base class for all levy export file parsers:

Static Methods:
- `detect_format(file_path)`: Detect the format of a levy export file based on its extension
- `create_parser(file_format)`: Create a parser for the specified file format
- `parse_file(file_path)`: Parse a levy export file, automatically detecting the format

### Format-Specific Parsers

- `TextLevyExportParser`: Parser for text/CSV levy export files
- `CsvLevyExportParser`: Parser for CSV levy export files
- `ExcelLevyExportParser`: Parser for Excel (XLS/XLSX) levy export files
- `XmlLevyExportParser`: Parser for XML levy export files

## Utility Functions

- `merge_levy_export_data(data_list)`: Merge multiple levy export data objects into one
- `filter_levy_export_data_by_year(data, year)`: Filter levy export data to only include records for a specific year
- `get_levy_data_summary(data)`: Generate a summary of levy export data

## Usage Examples

### Detecting File Format

```python
from utils.levy_export_parser import LevyExportParser

file_path = "levy_export.xlsx"
file_format = LevyExportParser.detect_format(file_path)
print(f"Detected format: {file_format.name}")
```

### Parsing a File

```python
from utils.levy_export_parser import LevyExportParser

file_path = "levy_export.xlsx"
levy_data = LevyExportParser.parse_file(file_path)

# Print summary of parsed data
print(f"Parsed {len(levy_data)} records")
print(f"Years: {levy_data.get_years()}")
print(f"Tax Districts: {len(levy_data.metadata['tax_districts'])}")
print(f"Levy Codes: {len(levy_data.metadata['levy_codes'])}")
```

### Converting to DataFrame

```python
from utils.levy_export_parser import LevyExportParser

file_path = "levy_export.xlsx"
levy_data = LevyExportParser.parse_file(file_path)

# Convert to pandas DataFrame
df = levy_data.to_dataframe()

# Perform data analysis
print(df.describe())
```

### Filtering by Year

```python
from utils.levy_export_parser import LevyExportParser, filter_levy_export_data_by_year

file_path = "levy_export.xlsx"
levy_data = LevyExportParser.parse_file(file_path)

# Filter data for a specific year
year_data = filter_levy_export_data_by_year(levy_data, 2022)
print(f"Records for 2022: {len(year_data)}")
```

## Integration with the Application

The levy export parser is integrated with the application in the following ways:

1. **Direct Parsing**: The `/levy-exports/parse-direct` route allows users to parse levy export files directly without importing them into the database.

2. **Enhanced Import Process**: The levy export routes use the parser to handle uploads and imports of levy export files in various formats.

3. **Fallback Mechanism**: The application uses the enhanced parser first, but falls back to legacy parsers if needed.

## Schema Expectations

The parser expects the following columns to be present in the levy export files:

- `tax_district_id`: The ID of the tax district (int)
- `year`: The tax year (int)
- `levy_cd`: The levy code (string)
- `levy_cd_linked`: The linked levy code (string)

Additional columns may be present and will be preserved in the parsed data, but these four columns are required for full functionality.

## Error Handling

The parser includes comprehensive error handling:

- Format detection based on file extension
- Graceful handling of missing or invalid data
- Exception handling for file I/O issues
- Fallback mechanisms when enhanced parsing fails

## Testing

Unit tests for the levy export parser are available in `tests/test_levy_export_parser.py`. These tests verify:

- Format detection based on file extension
- Parser creation for different formats
- Adding records and updating metadata
- Accessing records and metadata through getter methods