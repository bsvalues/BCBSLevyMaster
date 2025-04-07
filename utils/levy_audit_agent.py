"""
Levy Audit Agent Implementation for the Levy Calculation System.

This module provides the "Lev" AI agent, an expert in property tax and levy auditing,
which assists users in understanding, auditing, and optimizing levy processes.
The agent provides:
- Levy compliance verification
- Expert property tax law guidance
- Contextual recommendations for levy optimization
- Natural language explanations of complex levy concepts
- Historical, current, and potential future levy law insights
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple, cast

from utils.anthropic_utils import get_claude_service, check_api_key_status
from utils.mcp_agents import MCPAgent
from utils.mcp_core import registry
from utils.html_sanitizer import sanitize_html, sanitize_mcp_insights
from utils.api_logging import APICallRecord, api_tracker

logger = logging.getLogger(__name__)

class LevyAuditAgent(MCPAgent):
    """
    Advanced AI agent specialized in levy auditing and property tax expertise.
    
    This agent extends the base MCPAgent with specialized capabilities for:
    - Levy compliance verification against local, state, and federal requirements
    - Historical and current property tax law expertise
    - Contextual recommendations for levy optimization and compliance
    - Interactive auditing workflow assistance
    - Natural language explanations of complex levy concepts
    """
    
    def __init__(self):
        """Initialize the Levy Audit Agent."""
        super().__init__(
            name="Lev",
            description="World's foremost expert in property tax and levy auditing"
        )
        
        # Register specialized capabilities
        self.register_capability("audit_levy_compliance")
        self.register_capability("explain_levy_law")
        self.register_capability("provide_levy_recommendations")
        self.register_capability("process_levy_query")
        self.register_capability("verify_levy_calculation")
        
        # Claude service for AI capabilities
        self.claude = get_claude_service()
        
        # Conversation history for multi-turn dialogue
        self.conversation_history = []
        
    def audit_levy_compliance(self, 
                            district_id: str,
                            year: int,
                            full_audit: bool = False) -> Dict[str, Any]:
        """
        Audit a tax district's levy for compliance with applicable laws.
        
        Args:
            district_id: Tax district identifier
            year: Assessment year
            full_audit: Whether to perform a comprehensive audit (more detailed)
            
        Returns:
            Compliance audit results with findings and recommendations
        """
        if not self.claude:
            return {
                "error": "Claude service not available",
                "audit_results": "Levy compliance audit not available"
            }
        
        # Get district information from the registry
        district_info = registry.execute_function(
            "get_district_details",
            {"district_id": district_id}
        )
        
        # Get levy data for the specified year
        levy_data = registry.execute_function(
            "get_district_levy_data",
            {"district_id": district_id, "year": year}
        )
        
        # Get historical rates for context
        historical_rates = registry.execute_function(
            "get_district_historical_rates",
            {"district_id": district_id, "years": 5}  # Last 5 years for context
        )
        
        # Determine the appropriate compliance rules to check
        district_type = district_info.get("district_type", "UNKNOWN")
        state = district_info.get("state", "WA")  # Default to Washington state
        
        # Set up the audit prompt based on the district details
        audit_depth = "comprehensive" if full_audit else "standard"
        
        prompt = f"""
        As Lev, the world's foremost expert in property tax and levy auditing, perform a {audit_depth} 
        compliance audit for the following tax district's levy data for {year}.
        
        District Information:
        {json.dumps(district_info, indent=2)}
        
        Levy Data for {year}:
        {json.dumps(levy_data, indent=2)}
        
        Historical Rates (for context):
        {json.dumps(historical_rates, indent=2)}
        
        Please perform a thorough compliance analysis considering:
        1. Applicable {state} state laws for {district_type} tax districts
        2. Federal requirements that may apply
        3. Local ordinances and special provisions
        4. Levy rate limits and statutory caps
        5. Year-over-year increase restrictions
        6. Special exemptions or circumstances
        7. Procedural compliance requirements
        
        For each finding, indicate:
        - The specific compliance issue or confirmation
        - The relevant statute or regulation
        - The severity level (Critical, High, Medium, Low, or Compliant)
        - Specific recommendation for addressing any issues
        
        Format your response as JSON with the following structure:
        {{
            "district_name": "{district_info.get('name', 'Unknown District')}",
            "audit_year": {year},
            "audit_type": "{audit_depth}",
            "compliance_summary": "string",
            "compliance_score": "percentage as float",
            "findings": [
                {{
                    "area": "string",
                    "status": "Critical|High|Medium|Low|Compliant",
                    "finding": "string",
                    "regulation": "string",
                    "recommendation": "string"
                }},
                // More findings...
            ],
            "overall_recommendations": ["string", "string", ...],
            "potential_risks": ["string", "string", ...]
        }}
        """
        
        try:
            # Use Claude to generate the compliance audit
            response = self.claude.generate_text(prompt)
            
            # Extract JSON from response
            result = json.loads(response)
            logger.info(f"Successfully generated levy compliance audit for district {district_id}, year {year}")
            
            # Sanitize the result to prevent XSS
            sanitized_result = sanitize_mcp_insights(result)
            return sanitized_result
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response")
            return {
                "error": "Failed to process audit results",
                "district_name": district_info.get("name", "Unknown District"),
                "audit_year": year,
                "audit_type": audit_depth,
                "compliance_summary": "Audit processing error",
                "compliance_score": 0.0,
                "findings": [],
                "overall_recommendations": [
                    "Please try running the audit again",
                    "Contact system administrator if the problem persists"
                ],
                "potential_risks": [
                    "Audit failed to complete - compliance status unknown"
                ]
            }
        except Exception as e:
            logger.error(f"Error in levy compliance audit: {str(e)}")
            return {"error": sanitize_html(str(e))}
    
    def explain_levy_law(self, 
                       topic: str,
                       jurisdiction: str = "WA", 
                       level_of_detail: str = "standard") -> Dict[str, Any]:
        """
        Provide expert explanation of property tax and levy laws.
        
        Args:
            topic: The specific levy or tax law topic to explain
            jurisdiction: State or jurisdiction code (default: WA for Washington)
            level_of_detail: Level of detail for the explanation (basic, standard, detailed)
            
        Returns:
            Detailed explanation with relevant citations and practical implications
        """
        if not self.claude:
            return {
                "error": "Claude service not available",
                "explanation": "Levy law explanation not available"
            }
        
        # Convert level of detail to appropriate depth
        detail_level_map = {
            "basic": "a concise overview accessible to non-specialists",
            "standard": "a comprehensive explanation with key details",
            "detailed": "an in-depth analysis with extensive citations and nuances"
        }
        detail_level = detail_level_map.get(level_of_detail.lower(), "a comprehensive explanation with key details")
        
        prompt = f"""
        As Lev, the world's foremost expert in property tax and levy laws, provide {detail_level}
        of '{topic}' under {jurisdiction} jurisdiction.
        
        Include in your explanation:
        1. The fundamental purpose and principles of this aspect of levy law
        2. Relevant statutory references and citations
        3. How this applies in practice for tax districts and property owners
        4. Common misconceptions or areas of confusion
        5. Recent developments or changes to be aware of
        6. Practical implications for levy calculation and administration
        
        Format your response as JSON with the following structure:
        {{
            "topic": "{topic}",
            "jurisdiction": "{jurisdiction}",
            "overview": "string",
            "key_principles": ["string", "string", ...],
            "statutory_references": ["string", "string", ...],
            "practical_applications": ["string", "string", ...],
            "common_misconceptions": ["string", "string", ...],
            "recent_developments": ["string", "string", ...],
            "see_also": ["string", "string", ...]
        }}
        """
        
        try:
            # Use Claude to generate the explanation
            response = self.claude.generate_text(prompt)
            
            # Extract JSON from response
            result = json.loads(response)
            logger.info(f"Successfully generated levy law explanation for topic: {topic}")
            
            # Sanitize the result to prevent XSS
            sanitized_result = sanitize_mcp_insights(result)
            return sanitized_result
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response")
            return {
                "topic": topic,
                "jurisdiction": jurisdiction,
                "overview": "Error processing explanation request",
                "key_principles": [],
                "statutory_references": [],
                "practical_applications": [],
                "common_misconceptions": [],
                "recent_developments": [],
                "see_also": []
            }
        except Exception as e:
            logger.error(f"Error generating levy law explanation: {str(e)}")
            return {"error": sanitize_html(str(e))}
    
    def provide_levy_recommendations(self,
                                  district_id: str,
                                  year: int,
                                  focus_area: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate contextual recommendations for levy optimization and compliance.
        
        Args:
            district_id: Tax district identifier 
            year: Assessment year
            focus_area: Specific area of focus (compliance, optimization, public communication)
            
        Returns:
            Tailored recommendations with justifications and priority levels
        """
        if not self.claude:
            return {
                "error": "Claude service not available",
                "recommendations": []
            }
        
        # Get district information from the registry
        district_info = registry.execute_function(
            "get_district_details",
            {"district_id": district_id}
        )
        
        # Get levy data for the specified year
        levy_data = registry.execute_function(
            "get_district_levy_data",
            {"district_id": district_id, "year": year}
        )
        
        # Get historical rates for context
        historical_rates = registry.execute_function(
            "get_district_historical_rates",
            {"district_id": district_id, "years": 5}  # Last 5 years for context
        )
        
        # Determine focus areas based on input
        if not focus_area:
            focus_areas = ["compliance", "optimization", "communication"]
        else:
            focus_areas = [focus_area]
        
        prompt = f"""
        As Lev, the world's foremost expert in property tax and levy optimization, analyze the 
        following tax district data and provide strategic recommendations focused on {', '.join(focus_areas)}.
        
        District Information:
        {json.dumps(district_info, indent=2)}
        
        Levy Data for {year}:
        {json.dumps(levy_data, indent=2)}
        
        Historical Rates (for context):
        {json.dumps(historical_rates, indent=2)}
        
        Based on this data, provide:
        1. Strategic recommendations for improving levy {', '.join(focus_areas)}
        2. Data-driven justification for each recommendation
        3. Priority level and potential impact of each recommendation
        4. Implementation considerations and potential challenges
        
        Format your response as JSON with the following structure:
        {{
            "district_name": "{district_info.get('name', 'Unknown District')}",
            "assessment_year": {year},
            "focus_areas": {json.dumps(focus_areas)},
            "executive_summary": "string",
            "recommendations": [
                {{
                    "title": "string",
                    "description": "string",
                    "justification": "string",
                    "focus_area": "compliance|optimization|communication",
                    "priority": "critical|high|medium|low",
                    "implementation_considerations": "string"
                }},
                // More recommendations...
            ],
            "additional_insights": ["string", "string", ...]
        }}
        """
        
        try:
            # Use Claude to generate recommendations
            response = self.claude.generate_text(prompt)
            
            # Extract JSON from response
            result = json.loads(response)
            logger.info(f"Successfully generated levy recommendations for district {district_id}")
            
            # Sanitize the result to prevent XSS
            sanitized_result = sanitize_mcp_insights(result)
            return sanitized_result
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response")
            return {
                "district_name": district_info.get("name", "Unknown District"),
                "assessment_year": year,
                "focus_areas": focus_areas,
                "executive_summary": "Error processing recommendation request",
                "recommendations": [],
                "additional_insights": []
            }
        except Exception as e:
            logger.error(f"Error generating levy recommendations: {str(e)}")
            return {"error": sanitize_html(str(e))}
    
    def process_levy_query(self,
                         query: str,
                         context: Optional[Dict[str, Any]] = None,
                         add_to_history: bool = True) -> Dict[str, Any]:
        """
        Process a natural language query about levy and property tax topics.
        
        Args:
            query: Natural language query
            context: Additional context for the query (district, year, etc.)
            add_to_history: Whether to add this interaction to conversation history
            
        Returns:
            Response to the natural language query with relevant explanations
        """
        if not self.claude:
            return {
                "error": "Claude service not available",
                "response": "Query processing not available"
            }
        
        # Add query to conversation history if enabled
        if add_to_history:
            self.conversation_history.append({
                "role": "user",
                "content": query,
                "timestamp": datetime.now().isoformat()
            })
        
        # Prepare context for the query
        context_data = ""
        if context:
            context_data = f"Context Information:\n{json.dumps(context, indent=2)}\n\n"
        
        # Include relevant conversation history for continuity
        history_text = ""
        if self.conversation_history and len(self.conversation_history) > 1:
            history_text = "Previous conversation:\n"
            for i, entry in enumerate(self.conversation_history[:-1]):
                history_text += f"{entry['role'].title()}: {entry['content']}\n"
            history_text += "\n"
        
        prompt = f"""
        As Lev, the world's foremost expert in property tax and levy laws, respond to the following query:
        
        {history_text}
        {context_data}
        User Query: {query}
        
        Provide a comprehensive answer that demonstrates your deep expertise in property tax systems, levy laws,
        and assessment procedures. Include:
        
        1. A direct answer to the query
        2. Relevant citations or references if applicable
        3. Practical implications and considerations
        4. Any relevant historical context or future developments
        5. Follow-up suggestions that might be useful
        
        Format your response as JSON with the following structure:
        {{
            "query": "{query}",
            "answer": "string",
            "citations": ["string", "string", ...],
            "practical_implications": ["string", "string", ...],
            "additional_context": "string",
            "follow_up_questions": ["string", "string", ...]
        }}
        """
        
        try:
            # Use Claude to process the query
            response = self.claude.generate_text(prompt)
            
            # Extract JSON from response
            result = json.loads(response)
            logger.info(f"Successfully processed levy query: {query[:50]}...")
            
            # Add response to conversation history if enabled
            if add_to_history:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "timestamp": datetime.now().isoformat()
                })
            
            # Sanitize the result to prevent XSS
            sanitized_result = sanitize_mcp_insights(result)
            return sanitized_result
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response")
            return {
                "query": query,
                "answer": "I'm sorry, but I couldn't properly process your query about levy or property tax. Please try rephrasing your question.",
                "citations": [],
                "practical_implications": [],
                "additional_context": "",
                "follow_up_questions": [
                    "Could you rephrase your question about the levy process?",
                    "Would you like information about a specific aspect of property tax laws?",
                    "Are you looking for information about a particular jurisdiction?"
                ]
            }
        except Exception as e:
            logger.error(f"Error processing levy query: {str(e)}")
            return {"error": sanitize_html(str(e))}
    
    def verify_levy_calculation(self,
                              tax_code_id: str,
                              property_value: float,
                              year: Optional[int] = None) -> Dict[str, Any]:
        """
        Verify a levy calculation and provide expert analysis.
        
        Args:
            tax_code_id: Tax code identifier
            property_value: Property assessed value
            year: Assessment year (optional, defaults to current)
            
        Returns:
            Verification results with detailed analysis and recommendations
        """
        if not self.claude:
            return {
                "error": "Claude service not available",
                "verification": "Levy calculation verification not available"
            }
        
        try:
            # Get tax code details
            tax_code = registry.execute_function(
                "get_tax_code_details",
                {"tax_code_id": tax_code_id}
            )
            
            # Get district information
            district_id = tax_code.get("tax_district_id")
            district = registry.execute_function(
                "get_district_details",
                {"district_id": district_id}
            )
            
            # Calculate levy amount
            levy_rate = tax_code.get("levy_rate", 0)
            
            # If year is provided, try to get the historical rate
            if year:
                historical_rate = registry.execute_function(
                    "get_historical_rate",
                    {"tax_code_id": tax_code_id, "year": year}
                )
                if historical_rate:
                    levy_rate = historical_rate.get("levy_rate", levy_rate)
            
            # Calculate tax amount (property value / 1000 * levy rate)
            calculated_amount = (property_value / 1000) * levy_rate
            
            # Prepare data for verification
            verification_data = {
                "tax_code": tax_code,
                "district": district,
                "property_value": property_value,
                "levy_rate": levy_rate,
                "calculated_amount": calculated_amount,
                "year": year or "current"
            }
            
            prompt = f"""
            As Lev, the world's foremost expert in property tax and levy calculation, verify and analyze the following levy calculation:
            
            Tax Code Information:
            {json.dumps(tax_code, indent=2)}
            
            District Information:
            {json.dumps(district, indent=2)}
            
            Calculation Details:
            - Property Value: ${property_value:,.2f}
            - Levy Rate: {levy_rate} per $1,000 assessed value
            - Calculated Levy Amount: ${calculated_amount:,.2f}
            - Assessment Year: {year or "Current"}
            
            Please provide:
            1. Verification of this calculation's accuracy
            2. Analysis of the effective tax rate relative to comparable properties/districts
            3. Applicable exemptions or special considerations that might apply
            4. Recommendations for the property owner or tax authority
            
            Format your response as JSON with the following structure:
            {{
                "verification_result": "correct|incorrect|needs_review",
                "calculation_analysis": "string",
                "effective_tax_rate": "percentage as float",
                "comparative_analysis": "string",
                "potential_exemptions": ["string", "string", ...],
                "recommendations": ["string", "string", ...],
                "additional_insights": "string"
            }}
            """
            
            # Use Claude to verify the calculation
            response = self.claude.generate_text(prompt)
            
            # Extract JSON from response
            result = json.loads(response)
            logger.info(f"Successfully verified levy calculation for tax code {tax_code_id}")
            
            # Add the calculation details to the result
            result["calculation_details"] = {
                "property_value": property_value,
                "levy_rate": levy_rate,
                "calculated_amount": calculated_amount,
                "tax_code": tax_code.get("tax_code", tax_code_id),
                "district_name": district.get("name", "Unknown District"),
                "year": year or "current"
            }
            
            # Sanitize the result to prevent XSS
            sanitized_result = sanitize_mcp_insights(result)
            return sanitized_result
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response")
            return {
                "verification_result": "error",
                "calculation_analysis": "Error processing verification request",
                "effective_tax_rate": 0.0,
                "comparative_analysis": "",
                "potential_exemptions": [],
                "recommendations": [
                    "Please try the verification again",
                    "Contact system administrator if the problem persists"
                ],
                "additional_insights": "",
                "calculation_details": {
                    "property_value": property_value,
                    "levy_rate": 0,
                    "calculated_amount": 0,
                    "tax_code": tax_code_id,
                    "district_name": "Unknown",
                    "year": year or "current"
                }
            }
        except Exception as e:
            logger.error(f"Error verifying levy calculation: {str(e)}")
            return {"error": sanitize_html(str(e))}


# Singleton instance
levy_audit_agent = None

def init_levy_audit_agent():
    """Initialize the levy audit agent and register its functions."""
    global levy_audit_agent
    
    try:
        # Create the agent instance
        agent = LevyAuditAgent()
        
        # Register the agent's functions with the MCP registry
        registry.register_function(
            func=agent.audit_levy_compliance,
            name="audit_levy_compliance",
            description="Audit a tax district's levy for compliance with applicable laws",
            parameter_schema={
                "type": "object",
                "properties": {
                    "district_id": {
                        "type": "string",
                        "description": "Tax district identifier"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Assessment year"
                    },
                    "full_audit": {
                        "type": "boolean",
                        "description": "Whether to perform a comprehensive audit"
                    }
                },
                "required": ["district_id", "year"]
            }
        )
        
        registry.register_function(
            func=agent.explain_levy_law,
            name="explain_levy_law",
            description="Provide expert explanation of property tax and levy laws",
            parameter_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific levy or tax law topic to explain"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "description": "State or jurisdiction code"
                    },
                    "level_of_detail": {
                        "type": "string",
                        "description": "Level of detail for the explanation (basic, standard, detailed)"
                    }
                },
                "required": ["topic"]
            }
        )
        
        registry.register_function(
            func=agent.provide_levy_recommendations,
            name="provide_levy_recommendations",
            description="Generate contextual recommendations for levy optimization and compliance",
            parameter_schema={
                "type": "object",
                "properties": {
                    "district_id": {
                        "type": "string",
                        "description": "Tax district identifier"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Assessment year"
                    },
                    "focus_area": {
                        "type": "string",
                        "description": "Specific area of focus (compliance, optimization, public communication)"
                    }
                },
                "required": ["district_id", "year"]
            }
        )
        
        registry.register_function(
            func=agent.process_levy_query,
            name="process_levy_query",
            description="Process a natural language query about levy and property tax topics",
            parameter_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for the query (district, year, etc.)"
                    },
                    "add_to_history": {
                        "type": "boolean",
                        "description": "Whether to add this interaction to conversation history"
                    }
                },
                "required": ["query"]
            }
        )
        
        registry.register_function(
            func=agent.verify_levy_calculation,
            name="verify_levy_calculation",
            description="Verify a levy calculation and provide expert analysis",
            parameter_schema={
                "type": "object",
                "properties": {
                    "tax_code_id": {
                        "type": "string",
                        "description": "Tax code identifier"
                    },
                    "property_value": {
                        "type": "number",
                        "description": "Property assessed value"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Assessment year (optional, defaults to current)"
                    }
                },
                "required": ["tax_code_id", "property_value"]
            }
        )
        
        logger.info("Levy Audit Agent initialized and registered")
        return agent
        
    except Exception as e:
        logger.error(f"Error initializing levy audit agent: {str(e)}")
        return None


def get_levy_audit_agent():
    """Get the levy audit agent instance, initializing it if necessary."""
    global levy_audit_agent
    if levy_audit_agent is None:
        try:
            levy_audit_agent = init_levy_audit_agent()
            if levy_audit_agent is None:
                logger.error("Failed to initialize levy audit agent")
                # Create a new instance if initialization failed
                levy_audit_agent = LevyAuditAgent()
        except Exception as e:
            logger.error(f"Error initializing levy audit agent: {str(e)}")
            # Create a new instance if initialization failed with an exception
            levy_audit_agent = LevyAuditAgent()
    return levy_audit_agent