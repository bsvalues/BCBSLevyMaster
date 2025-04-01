# SaaS Levy Calculation Application

A Flask-based SaaS application for property tax levy calculations, leveraging AI and advanced data analytics to provide comprehensive tax assessment insights for county assessors.

## Overview

This application is designed for the Benton County Assessor's office in Washington state. It handles property tax levy calculations, statutory compliance, and related functionalities for property tax administration. The system supports data import/export, levy calculations, property lookups, tax district management, and comprehensive reporting capabilities.

## Features

- **Property Tax Levy Calculations**: Calculate levy rates and amounts based on assessed values
- **Multi-Year Analysis**: Track and analyze tax rates across multiple years
- **Interactive Visualizations**: Visualization system with enhanced charting and real-time filtering
- **AI-Enhanced Forecasting**: Claude 3.5 Sonnet integration for intelligent model selection and natural language explanations
- **Bill Impact Calculator**: Analyze effects of pending legislation on tax rates
- **Anomaly Detection**: Identify unusual patterns in historical tax rate data
- **Statutory Compliance Reports**: Detailed compliance checks with tabbed interface
- **Data Management**: Table-level snapshots with configurable retention periods
- **Audit Trail**: Detailed tracking of all data changes with before/after comparison
- **Public Portal**: Mobile-optimized public interface with property lookup and glossary
- **Tax Terminology**: Interactive tooltips and comprehensive glossary

## Technical Stack

- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL with Flask-Migrate for migrations
- **AI Integration**: Anthropic Claude 3.5 Sonnet
- **Data Processing**: Pandas and NumPy
- **Statistical Analysis**: scikit-learn and statsmodels
- **Frontend**: Bootstrap with responsive design

## Getting Started

### Prerequisites

- Python 3.11
- PostgreSQL database
- Anthropic API key (for AI features)

### Installation

1. Clone the repository
2. Set up environment variables:
   ```
   DATABASE_URL=postgresql://user:password@localhost/dbname
   ANTHROPIC_API_KEY=your_api_key
   SESSION_SECRET=your_session_secret
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up the database:
   ```
   python migrate.py upgrade
   ```
5. Run the application:
   ```
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

### Database Migrations

The application uses Flask-Migrate for database schema changes. See [docs/migration_guide.md](docs/migration_guide.md) for detailed instructions.

### Development

```
python main.py
```

### Production Deployment

See [docs/deployment.md](docs/deployment.md) for production deployment instructions.

## Documentation

- [docs/migration_guide.md](docs/migration_guide.md): Database migration guide
- [docs/deployment.md](docs/deployment.md): Production deployment guide

## License

This project is proprietary and confidential.

## Acknowledgments

- Benton County Assessor's Office
- Flask and SQLAlchemy communities
- Anthropic for Claude AI services