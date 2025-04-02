"""
HTML sanitizer utilities for AI-generated content.

This module provides functions to sanitize HTML content
from AI models to prevent XSS vulnerabilities.
"""

import re
import html
from typing import Optional, Dict, Any, Union, List

def sanitize_html(content: str) -> str:
    """
    Sanitize HTML content to prevent XSS vulnerabilities.
    
    Args:
        content: The content to sanitize
        
    Returns:
        Sanitized content with HTML entities escaped
    """
    if not content:
        return ""
    
    # Escape HTML entities
    return html.escape(content)

def sanitize_ai_response(response: Union[Dict[str, Any], List, str, None]) -> Union[Dict[str, Any], List, str, None]:
    """
    Recursively sanitize AI-generated content.
    
    Handles nested dictionaries, lists, and strings.
    
    Args:
        response: The AI response to sanitize
        
    Returns:
        Sanitized response
    """
    if isinstance(response, dict):
        return {key: sanitize_ai_response(value) for key, value in response.items()}
    elif isinstance(response, list):
        return [sanitize_ai_response(item) for item in response]
    elif isinstance(response, str):
        return sanitize_html(response)
    else:
        return response

def sanitize_mcp_insights(insights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize MCP insights to prevent XSS vulnerabilities.
    
    This function sanitizes all string values in the insights dictionary.
    
    Args:
        insights: The insights dictionary to sanitize
        
    Returns:
        Sanitized insights dictionary
    """
    if not insights:
        return {}
    
    # If insights contains a 'narrative' key, make sure to sanitize it
    if 'narrative' in insights and isinstance(insights['narrative'], str):
        insights['narrative'] = sanitize_html(insights['narrative'])
    
    # Sanitize the entire response recursively
    result = sanitize_ai_response(insights)
    
    # Ensure we always return a dictionary
    if isinstance(result, dict):
        return result
    elif isinstance(result, str):
        return {"narrative": result}
    elif isinstance(result, list):
        return {"items": result}
    else:
        return {}

def sanitize_plain_text(content: str) -> str:
    """
    Sanitize plain text content, converting newlines to <br> tags.
    
    This function is useful for preserving line breaks while 
    still sanitizing content.
    
    Args:
        content: The plain text content to sanitize
        
    Returns:
        Sanitized content with newlines converted to <br> tags
    """
    if not content:
        return ""
    
    # First escape HTML entities
    escaped = html.escape(content)
    
    # Then convert newlines to <br> tags
    return escaped.replace('\n', '<br>')