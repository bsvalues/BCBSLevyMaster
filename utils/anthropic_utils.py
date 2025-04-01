"""
Anthropic Claude integration utilities for the SaaS Levy Calculation Application.

This module provides Claude-specific functionality and integration with the
Model Content Protocol (MCP) framework.
"""

import os
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Union

import anthropic
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for interacting with Anthropic's Claude models."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the Claude service.
        
        Args:
            api_key: Anthropic API key (if None, will look for ANTHROPIC_API_KEY env var)
            model: Claude model to use, defaults to the latest model
        """
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        self.model = model
        self.client = Anthropic(api_key=api_key)
        logger.info(f"Initialized Claude service with model: {model}")
    
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, 
                     temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate text using Claude.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system instructions
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        logger.debug(f"Generating text with prompt: {prompt[:100]}...")
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the text from the response
            return message.content[0].text
        except Exception as e:
            logger.error(f"Error generating text with Claude: {str(e)}")
            return f"Error: {str(e)}"
    
    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None,
            temperature: float = 0.7, max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Chat with Claude using a conversation history.
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
                     Roles should be 'user' or 'assistant'
            system_prompt: Optional system instructions
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response object containing generated message
        """
        logger.debug(f"Chatting with {len(messages)} messages")
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages
            )
            
            # Return a dictionary with the response text
            return {"text": message.content[0].text}
        except Exception as e:
            logger.error(f"Error chatting with Claude: {str(e)}")
            return {"error": str(e)}
    
    def analyze_property_data(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze property data using Claude intelligence.
        
        Args:
            property_data: Dictionary containing property information
            
        Returns:
            Dictionary with analysis insights
        """
        # Create a prompt for Claude to analyze the property data
        prompt = f"""
        Please analyze this property tax data and provide insights:
        
        Property ID: {property_data.get('property_id')}
        Assessed Value: ${property_data.get('assessed_value', 0):,.2f}
        Tax Code: {property_data.get('tax_code')}
        Levy Rate: {property_data.get('levy_rate', 0):.2f} per $1,000
        
        I need a comprehensive analysis of this property's tax situation including:
        1. Assessment insights: How does this property compare to others? Is the assessed value reasonable?
        2. Tax burden: Is the tax burden for this property typical, high, or low?
        3. Recommendations: What should the property owner know about their property taxes?
        
        Provide your analysis in a structured JSON format with 'insights' and 'recommendations' keys.
        """
        
        system_prompt = """
        You are an expert property tax analyst working for a county assessor's office.
        Provide detailed, fact-based analysis of property tax data.
        Format your response as valid JSON with no preamble or explanations outside the JSON structure.
        """
        
        # Generate the analysis
        try:
            response = self.generate_text(prompt, system_prompt, temperature=0.3)
            
            # Parse the JSON response
            analysis = json.loads(response)
            return analysis
        except json.JSONDecodeError:
            logger.error("Failed to parse Claude response as JSON")
            # Return a simple structure if parsing fails
            return {
                "insights": "Error parsing analysis",
                "recommendations": ["Please try again"]
            }
        except Exception as e:
            logger.error(f"Error analyzing property data: {str(e)}")
            return {
                "insights": f"Error during analysis: {str(e)}",
                "recommendations": ["System encountered an error during analysis"]
            }
    
    def generate_levy_insights(self, levy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate insights about levy calculations using Claude intelligence.
        
        Args:
            levy_data: Dictionary containing levy information
            
        Returns:
            Dictionary with analysis insights
        """
        # Create a prompt for Claude to analyze the levy data
        tax_codes = levy_data.get("tax_codes", [])
        total_assessed_value = levy_data.get("total_assessed_value", 0)
        
        tax_code_details = "\n".join([
            f"Tax Code: {tc.get('code')}, Levy Rate: {tc.get('levy_rate', 0):.2f}, " +
            f"Levy Amount: ${tc.get('levy_amount', 0):,.2f}"
            for tc in tax_codes
        ])
        
        prompt = f"""
        Please analyze this levy calculation data and provide insights:
        
        Total Assessed Value: ${total_assessed_value:,.2f}
        Number of Tax Codes: {len(tax_codes)}
        
        Tax Code Details:
        {tax_code_details}
        
        I need a comprehensive analysis of these levy calculations including:
        1. Distribution analysis: How is the tax burden distributed across tax codes?
        2. Rate analysis: Are the levy rates reasonable and compliant with statutory limits?
        3. Key highlights: What are the most important things to note about these levy calculations?
        4. Recommendations: What actions should be considered based on this analysis?
        
        Provide your analysis in a structured JSON format with 'analysis', 'highlights', and 'recommendations' keys.
        """
        
        system_prompt = """
        You are an expert property tax analyst working for a county assessor's office.
        Provide detailed, fact-based analysis of levy calculations data.
        Format your response as valid JSON with no preamble or explanations outside the JSON structure.
        """
        
        # Generate the analysis
        try:
            response = self.generate_text(prompt, system_prompt, temperature=0.3)
            
            # Parse the JSON response
            analysis = json.loads(response)
            return analysis
        except json.JSONDecodeError:
            logger.error("Failed to parse Claude response as JSON")
            # Return a simple structure if parsing fails
            return {
                "analysis": "Error parsing analysis",
                "highlights": ["Unable to parse response"],
                "recommendations": ["Please try again"]
            }
        except Exception as e:
            logger.error(f"Error analyzing levy data: {str(e)}")
            return {
                "analysis": f"Error during analysis: {str(e)}",
                "highlights": ["System encountered an error"],
                "recommendations": ["System encountered an error during analysis"]
            }


def get_claude_service() -> Optional[ClaudeService]:
    """
    Get a configured Claude service instance if possible.
    
    Returns:
        ClaudeService instance or None if API key not available
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not found in environment, Claude features disabled")
        return None
    
    try:
        return ClaudeService(api_key=api_key)
    except Exception as e:
        logger.error(f"Error initializing Claude service: {str(e)}")
        return None