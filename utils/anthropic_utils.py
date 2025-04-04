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

from utils.html_sanitizer import sanitize_mcp_insights, sanitize_html

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
             temperature: float = 0.7,
             max_retries: int = 3,
             retry_delay: float = 1.0) -> Dict[str, Any]:
        """
        Send a chat request to the Claude API with automatic retries.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: System instructions for Claude
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            max_retries: Maximum number of retry attempts on temporary errors
            retry_delay: Delay between retries in seconds (exponential backoff applied)
            
        Returns:
            The response from Claude API
        """
        attempt = 0
        last_error = None
        
        while attempt < max_retries + 1:  # +1 for the initial attempt
            try:
                logger.info(f"Sending chat request with {len(messages)} messages (attempt {attempt + 1}/{max_retries + 1})")
                
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
                last_error = e
                error_str = str(e)
                
                # Check if the error is related to credit balance
                if "credit balance is too low" in error_str or "quota exceeded" in error_str:
                    logger.error(f"Credit balance error (non-retriable): {error_str}")
                    break  # Don't retry credit balance errors
                
                # Check if it's a temporary error that might resolve with a retry
                retriable_errors = [
                    "timeout", 
                    "connection error",
                    "server error",
                    "500",
                    "503",
                    "429",  # Rate limit error
                    "too many requests"
                ]
                
                is_retriable = any(err_type.lower() in error_str.lower() for err_type in retriable_errors)
                
                if not is_retriable:
                    logger.error(f"Non-retriable error in chat request: {error_str}")
                    break  # Don't retry permanent errors
                
                # Only log and retry if this isn't the last attempt
                if attempt < max_retries:
                    delay = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Temporary error in chat request: {error_str}. Retrying in {delay:.2f}s...")
                    
                    # Sleep before retry with exponential backoff
                    import time
                    time.sleep(delay)
                else:
                    logger.error(f"Failed chat request after {max_retries + 1} attempts: {error_str}")
            
            attempt += 1
        
        # If we get here, all retries failed or a non-retriable error occurred
        if last_error:
            logger.error(f"All retries failed: {str(last_error)}")
            raise last_error
    
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
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.chat(messages, max_tokens=max_tokens, temperature=temperature)
            
            # Extract the text from the response
            if response and response.content:
                return response.content[0].text
            
            return ""
        except Exception as e:
            error_msg = str(e)
            # Check for credit/quota errors specifically
            if "credit balance is too low" in error_msg or "quota exceeded" in error_msg:
                logger.error(f"Anthropic API credit issue: {error_msg}")
                return json.dumps({
                    "error": "API_CREDIT_ISSUE",
                    "message": "The Anthropic API could not be accessed due to credit limitations. Please update your API key or add credits to your account."
                })
            # Other API errors
            elif "api" in error_msg.lower() or "key" in error_msg.lower():
                logger.error(f"Anthropic API error: {error_msg}")
                return json.dumps({
                    "error": "API_ERROR",
                    "message": "There was an error connecting to the Anthropic API. Please check your API key configuration."
                })
            # Generic errors
            else:
                logger.error(f"Error generating text: {error_msg}")
                return json.dumps({
                    "error": "GENERATION_ERROR",
                    "message": "An error occurred while generating text with Claude."
                })

    def analyze_property_data(self, property_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze property data using Claude to generate insights.
        
        Args:
            property_data: List of property dictionaries
            
        Returns:
            Dictionary containing analysis results with sanitized content
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
            # Sanitize the result to prevent XSS
            sanitized_result = sanitize_mcp_insights(result)
            return sanitized_result
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
            return {"error": sanitize_html(str(e))}
    
    def generate_levy_insights(self, 
                              tax_code_data: List[Dict[str, Any]], 
                              historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate insights about levy rates and property taxes using Claude.
        
        Args:
            tax_code_data: Current tax code data
            historical_data: Historical tax data for comparison
            
        Returns:
            Dictionary containing sanitized insights
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
            # Sanitize the result to prevent XSS
            sanitized_result = sanitize_mcp_insights(result)
            return sanitized_result
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
            return {"error": sanitize_html(str(e))}


# Singleton instance
claude_service = None

def check_api_key_status(max_retries: int = 2, retry_delay: float = 0.5) -> Dict[str, str]:
    """
    Check the status of the Anthropic API key with retry capability.
    
    Args:
        max_retries: Maximum number of retry attempts for temporary errors
        retry_delay: Initial delay between retries in seconds (exponential backoff applied)
    
    Returns:
        Dictionary with status information:
        {
            'status': 'missing'|'invalid'|'valid'|'no_credits',
            'message': 'Description of the status'
        }
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        return {
            'status': 'missing',
            'message': 'API key not found in environment variables'
        }
    
    # Check if the API key has the expected format (basic validation)
    if not api_key.startswith('sk-ant-'):
        return {
            'status': 'invalid',
            'message': 'API key has an invalid format'
        }
    
    # Try to initialize the client to further validate
    try:
        client = Anthropic(api_key=api_key)
        
        # Simple test to check if the key works and has credits
        attempt = 0
        last_error = None
        
        while attempt < max_retries + 1:  # +1 for the initial attempt
            try:
                logger.info(f"Testing API key status (attempt {attempt + 1}/{max_retries + 1})")
                
                # Make a minimal API request to check credits
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "Test"}]
                )
                
                return {
                    'status': 'valid',
                    'message': 'API key is valid and has credits'
                }
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if the error is related to credit balance
                if "credit balance is too low" in error_str or "quota exceeded" in error_str:
                    logger.warning(f"Anthropic API credit issue: Error code: {getattr(e, 'status_code', 'unknown')} - {error_str}")
                    return {
                        'status': 'no_credits',
                        'message': 'API key is valid but has insufficient credits'
                    }
                
                # Check if it's a temporary error that might resolve with a retry
                retriable_errors = [
                    "timeout", 
                    "connection error",
                    "server error",
                    "500",
                    "503",
                    "429",  # Rate limit error
                    "too many requests"
                ]
                
                is_retriable = any(err_type.lower() in error_str.lower() for err_type in retriable_errors)
                
                if not is_retriable:
                    logger.error(f"Non-retriable API error: {error_str}")
                    return {
                        'status': 'invalid',
                        'message': f'API error: {error_str}'
                    }
                
                # Only log and retry if this isn't the last attempt
                if attempt < max_retries:
                    delay = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Temporary API error: {error_str}. Retrying in {delay:.2f}s...")
                    
                    # Sleep before retry with exponential backoff
                    import time
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to validate API key after {max_retries + 1} attempts")
                    return {
                        'status': 'invalid',
                        'message': f'Failed to validate API key after multiple attempts: {error_str}'
                    }
            
            attempt += 1
        
        # This should not be reached given the return statements in the loop above
        return {
            'status': 'invalid',
            'message': 'Unknown error validating API key'
        }
        
    except Exception as e:
        return {
            'status': 'invalid',
            'message': f'API key validation error: {str(e)}'
        }

def get_claude_service() -> Optional[ClaudeService]:
    """
    Get or create the Claude service singleton.
    
    Returns:
        ClaudeService instance or None if initialization fails
    """
    global claude_service
    
    # Check API key status first
    key_status = check_api_key_status()
    if key_status['status'] == 'no_credits':
        logger.warning(f"Claude service unavailable: API key is valid but has insufficient credits")
        return None
    elif key_status['status'] != 'valid':
        logger.warning(f"Claude service unavailable: {key_status['message']}")
        return None
    
    # Initialize the service if needed
    if claude_service is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        try:
            claude_service = ClaudeService(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Claude service: {str(e)}")
            return None
    
    return claude_service