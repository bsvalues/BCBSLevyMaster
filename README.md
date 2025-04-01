# SaaS Levy Calculation Application

A comprehensive property tax levy calculation system developed for county assessors, featuring AI-powered insights, efficient data processing, and statutory compliance.

## Features

### Core Functionality

- **Property Management**: Import, view, and manage property data with assessed values
- **Tax Code Management**: Configure tax codes and levy rates
- **District Relationship Management**: Define and maintain tax district relationships
- **Levy Calculator**: Calculate and apply statutory limits to levy rates
- **Property Lookup**: Quick access to property details and tax calculations
- **Reports**: Generate comprehensive tax roll reports

### AI Capabilities

- **Claude 3.5 Sonnet Integration**: Powered by Anthropic's cutting-edge LLM
- **Property Analysis**: AI-driven insights on property assessments and tax implications
- **Levy Rate Analysis**: Intelligent analysis of levy rates, distributions, and statutory compliance
- **Model Content Protocol (MCP)**: Standardized framework for AI agent capabilities
- **Visualized Insights**: Interactive charts and visualizations of AI-generated data

### Data Processing

- **Multi-Format Import**: Support for CSV, TXT, XML, and Excel files
- **Validation Engine**: Comprehensive data validation and error handling
- **Batch Processing**: Efficient handling of large property datasets
- **Audit Logging**: Detailed logs for import and export operations

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Anthropic API key for Claude integration

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/saas-levy-calculation.git
   cd saas-levy-calculation
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   export DATABASE_URL=postgresql://username:password@localhost/levy_calc
   export ANTHROPIC_API_KEY=your_api_key  # Optional, for AI features
   export SESSION_SECRET=your_secret_key
   ```

4. Initialize the database:
   ```
   python seed_data.py
   ```

5. Start the application:
   ```
   python main.py
   ```

The application will be available at `http://localhost:5000`.

### Sample Data

Sample data is provided for development and testing:
- `seed_data.py`: Creates sample properties, tax codes, and districts

## Usage

### Data Import

1. **Property Import**: Upload CSV files with property IDs, assessed values, and tax codes
2. **District Import**: Upload tax district relationships via TXT, XML, or Excel files

### Levy Calculation

1. Navigate to the Levy Calculator
2. Enter levy amounts for each tax code
3. Calculate levy rates based on assessed values
4. Review AI-powered insights and recommendations
5. Apply statutory limits automatically

### Property Lookup

1. Enter a property ID in the lookup form
2. View property details, tax code information, and calculated tax
3. Explore AI-generated insights about the property

### Reports

1. Navigate to the Reports section
2. Generate a tax roll report
3. Download the CSV file with property tax calculations

## API Documentation

The application provides a RESTful API for integration with other systems:

- `/api/tax-codes`: Get tax code information
- `/api/district-summary`: Get district relationship summary

See [API Documentation](docs/api.md) for details.

## Project Structure

```
├── app.py                # Flask application configuration
├── main.py               # Application entry point
├── models.py             # Database models
├── routes.py             # Route handlers
├── seed_data.py          # Sample data generator
├── add_import_type_migration.py  # Database migration script
├── utils/                # Utility modules
│   ├── __init__.py
│   ├── anthropic_utils.py  # Claude AI integration
│   ├── district_utils.py   # District processing utilities
│   ├── export_utils.py     # Export functionality
│   ├── import_utils.py     # Import functionality
│   ├── levy_utils.py       # Levy calculation utilities
│   └── mcp_core.py         # Model Content Protocol core
├── templates/            # HTML templates
│   ├── index.html          # Dashboard template
│   ├── import.html         # Import page template
│   ├── districts.html      # Districts page template
│   ├── levy_calculator.html  # Levy calculator template
│   ├── property_lookup.html  # Property lookup template
│   ├── reports.html        # Reports page template
│   └── mcp_insights.html   # AI insights page template
├── static/               # Static assets
│   ├── css/                # Stylesheets
│   ├── js/                 # JavaScript files
│   └── img/                # Images
├── tests/                # Test suite
│   ├── conftest.py         # Test configuration
│   ├── test_models.py      # Database model tests
│   ├── test_routes.py      # Route handler tests
│   ├── test_utils.py       # Utility function tests
│   └── test_anthropic.py   # Claude integration tests
└── docs/                 # Documentation
    ├── api.md              # API documentation
    ├── data_dictionary.md  # Data model documentation
    └── mcp_framework.md    # MCP framework documentation
```

## Model Content Protocol (MCP)

The MCP framework provides standardized interfaces for AI capabilities:

- **Function Registry**: Centralized repository of AI functions
- **AI Agents**: Specialized agents for different tasks
- **Workflows**: Predefined sequences of AI operations
- **Claude Integration**: Interface to Claude 3.5 Sonnet LLM

See [MCP Framework Documentation](docs/mcp_framework.md) for details.

## Data Dictionary

For information about the database models and fields, see the [Data Dictionary](docs/data_dictionary.md).

## Testing

Run the test suite with pytest:

```
pytest
```

The test suite includes:
- Database model tests
- Route handler tests
- Utility function tests
- Claude integration tests (with mocks)

## Compliance

This application helps ensure compliance with Washington state property tax statutes:
- 101% cap on levy rate increases
- $5.90 per $1,000 maximum levy rate

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Anthropic Claude for AI capabilities
- Flask and SQLAlchemy for the web framework
- Bootstrap for the responsive UI design