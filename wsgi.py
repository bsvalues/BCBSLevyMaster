"""
WSGI entry point for production deployment.

This module provides a production-ready WSGI application configured for the 
Levy Calculation Application. It uses the application factory pattern with 
the production configuration.

Usage:
    gunicorn --bind 0.0.0.0:5000 wsgi:app
"""

import os
from app import create_app

# Set environment to production
os.environ['FLASK_ENV'] = 'production'

# Create the application with production configuration
app = create_app('production')

# Register all routes and extensions
with app.app_context():
    # Import routes
    import routes
    import routes_data_management
    import routes_historical_analysis
    import routes_glossary
    import routes_public
    import routes_forecasting
    import routes_reports
    from utils.tooltip_utils import initialize_tooltip_jinja_filters
    from utils.filter_utils import setup_jinja_filters
    
    # Initialize data management routes
    routes_data_management.init_data_management_routes()
    
    # Initialize historical analysis routes
    routes_historical_analysis.init_historical_analysis_routes(app)
    
    # Initialize glossary routes
    routes_glossary.init_glossary_routes(app)
    
    # Initialize public portal routes
    routes_public.init_public_routes()
    
    # Initialize forecasting routes
    routes_forecasting.init_forecasting_routes()
    
    # Initialize report routes
    routes_reports.init_report_routes()
    
    # Initialize Jinja filters
    setup_jinja_filters(app)
    
    # Initialize tooltip functionality
    initialize_tooltip_jinja_filters(app)
    
    # Initialize MCP if enabled
    MCP_ENABLED = app.config.get('ENABLE_MCP', True)
    
    if MCP_ENABLED:
        try:
            # Import MCP modules
            from utils.mcp_integration import init_mcp, init_mcp_api_routes, enhance_routes_with_mcp
            
            # Initialize MCP integration
            init_mcp()
            
            # Initialize MCP API routes
            init_mcp_api_routes(app)
            
            # Enhance existing routes with MCP intelligence
            enhance_routes_with_mcp(app)
            
            app.logger.info("MCP integration successfully initialized and enabled")
        except Exception as e:
            app.logger.error(f"Failed to initialize MCP integration: {str(e)}")
            app.logger.error("Application will run without MCP features")
    else:
        app.logger.info("MCP integration disabled by configuration")

# This app object is used by gunicorn or other WSGI servers
if __name__ == "__main__":
    # This can be used for testing the production configuration locally
    app.run(host="0.0.0.0", port=5000)