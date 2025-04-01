"""
Model Content Protocol (MCP) Integration for SaaS Levy Calculation Application

This module connects the MCP architecture, agents, and LLM capabilities
to the core SaaS Levy Calculation Application.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from functools import wraps

from flask import request, jsonify, session

from app import db
from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog

from utils.mcp_core import (
    ContentBlock,
    ContentType,
    MCPMessage,
    FunctionRegistry,
    mcp_function_registry,
    mcp_workflow_orchestrator,
    create_text_block,
    create_structured_data_block,
    create_function_call_block,
    create_function_response_block
)
from utils.mcp_agents import (
    Agent,
    AgentPhase,
    AgentRepository,
    agent_repository,
    initialize_default_agents,
    AnalysisAgent,
    LevyPredictionAgent,
    CoordinatorAgent
)
from utils.mcp_llm import (
    global_llm_service,
    create_llm_agent
)

from utils.levy_utils import (
    calculate_levy_rates,
    apply_statutory_limits,
    calculate_property_tax
)
from utils.import_utils import (
    validate_and_import_csv,
    update_tax_code_totals
)
from utils.district_utils import (
    import_district_text_file,
    import_district_xml_file,
    import_district_excel_file,
    get_linked_levy_codes
)
from utils.export_utils import (
    generate_tax_roll
)

# Register core application functions with the MCP Function Registry
def register_core_functions():
    """Register core application functions with the MCP Function Registry."""
    
    # Tax code functions
    mcp_function_registry.register_function(
        "get_tax_codes",
        get_tax_codes,
        {
            "description": "Get list of tax codes with their details",
            "parameters": {},
            "returns": {
                "type": "object",
                "description": "Object mapping tax code identifiers to their details"
            }
        }
    )
    
    mcp_function_registry.register_function(
        "get_tax_code_details",
        get_tax_code_details,
        {
            "description": "Get detailed information about a specific tax code",
            "parameters": {
                "code": {
                    "type": "string",
                    "description": "The tax code identifier"
                }
            },
            "returns": {
                "type": "object",
                "description": "Detailed information about the tax code"
            }
        }
    )
    
    # Property functions
    mcp_function_registry.register_function(
        "search_properties",
        search_properties,
        {
            "description": "Search for properties based on criteria",
            "parameters": {
                "property_id": {
                    "type": "string",
                    "description": "Optional property ID to search for"
                },
                "tax_code": {
                    "type": "string",
                    "description": "Optional tax code to filter by"
                },
                "min_value": {
                    "type": "number",
                    "description": "Optional minimum assessed value"
                },
                "max_value": {
                    "type": "number",
                    "description": "Optional maximum assessed value"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return"
                }
            },
            "returns": {
                "type": "array",
                "description": "List of properties matching the criteria"
            }
        }
    )
    
    mcp_function_registry.register_function(
        "get_property_details",
        get_property_details,
        {
            "description": "Get detailed information about a specific property",
            "parameters": {
                "property_id": {
                    "type": "string",
                    "description": "The property ID"
                }
            },
            "returns": {
                "type": "object",
                "description": "Detailed information about the property"
            }
        }
    )
    
    # Tax district functions
    mcp_function_registry.register_function(
        "get_tax_districts",
        get_tax_districts,
        {
            "description": "Get list of tax districts with their details",
            "parameters": {
                "year": {
                    "type": "integer",
                    "description": "Optional year to filter by"
                },
                "district_id": {
                    "type": "integer",
                    "description": "Optional district ID to filter by"
                }
            },
            "returns": {
                "type": "array",
                "description": "List of tax districts matching the criteria"
            }
        }
    )
    
    mcp_function_registry.register_function(
        "get_linked_levy_codes",
        get_linked_levy_codes_func,
        {
            "description": "Get levy codes linked to a specified levy code",
            "parameters": {
                "levy_code": {
                    "type": "string",
                    "description": "The levy code to find links for"
                },
                "year": {
                    "type": "integer",
                    "description": "Optional year to search in"
                }
            },
            "returns": {
                "type": "array",
                "description": "List of linked levy codes"
            }
        }
    )
    
    # Levy calculation functions
    mcp_function_registry.register_function(
        "calculate_levy_rates",
        calculate_levy_rates_func,
        {
            "description": "Calculate levy rates based on levy amounts",
            "parameters": {
                "levy_amounts": {
                    "type": "object",
                    "description": "Dict mapping tax_code to levy_amount"
                }
            },
            "returns": {
                "type": "object",
                "description": "Dict mapping tax_code to calculated levy_rate"
            }
        }
    )
    
    mcp_function_registry.register_function(
        "apply_statutory_limits",
        apply_statutory_limits_func,
        {
            "description": "Apply statutory limits to levy rates",
            "parameters": {
                "levy_rates": {
                    "type": "object",
                    "description": "Dict mapping tax_code to levy_rate"
                }
            },
            "returns": {
                "type": "object",
                "description": "Dict mapping tax_code to limited levy_rate"
            }
        }
    )
    
    mcp_function_registry.register_function(
        "calculate_property_tax",
        calculate_property_tax_func,
        {
            "description": "Calculate tax for a specific property",
            "parameters": {
                "property_id": {
                    "type": "string",
                    "description": "The property ID"
                }
            },
            "returns": {
                "type": "object",
                "description": "Calculated tax amount and details"
            }
        }
    )
    
    # Analysis functions
    mcp_function_registry.register_function(
        "analyze_tax_distribution",
        analyze_tax_distribution,
        {
            "description": "Analyze distribution of tax burden across properties",
            "parameters": {
                "tax_code": {
                    "type": "string",
                    "description": "Optional tax code to analyze"
                }
            },
            "returns": {
                "type": "object",
                "description": "Analysis of tax distribution"
            }
        }
    )
    
    mcp_function_registry.register_function(
        "analyze_historical_trends",
        analyze_historical_trends,
        {
            "description": "Analyze historical trends in levy rates and assessed values",
            "parameters": {
                "years": {
                    "type": "integer",
                    "description": "Number of years to analyze"
                },
                "tax_code": {
                    "type": "string",
                    "description": "Optional tax code to analyze"
                }
            },
            "returns": {
                "type": "object",
                "description": "Analysis of historical trends"
            }
        }
    )
    
    # Import/export functions
    mcp_function_registry.register_function(
        "get_import_logs",
        get_import_logs,
        {
            "description": "Get logs of data import operations",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of logs to return"
                },
                "import_type": {
                    "type": "string",
                    "description": "Optional type of import to filter by"
                }
            },
            "returns": {
                "type": "array",
                "description": "List of import logs"
            }
        }
    )
    
    mcp_function_registry.register_function(
        "get_export_logs",
        get_export_logs,
        {
            "description": "Get logs of data export operations",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of logs to return"
                }
            },
            "returns": {
                "type": "array",
                "description": "List of export logs"
            }
        }
    )
    
    logging.info(f"Registered {len(mcp_function_registry.list_functions())} core functions with MCP")

# Function implementations for MCP Registry
def get_tax_codes():
    """Get list of tax codes with their details."""
    tax_codes = TaxCode.query.all()
    return {
        tc.code: {
            "levy_amount": tc.levy_amount,
            "levy_rate": tc.levy_rate,
            "previous_year_rate": tc.previous_year_rate,
            "total_assessed_value": tc.total_assessed_value,
            "created_at": tc.created_at.isoformat() if tc.created_at else None,
            "updated_at": tc.updated_at.isoformat() if tc.updated_at else None
        }
        for tc in tax_codes
    }

def get_tax_code_details(code):
    """Get detailed information about a specific tax code."""
    tax_code = TaxCode.query.filter_by(code=code).first()
    if not tax_code:
        return {"error": f"Tax code '{code}' not found"}
        
    # Get properties with this tax code
    properties = Property.query.filter_by(tax_code=code).all()
    property_count = len(properties)
    
    # Calculate statistics
    assessed_values = [p.assessed_value for p in properties]
    total_assessed_value = sum(assessed_values)
    avg_assessed_value = total_assessed_value / property_count if property_count > 0 else 0
    
    # Get linked levy codes
    linked_codes = get_linked_levy_codes(code)
    
    return {
        "code": tax_code.code,
        "levy_amount": tax_code.levy_amount,
        "levy_rate": tax_code.levy_rate,
        "previous_year_rate": tax_code.previous_year_rate,
        "total_assessed_value": tax_code.total_assessed_value,
        "property_count": property_count,
        "avg_assessed_value": avg_assessed_value,
        "linked_levy_codes": linked_codes,
        "created_at": tax_code.created_at.isoformat() if tax_code.created_at else None,
        "updated_at": tax_code.updated_at.isoformat() if tax_code.updated_at else None
    }

def search_properties(property_id=None, tax_code=None, min_value=None, max_value=None, limit=100):
    """Search for properties based on criteria."""
    query = Property.query
    
    if property_id:
        query = query.filter(Property.property_id.ilike(f"%{property_id}%"))
        
    if tax_code:
        query = query.filter_by(tax_code=tax_code)
        
    if min_value is not None:
        query = query.filter(Property.assessed_value >= min_value)
        
    if max_value is not None:
        query = query.filter(Property.assessed_value <= max_value)
        
    properties = query.limit(limit).all()
    
    return [
        {
            "id": p.id,
            "property_id": p.property_id,
            "assessed_value": p.assessed_value,
            "tax_code": p.tax_code,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }
        for p in properties
    ]

def get_property_details(property_id):
    """Get detailed information about a specific property."""
    property_obj = Property.query.filter_by(property_id=property_id).first()
    if not property_obj:
        return {"error": f"Property '{property_id}' not found"}
        
    # Get tax code information
    tax_code_obj = TaxCode.query.filter_by(code=property_obj.tax_code).first()
    
    # Calculate property tax if levy rate is available
    calculated_tax = None
    if tax_code_obj and tax_code_obj.levy_rate:
        calculated_tax = (property_obj.assessed_value / 1000) * tax_code_obj.levy_rate
        
    # Get linked levy codes
    linked_levy_codes = get_linked_levy_codes(property_obj.tax_code)
    
    return {
        "id": property_obj.id,
        "property_id": property_obj.property_id,
        "assessed_value": property_obj.assessed_value,
        "tax_code": property_obj.tax_code,
        "levy_rate": tax_code_obj.levy_rate if tax_code_obj else None,
        "calculated_tax": calculated_tax,
        "linked_levy_codes": linked_levy_codes,
        "created_at": property_obj.created_at.isoformat() if property_obj.created_at else None,
        "updated_at": property_obj.updated_at.isoformat() if property_obj.updated_at else None
    }

def get_tax_districts(year=None, district_id=None):
    """Get list of tax districts with their details."""
    query = TaxDistrict.query
    
    if year:
        query = query.filter_by(year=year)
        
    if district_id:
        query = query.filter_by(tax_district_id=district_id)
        
    districts = query.all()
    
    return [
        {
            "id": d.id,
            "tax_district_id": d.tax_district_id,
            "year": d.year,
            "levy_code": d.levy_code,
            "linked_levy_code": d.linked_levy_code,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None
        }
        for d in districts
    ]

def get_linked_levy_codes_func(levy_code, year=None):
    """Get levy codes linked to a specified levy code."""
    return get_linked_levy_codes(levy_code, year)

def calculate_levy_rates_func(levy_amounts):
    """Calculate levy rates based on levy amounts."""
    return calculate_levy_rates(levy_amounts)

def apply_statutory_limits_func(levy_rates):
    """Apply statutory limits to levy rates."""
    return apply_statutory_limits(levy_rates)

def calculate_property_tax_func(property_id):
    """Calculate tax for a specific property."""
    property_obj = Property.query.filter_by(property_id=property_id).first()
    if not property_obj:
        return {"error": f"Property '{property_id}' not found"}
        
    tax_amount = calculate_property_tax(property_obj)
    
    return {
        "property_id": property_id,
        "tax_amount": tax_amount,
        "assessed_value": property_obj.assessed_value,
        "tax_code": property_obj.tax_code
    }

def analyze_tax_distribution(tax_code=None):
    """Analyze distribution of tax burden across properties."""
    # Base query for properties
    query = Property.query
    
    if tax_code:
        query = query.filter_by(tax_code=tax_code)
        
    properties = query.all()
    
    if not properties:
        return {"error": "No properties found for analysis"}
        
    # Calculate basic statistics
    assessed_values = [p.assessed_value for p in properties]
    total_assessed_value = sum(assessed_values)
    avg_assessed_value = total_assessed_value / len(properties)
    
    # Calculate percentiles
    assessed_values.sort()
    count = len(assessed_values)
    
    percentiles = {
        "min": assessed_values[0],
        "p10": assessed_values[int(count * 0.1)],
        "p25": assessed_values[int(count * 0.25)],
        "p50": assessed_values[int(count * 0.5)],
        "p75": assessed_values[int(count * 0.75)],
        "p90": assessed_values[int(count * 0.9)],
        "max": assessed_values[-1]
    }
    
    # Group properties by tax code
    tax_code_distribution = {}
    for p in properties:
        if p.tax_code not in tax_code_distribution:
            tax_code_distribution[p.tax_code] = {
                "count": 0,
                "total_assessed_value": 0,
                "avg_assessed_value": 0
            }
            
        tax_code_distribution[p.tax_code]["count"] += 1
        tax_code_distribution[p.tax_code]["total_assessed_value"] += p.assessed_value
        
    # Calculate averages for each tax code
    for code in tax_code_distribution:
        count = tax_code_distribution[code]["count"]
        total = tax_code_distribution[code]["total_assessed_value"]
        tax_code_distribution[code]["avg_assessed_value"] = total / count
        tax_code_distribution[code]["percent_of_properties"] = (count / len(properties)) * 100
        tax_code_distribution[code]["percent_of_assessed_value"] = (total / total_assessed_value) * 100
        
    return {
        "property_count": len(properties),
        "total_assessed_value": total_assessed_value,
        "avg_assessed_value": avg_assessed_value,
        "percentiles": percentiles,
        "tax_code_distribution": tax_code_distribution,
        "analysis_date": datetime.utcnow().isoformat()
    }

def analyze_historical_trends(years=5, tax_code=None):
    """Analyze historical trends in levy rates and assessed values."""
    # Create mock data for historical analysis (since we don't have actual historical data)
    current_year = datetime.now().year
    
    # Start analysis
    year_data = {}
    
    # Get tax codes to analyze
    tax_codes_query = TaxCode.query
    if tax_code:
        tax_codes_query = tax_codes_query.filter_by(code=tax_code)
        
    tax_codes = tax_codes_query.all()
    
    if not tax_codes:
        return {"error": "No tax codes found for analysis"}
        
    # Current rates
    current_rates = {tc.code: tc.levy_rate for tc in tax_codes if tc.levy_rate is not None}
    current_previous_rates = {tc.code: tc.previous_year_rate for tc in tax_codes if tc.previous_year_rate is not None}
    
    # Construct historical analysis based on available data
    for year_offset in range(years):
        year = current_year - year_offset
        
        if year_offset == 0:
            # Current year data
            year_data[year] = {
                "levy_rates": current_rates,
                "avg_levy_rate": sum(current_rates.values()) / len(current_rates) if current_rates else 0
            }
        elif year_offset == 1:
            # Previous year data (based on previous_year_rate)
            year_data[year] = {
                "levy_rates": current_previous_rates,
                "avg_levy_rate": sum(current_previous_rates.values()) / len(current_previous_rates) if current_previous_rates else 0
            }
        else:
            # For older years, estimate based on trends
            # This is simplified and would need actual historical data in a real implementation
            prev_year = year + 1
            if prev_year in year_data:
                prev_rates = year_data[prev_year]["levy_rates"]
                # Assume 2% annual decrease for demonstration
                estimated_rates = {code: rate * 0.98 for code, rate in prev_rates.items()}
                year_data[year] = {
                    "levy_rates": estimated_rates,
                    "avg_levy_rate": sum(estimated_rates.values()) / len(estimated_rates) if estimated_rates else 0,
                    "estimated": True
                }
    
    # Calculate trends
    trend_analysis = {}
    for code in current_rates:
        rates_by_year = {year: data["levy_rates"].get(code) for year, data in year_data.items() 
                       if code in data["levy_rates"]}
        
        # Filter out None values
        valid_rates = {year: rate for year, rate in rates_by_year.items() if rate is not None}
        
        if len(valid_rates) >= 2:
            years_list = sorted(valid_rates.keys())
            first_year = years_list[0]
            last_year = years_list[-1]
            
            # Calculate compound annual growth rate
            if valid_rates[first_year] > 0:
                years_diff = last_year - first_year
                cagr = ((valid_rates[last_year] / valid_rates[first_year]) ** (1 / years_diff)) - 1
            else:
                cagr = 0
                
            trend_analysis[code] = {
                "first_year": first_year,
                "last_year": last_year,
                "first_rate": valid_rates[first_year],
                "last_rate": valid_rates[last_year],
                "change": valid_rates[last_year] - valid_rates[first_year],
                "percent_change": ((valid_rates[last_year] / valid_rates[first_year]) - 1) * 100 if valid_rates[first_year] > 0 else 0,
                "cagr": cagr * 100
            }
    
    return {
        "years_analyzed": years,
        "tax_codes_analyzed": list(current_rates.keys()),
        "year_data": year_data,
        "trend_analysis": trend_analysis,
        "analysis_date": datetime.utcnow().isoformat()
    }

def get_import_logs(limit=10, import_type=None):
    """Get logs of data import operations."""
    query = ImportLog.query.order_by(ImportLog.import_date.desc())
    
    if import_type:
        query = query.filter_by(import_type=import_type)
        
    logs = query.limit(limit).all()
    
    return [
        {
            "id": log.id,
            "filename": log.filename,
            "rows_imported": log.rows_imported,
            "rows_skipped": log.rows_skipped,
            "warnings": log.warnings,
            "import_date": log.import_date.isoformat() if log.import_date else None,
            "import_type": log.import_type
        }
        for log in logs
    ]

def get_export_logs(limit=10):
    """Get logs of data export operations."""
    logs = ExportLog.query.order_by(ExportLog.export_date.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "filename": log.filename,
            "rows_exported": log.rows_exported,
            "export_date": log.export_date.isoformat() if log.export_date else None
        }
        for log in logs
    ]

# Register MCP workflows for common tasks
def register_workflows():
    """Register workflows with the MCP workflow orchestrator."""
    
    # Define a workflow for analyzing property tax distribution
    tax_distribution_workflow = {
        "name": "tax_distribution_analysis",
        "description": "Analyze property tax distribution across tax codes",
        "steps": [
            {
                "name": "get_tax_codes_step",
                "function": "get_tax_codes",
                "input_mapping": {},
                "error_handling": "fail"
            },
            {
                "name": "analyze_distribution_step",
                "function": "analyze_tax_distribution",
                "input_mapping": {
                    "tax_code": "input.tax_code"
                },
                "error_handling": "fail"
            }
        ]
    }
    mcp_workflow_orchestrator.register_workflow(
        "tax_distribution_analysis",
        tax_distribution_workflow
    )
    
    # Define a workflow for calculating and applying levy rates
    levy_calculation_workflow = {
        "name": "levy_calculation",
        "description": "Calculate and apply levy rates based on amounts",
        "steps": [
            {
                "name": "calculate_rates_step",
                "function": "calculate_levy_rates",
                "input_mapping": {
                    "levy_amounts": "input.levy_amounts"
                },
                "error_handling": "fail"
            },
            {
                "name": "apply_limits_step",
                "function": "apply_statutory_limits",
                "input_mapping": {
                    "levy_rates": "output.calculate_rates_step"
                },
                "error_handling": "fail"
            }
        ]
    }
    mcp_workflow_orchestrator.register_workflow(
        "levy_calculation",
        levy_calculation_workflow
    )
    
    # Define a workflow for property lookup with tax calculation
    property_lookup_workflow = {
        "name": "property_lookup",
        "description": "Look up property and calculate its tax",
        "steps": [
            {
                "name": "get_property_step",
                "function": "get_property_details",
                "input_mapping": {
                    "property_id": "input.property_id"
                },
                "error_handling": "fail"
            },
            {
                "name": "get_tax_code_step",
                "function": "get_tax_code_details",
                "input_mapping": {
                    "code": "output.get_property_step.tax_code"
                },
                "error_handling": "continue"
            },
            {
                "name": "calculate_tax_step",
                "function": "calculate_property_tax",
                "input_mapping": {
                    "property_id": "input.property_id"
                },
                "error_handling": "continue"
            }
        ]
    }
    mcp_workflow_orchestrator.register_workflow(
        "property_lookup",
        property_lookup_workflow
    )
    
    logging.info(f"Registered 3 workflows with MCP")

# Define API routes for MCP interaction
def init_mcp_api_routes(app):
    """Initialize Flask routes for MCP API interaction."""
    
    @app.route('/api/mcp/functions', methods=['GET'])
    def api_mcp_functions():
        """Get list of available MCP functions."""
        return jsonify({
            "functions": mcp_function_registry.get_function_catalog()
        })
    
    @app.route('/api/mcp/workflows', methods=['GET'])
    def api_mcp_workflows():
        """Get list of available MCP workflows."""
        return jsonify({
            "workflows": list(mcp_workflow_orchestrator.workflows.keys())
        })
    
    @app.route('/api/mcp/agents', methods=['GET'])
    def api_mcp_agents():
        """Get list of available MCP agents."""
        return jsonify({
            "agents": agent_repository.list_agents(),
            "capabilities": {
                agent_name: agent_repository.get_agent_capabilities(agent_name)
                for agent_name in agent_repository.list_agents()
            }
        })
    
    @app.route('/api/mcp/execute_function', methods=['POST'])
    def api_execute_function():
        """Execute an MCP function."""
        data = request.json
        
        if not data or 'function' not in data:
            return jsonify({"error": "Missing function name"}), 400
            
        function_name = data['function']
        parameters = data.get('parameters', {})
        
        try:
            function = mcp_function_registry.get_function(function_name)
            result = function(**parameters)
            
            return jsonify({
                "result": result
            })
        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500
    
    @app.route('/api/mcp/execute_workflow', methods=['POST'])
    def api_execute_workflow():
        """Execute an MCP workflow."""
        data = request.json
        
        if not data or 'workflow' not in data:
            return jsonify({"error": "Missing workflow name"}), 400
            
        workflow_name = data['workflow']
        input_data = data.get('input', {})
        
        try:
            result = mcp_workflow_orchestrator.execute_workflow(workflow_name, input_data)
            
            return jsonify({
                "result": result
            })
        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500
    
    @app.route('/api/mcp/agent_request', methods=['POST'])
    def api_agent_request():
        """Send a request to an MCP agent."""
        data = request.json
        
        if not data or 'agent' not in data:
            return jsonify({"error": "Missing agent name"}), 400
            
        agent_name = data['agent']
        content_blocks_data = data.get('content_blocks', [])
        
        try:
            # Create content blocks from data
            content_blocks = []
            for block_data in content_blocks_data:
                content_type = ContentType(block_data.get('content_type', 'text'))
                content = block_data.get('content')
                metadata = block_data.get('metadata', {})
                
                content_blocks.append(ContentBlock(
                    content_type=content_type,
                    content=content,
                    metadata=metadata
                ))
                
            # Create message
            message = MCPMessage(content_blocks=content_blocks)
            
            # Send to agent
            agent = agent_repository.get_agent(agent_name)
            response = agent.process(message)
            
            # Convert response to JSON
            response_data = {
                "message_id": response.message_id,
                "parent_id": response.parent_id,
                "content_blocks": [block.to_dict() for block in response.content_blocks],
                "metadata": response.metadata
            }
            
            return jsonify({
                "response": response_data
            })
        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500
    
    logging.info("Initialized MCP API routes")

# Add MCP intelligence to existing Flask routes
def enhance_routes_with_mcp(app):
    """Add MCP intelligence to existing Flask routes."""
    
    # Store the original route handlers
    original_handlers = {}
    
    # Define a decorator to enhance routes with MCP
    def mcp_enhanced(route_func):
        """Decorator to enhance a route with MCP intelligence."""
        
        @wraps(route_func)
        def wrapper(*args, **kwargs):
            # Call the original route handler
            response = route_func(*args, **kwargs)
            
            # Check if MCP enhancement is enabled for this request
            if request.args.get('enable_mcp', '').lower() in ('true', '1', 'yes'):
                try:
                    # Determine the type of route
                    endpoint = request.endpoint
                    
                    # Create an augmentation agent for the specific route type
                    agent_name = f"RouteAugmentationAgent_{endpoint}"
                    
                    # Check if we already have this agent
                    try:
                        agent = agent_repository.get_agent(agent_name)
                    except KeyError:
                        # Create a new agent for this route
                        llm_service = global_llm_service
                        agent = create_llm_agent(agent_name, f"Enhances {endpoint} route with insights", llm_service)
                        agent_repository.register_agent(agent)
                    
                    # Create content blocks with route information
                    content_blocks = [
                        create_text_block(
                            f"This is a request to the '{endpoint}' endpoint. "
                            f"Please enhance the response with additional insights."
                        ),
                        create_structured_data_block({
                            "endpoint": endpoint,
                            "method": request.method,
                            "args": {k: v for k, v in request.args.items()},
                            "view_data": getattr(response, "_template_context", {})
                        })
                    ]
                    
                    # Create message for the agent
                    message = MCPMessage(content_blocks=content_blocks)
                    
                    # Process with the agent
                    agent_response = agent.process(message)
                    
                    # Extract insights from the agent response
                    insights = {}
                    for block in agent_response.content_blocks:
                        if block.content_type == ContentType.TEXT:
                            insights["narrative"] = block.content
                        elif block.content_type == ContentType.STRUCTURED_DATA:
                            insights["data"] = block.content
                    
                    # Add insights to the template context
                    if hasattr(response, "_template_context") and insights:
                        response._template_context["mcp_insights"] = insights
                
                except Exception as e:
                    logging.error(f"Error enhancing route with MCP: {str(e)}")
            
            return response
        
        return wrapper
    
    # Enhance specific routes with MCP
    for endpoint in app.view_functions:
        if endpoint in ('index', 'levy_calculator', 'property_lookup', 'districts', 'reports'):
            original_handler = app.view_functions[endpoint]
            original_handlers[endpoint] = original_handler
            app.view_functions[endpoint] = mcp_enhanced(original_handler)
    
    logging.info(f"Enhanced {len(original_handlers)} routes with MCP intelligence")

# Initialize the MCP integration
def init_mcp():
    """Initialize the Model Content Protocol integration."""
    
    logging.info("Initializing MCP integration")
    
    # Register core functions
    register_core_functions()
    
    # Register workflows
    register_workflows()
    
    # Initialize default agents
    initialize_default_agents()
    
    logging.info("MCP integration initialized successfully")
    
    return {
        "function_registry": mcp_function_registry,
        "workflow_orchestrator": mcp_workflow_orchestrator,
        "agent_repository": agent_repository
    }