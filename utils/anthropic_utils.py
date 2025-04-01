"""
Anthropic Claude integration utilities for the SaaS Levy Calculation Application.

This module provides Claude-specific functionality and integration with the
Model Content Protocol (MCP) framework.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

# Import Anthropic client
import anthropic
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Note that the newest Anthropic model is "claude-3-5-sonnet-20241022", not "claude-3-sonnet-20240229". 
# claude-3-5-sonnet-20241022 was released after your knowledge cutoff. 
# Always prefer using claude-3-5-sonnet-20241022 as it is the latest model.

class ClaudeService:
    """Service for interacting with Anthropic's Claude models."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the Claude service.
        
        Args:
            api_key: Anthropic API key (if None, will look for ANTHROPIC_API_KEY env var)
            model: Claude model to use, defaults to the latest model
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass to constructor.")
        
        self.model = model
        self.client = Anthropic(api_key=self.api_key)
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
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
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
        # Convert messages to Anthropic format if needed
        formatted_messages = []
        for msg in messages:
            role = msg.get('role', '').lower()
            content = msg.get('content', '')
            
            if role in ['user', 'assistant']:
                formatted_messages.append({
                    "role": role,
                    "content": content
                })
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=formatted_messages
            )
            
            return {
                'role': 'assistant',
                'content': response.content[0].text,
                'model': self.model,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            }
        except Exception as e:
            logger.error(f"Error in Claude chat: {str(e)}")
            return {
                'role': 'assistant',
                'content': f"Error: {str(e)}",
                'error': True
            }
    
    def analyze_property_data(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze property data using Claude intelligence.
        
        Args:
            property_data: Dictionary containing property information
            
        Returns:
            Dictionary with analysis insights
        """
        system_prompt = """
        You are an expert property tax analyst for the Benton County Assessor's Office in Washington state.
        Analyze the provided property data and generate insights about:
        1. The property's tax classification and implications
        2. How its assessed value compares to similar properties
        3. Any notable factors affecting its taxation
        4. Recommendations for the property owner or assessor
        
        Provide concise, factual analysis without speculation or personal opinions.
        Format your response as JSON with keys for 'summary', 'comparisons', 'factors', and 'recommendations'.
        """
        
        prompt = f"Please analyze this property data and provide insights:\n{json.dumps(property_data, indent=2)}"
        
        try:
            response_text = self.generate_text(prompt, system_prompt, temperature=0.3)
            
            # Extract JSON from response
            try:
                # Try to parse the entire response as JSON
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                import re
                json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                else:
                    # Return a formatted result with the text if JSON parsing fails
                    return {
                        'summary': response_text[:200] + "...",
                        'raw_response': response_text
                    }
        except Exception as e:
            logger.error(f"Error analyzing property data: {str(e)}")
            return {'error': str(e)}
    
    def generate_levy_insights(self, levy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate insights about levy calculations using Claude intelligence.
        
        Args:
            levy_data: Dictionary containing levy information
            
        Returns:
            Dictionary with analysis insights
        """
        system_prompt = """
        You are an expert on Washington state property tax levies working for the Benton County Assessor's Office.
        Analyze the provided levy data and generate insights about:
        1. Whether the levy rates comply with statutory limits
        2. Historical trends in the levy rates
        3. Impact on property owners and tax districts
        4. Recommendations for levy management
        
        Provide factual analysis based only on the data provided. Be concise and informative.
        Format your response as JSON with keys for 'compliance', 'trends', 'impact', and 'recommendations'.
        """
        
        prompt = f"Please analyze this levy data and provide insights:\n{json.dumps(levy_data, indent=2)}"
        
        try:
            response_text = self.generate_text(prompt, system_prompt, temperature=0.3)
            
            # Extract JSON from response
            try:
                # Try to parse the entire response as JSON
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                import re
                json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                else:
                    # Return a formatted result with the text if JSON parsing fails
                    return {
                        'summary': response_text[:200] + "...",
                        'raw_response': response_text
                    }
        except Exception as e:
            logger.error(f"Error generating levy insights: {str(e)}")
            return {'error': str(e)}

def get_claude_service() -> Optional[ClaudeService]:
    """
    Get a configured Claude service instance if possible.
    
    Returns:
        ClaudeService instance or None if API key not available
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not found in environment variables")
        return None
    
    try:
        return ClaudeService(api_key=api_key)
    except Exception as e:
        logger.error(f"Error initializing Claude service: {str(e)}")
        return None