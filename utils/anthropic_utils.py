"""
Anthropic Claude API utilities for the Levy Calculation System.

This module provides utilities for interacting with the Anthropic Claude API
to generate AI-powered insights and explanations for levy calculations.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import anthropic
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class ClaudeService:
    """Service for interacting with the Anthropic Claude API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Claude service.
        
        Args:
            api_key: The Anthropic API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.error("No Anthropic API key provided.")
            raise ValueError("Anthropic API key is required. Please set the ANTHROPIC_API_KEY environment variable.")
        
        self.client = Anthropic(
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            api_key=self.api_key,
        )
        logger.info("ClaudeService initialized successfully")
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             system_prompt: str = None,
             max_tokens: int = 1000,
             temperature: float = 0.7) -> Dict[str, Any]:
        """
        Send a chat request to the Claude API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: System instructions for Claude
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            
        Returns:
            The response from Claude API
        """
        try:
            logger.info(f"Sending chat request with {len(messages)} messages")
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system=system_prompt,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            logger.info(f"Received response with {len(response.content)} content blocks")
            return response
        
        except Exception as e:
            logger.error(f"Error in chat request: {str(e)}")
            raise
    
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate text using the Claude API.
        
        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            
        Returns:
            Generated text response
        """
        messages = [{"role": "user", "content": prompt}]
        response = self.chat(messages, max_tokens=max_tokens, temperature=temperature)
        
        # Extract the text from the response
        if response and response.content:
            return response.content[0].text
        
        return ""

    def analyze_property_data(self, property_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze property data using Claude to generate insights.
        
        Args:
            property_data: List of property dictionaries
            
        Returns:
            Dictionary containing analysis results
        """
        if not property_data:
            return {"error": "No property data provided"}
        
        # Limit data to avoid token limits
        sample_data = property_data[:20]
        data_str = json.dumps(sample_data, indent=2)
        
        prompt = f"""
        Analyze the following property assessment data and provide insights:
        
        {data_str}
        
        Please provide:
        1. High-level summary of the data
        2. Notable patterns or anomalies
        3. Recommendations for tax assessment strategies
        
        Format your response as JSON with the following structure:
        {{
            "summary": "string",
            "patterns": ["string", "string", ...],
            "anomalies": ["string", "string", ...],
            "recommendations": ["string", "string", ...]
        }}
        """
        
        try:
            response = self.generate_text(prompt)
            # Extract JSON from response
            result = json.loads(response)
            logger.info("Successfully analyzed property data")
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response")
            return {
                "summary": "Analysis failed",
                "patterns": [],
                "anomalies": [],
                "recommendations": []
            }
        except Exception as e:
            logger.error(f"Error analyzing property data: {str(e)}")
            return {"error": str(e)}
    
    def generate_levy_insights(self, 
                              tax_code_data: List[Dict[str, Any]], 
                              historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate insights about levy rates and property taxes using Claude.
        
        Args:
            tax_code_data: Current tax code data
            historical_data: Historical tax data for comparison
            
        Returns:
            Dictionary containing insights
        """
        if not tax_code_data:
            return {"error": "No tax code data provided"}
        
        # Convert data to strings for prompt
        current_data_str = json.dumps(tax_code_data[:10], indent=2)
        historical_data_str = json.dumps(historical_data[:10], indent=2)
        
        prompt = f"""
        Generate insights about the following tax levy data.
        
        Current tax code data:
        {current_data_str}
        
        Historical tax data:
        {historical_data_str}
        
        Please provide:
        1. Key trends in levy rates over time
        2. Anomalies or outliers in the data
        3. Recommendations for policymakers
        4. Potential impacts on property owners
        
        Format your response as JSON with the following structure:
        {{
            "trends": ["string", "string", ...],
            "anomalies": ["string", "string", ...],
            "recommendations": ["string", "string", ...],
            "impacts": ["string", "string", ...]
        }}
        """
        
        try:
            response = self.generate_text(prompt)
            # Extract JSON from response
            result = json.loads(response)
            logger.info("Successfully generated levy insights")
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Claude response")
            return {
                "trends": [],
                "anomalies": [],
                "recommendations": [],
                "impacts": []
            }
        except Exception as e:
            logger.error(f"Error generating levy insights: {str(e)}")
            return {"error": str(e)}


# Singleton instance
claude_service = None

def get_claude_service() -> ClaudeService:
    """
    Get or create the Claude service singleton.
    
    Returns:
        ClaudeService instance
    """
    global claude_service
    if claude_service is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment variables")
        try:
            claude_service = ClaudeService(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Claude service: {str(e)}")
            raise
    return claude_service