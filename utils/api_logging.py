"""
API Logging Utilities for External API Integration.

This module provides standardized logging functions for tracking API calls,
responses, and errors across the application. It includes utilities for:
- Logging API requests and responses
- Recording API errors with contextual information
- Handling retry attempts
- Tracking rate limits and quotas
"""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union
from flask import current_app, g

# Configure logger
logger = logging.getLogger(__name__)

class APICallRecord:
    """Class to store and format API call information."""
    
    def __init__(self, 
                 service: str, 
                 endpoint: str, 
                 method: str = "POST",
                 params: Optional[Dict[str, Any]] = None):
        """
        Initialize an API call record.
        
        Args:
            service: The name of the API service (e.g., "anthropic", "openai")
            endpoint: The specific API endpoint being called
            method: HTTP method used (GET, POST, etc.)
            params: Optional parameters sent with the request (sensitive data redacted)
        """
        self.service = service
        self.endpoint = endpoint
        self.method = method
        self.params = self._redact_sensitive_data(params) if params else {}
        self.start_time = time.time()
        self.end_time = None
        self.duration_ms = None
        self.status_code = None
        self.success = False
        self.error_message = None
        self.retry_count = 0
        self.response_summary = None
    
    def complete(self, 
                status_code: Optional[int] = None, 
                success: bool = True,
                response: Optional[Any] = None):
        """
        Mark the API call as complete and record the results.
        
        Args:
            status_code: HTTP status code of the response
            success: Whether the call was successful
            response: Response data (will be summarized/redacted for logging)
        """
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status_code = status_code
        self.success = success
        
        if response:
            self.response_summary = self._summarize_response(response)
    
    def record_error(self, error_message: str):
        """
        Record an error that occurred during the API call.
        
        Args:
            error_message: Description of the error
        """
        self.success = False
        self.error_message = error_message
        
        # If the call hasn't been completed yet, complete it
        if not self.end_time:
            self.complete(success=False)
    
    def record_retry(self):
        """Increment the retry count for this API call."""
        self.retry_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the record to a dictionary for logging/storage.
        
        Returns:
            Dictionary representation of the API call record
        """
        return {
            "service": self.service,
            "endpoint": self.endpoint,
            "method": self.method,
            "params": self.params,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
            "duration_ms": self.duration_ms,
            "status_code": self.status_code,
            "success": self.success,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "response_summary": self.response_summary
        }
    
    def _redact_sensitive_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive data from parameters for logging.
        
        Args:
            params: Original parameters dictionary
            
        Returns:
            Copy of parameters with sensitive data redacted
        """
        if not params:
            return {}
            
        # Create a deep copy to avoid modifying the original
        redacted_params = json.loads(json.dumps(params))
        
        # List of sensitive parameter names to redact
        sensitive_fields = [
            "api_key", "key", "secret", "password", "token", 
            "auth", "authorization", "credential"
        ]
        
        def redact_dict(d):
            for k, v in d.items():
                # Check if key contains any sensitive terms
                if any(field in k.lower() for field in sensitive_fields):
                    if isinstance(v, str):
                        # Show only first few and last few characters
                        if len(v) > 8:
                            d[k] = v[:4] + "..." + v[-4:]
                        else:
                            d[k] = "****"
                    else:
                        d[k] = "****"
                # Recursively check nested dictionaries
                elif isinstance(v, dict):
                    redact_dict(v)
                # Check lists for dictionaries to redact
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            redact_dict(item)
        
        redact_dict(redacted_params)
        return redacted_params
    
    def _summarize_response(self, response: Any) -> Dict[str, Any]:
        """
        Create a summarized version of the response for logging.
        
        Args:
            response: The API response to summarize
            
        Returns:
            Summarized response suitable for logging
        """
        try:
            # If response is a string that looks like JSON, parse it
            if isinstance(response, str):
                try:
                    response_data = json.loads(response)
                except json.JSONDecodeError:
                    # Not JSON, create simple summary
                    return {
                        "type": "string",
                        "length": len(response),
                        "preview": response[:100] + ("..." if len(response) > 100 else "")
                    }
            else:
                response_data = response
                
            # If it's a dictionary or similar
            if hasattr(response_data, "keys"):
                # Create a summary with just the keys and types/lengths
                summary = {}
                for key, value in response_data.items():
                    if isinstance(value, (dict, list)):
                        summary[key] = f"{type(value).__name__} ({len(value)} items)"
                    elif isinstance(value, str) and len(value) > 100:
                        summary[key] = f"string ({len(value)} chars)"
                    else:
                        summary[key] = str(value)[:100]
                return summary
            
            # For list responses, summarize the length and first few items
            elif isinstance(response_data, list):
                return {
                    "type": "list",
                    "length": len(response_data),
                    "preview": str(response_data[:3])[:100] + ("..." if len(response_data) > 3 else "")
                }
                
            # For other types, convert to string and truncate
            return {
                "type": type(response_data).__name__,
                "preview": str(response_data)[:100] + ("..." if len(str(response_data)) > 100 else "")
            }
                
        except Exception as e:
            # If anything goes wrong during summarization, provide a fallback
            return {
                "type": type(response).__name__,
                "error": f"Could not summarize response: {str(e)}"
            }


def log_api_call(service: str, endpoint: str, level: str = "info") -> Callable:
    """
    Decorator to log API calls with standardized formatting.
    
    Args:
        service: Name of the API service
        endpoint: Specific endpoint being called
        level: Logging level to use for successful calls
        
    Returns:
        Decorated function that logs API calls
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create API call record
            record = APICallRecord(service, endpoint)
            
            try:
                # Execute the API call
                result = func(*args, **kwargs)
                
                # Record successful completion
                if hasattr(result, "status_code"):
                    record.complete(status_code=result.status_code, success=True, response=result)
                else:
                    record.complete(success=True, response=result)
                
                # Log successful API call
                log_method = getattr(logger, level.lower())
                log_method(f"API Call: {service} {endpoint} - Success - {record.duration_ms}ms")
                
                # Log detailed information at debug level
                logger.debug(f"API Call Details: {json.dumps(record.to_dict())}")
                
                return result
                
            except Exception as e:
                # Record the error
                record.record_error(str(e))
                
                # Log the error with details
                logger.error(
                    f"API Call: {service} {endpoint} - Failed - {record.duration_ms}ms - Error: {str(e)}"
                )
                logger.debug(f"API Call Error Details: {json.dumps(record.to_dict())}")
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator


def save_api_call_to_database(call_record: APICallRecord, user_id: Optional[int] = None):
    """
    Save an API call record to the database for historical tracking.
    
    Args:
        call_record: The API call record to save
        user_id: Optional user ID associated with the call
    """
    from models import APICallLog, db
    
    try:
        # Create database record
        db_record = APICallLog(
            service=call_record.service,
            endpoint=call_record.endpoint,
            method=call_record.method,
            timestamp=datetime.fromtimestamp(call_record.start_time),
            duration_ms=call_record.duration_ms,
            status_code=call_record.status_code,
            success=call_record.success,
            error_message=call_record.error_message,
            retry_count=call_record.retry_count,
            params=call_record.params,
            response_summary=call_record.response_summary,
            user_id=user_id
        )
        
        # Save to database
        with current_app.app_context():
            db.session.add(db_record)
            db.session.commit()
            logger.debug(f"Saved API call {call_record.service}.{call_record.endpoint} to database (ID: {db_record.id})")
    except Exception as e:
        # Log error but don't propagate exception to avoid disrupting application flow
        logger.error(f"Failed to save API call to database: {str(e)}")


class APICallTracker:
    """
    Class to track API calls and record statistics.
    
    This class provides methods to track API usage, record statistics,
    and analyze patterns across multiple API calls.
    """
    
    def __init__(self):
        """Initialize the API call tracker."""
        self.calls: List[Dict[str, Any]] = []
        self.error_count = 0
        self.success_count = 0
        self.total_duration_ms = 0
        self.persist_to_database = True
    
    def record_call(self, call_record: APICallRecord):
        """
        Record an API call in the tracker.
        
        Args:
            call_record: The API call record to track
        """
        call_dict = call_record.to_dict()
        self.calls.append(call_dict)
        
        if call_record.success:
            self.success_count += 1
        else:
            self.error_count += 1
            
        if call_record.duration_ms:
            self.total_duration_ms += call_record.duration_ms
            
        # Save to database if enabled (for historical tracking)
        if self.persist_to_database:
            # Get current user ID if available
            user_id = getattr(g, 'user_id', None) if hasattr(g, 'user_id') else None
            
            # Save asynchronously to avoid impacting API performance
            try:
                save_api_call_to_database(call_record, user_id)
            except Exception as e:
                logger.error(f"Error saving API call to database: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tracked API calls.
        
        Returns:
            Dictionary with statistics about the tracked calls
        """
        total_calls = len(self.calls)
        
        # Avoid division by zero
        error_rate = (self.error_count / total_calls) * 100 if total_calls > 0 else 0
        avg_duration = self.total_duration_ms / total_calls if total_calls > 0 else 0
        
        # Count calls by service
        service_counts = {}
        for call in self.calls:
            service = call["service"]
            service_counts[service] = service_counts.get(service, 0) + 1
        
        return {
            "total_calls": total_calls,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "error_rate_percent": round(error_rate, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "calls_by_service": service_counts
        }
    
    def clear(self):
        """Clear all tracked calls and reset statistics."""
        self.calls = []
        self.error_count = 0
        self.success_count = 0
        self.total_duration_ms = 0


# Singleton instance of the API call tracker
api_tracker = APICallTracker()


def get_api_statistics() -> Dict[str, Any]:
    """
    Get current API call statistics.
    
    Returns:
        Dictionary with API call statistics
    """
    return api_tracker.get_statistics()


def track_anthropic_api_call(func: Callable) -> Callable:
    """
    Decorator specifically for tracking Anthropic API calls.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function with Anthropic API call tracking
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create API call record specific to Anthropic
        endpoint = func.__name__
        record = APICallRecord("anthropic", endpoint)
        
        try:
            # Execute the API call
            result = func(*args, **kwargs)
            
            # Record successful completion
            record.complete(success=True, response=result)
            
            # Log the API call
            logger.info(f"Anthropic API: {endpoint} - Success - {record.duration_ms}ms")
            
            # Track the call
            api_tracker.record_call(record)
            
            return result
            
        except Exception as e:
            # Record the error
            record.record_error(str(e))
            
            # Log the error
            logger.error(f"Anthropic API: {endpoint} - Failed - Error: {str(e)}")
            
            # Track the call
            api_tracker.record_call(record)
            
            # Re-raise the exception
            raise
            
    return wrapper