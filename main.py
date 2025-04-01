import os
import logging
from app import app

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import routes here to ensure routes are registered with the Flask app
import routes
import routes_data_management
import routes_historical_analysis
import routes_glossary
import routes_public
from utils.tooltip_utils import initialize_tooltip_jinja_filters

# Initialize data management routes
routes_data_management.init_data_management_routes()

# Initialize historical analysis routes
routes_historical_analysis.init_historical_analysis_routes(app)

# Initialize glossary routes
routes_glossary.init_glossary_routes(app)

# Initialize public portal routes
routes_public.init_public_routes()

# Initialize tooltip functionality
initialize_tooltip_jinja_filters(app)

# Initialize MCP if enabled
MCP_ENABLED = os.environ.get('ENABLE_MCP', 'true').lower() in ('true', '1', 'yes')

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
        
        logging.info("MCP integration successfully initialized and enabled")
    except Exception as e:
        logging.error(f"Failed to initialize MCP integration: {str(e)}")
        logging.error("Application will run without MCP features")
else:
    logging.info("MCP integration disabled by environment configuration")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
