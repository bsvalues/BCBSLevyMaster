"""
Tests for Anthropic API integration.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from utils.anthropic_utils import ClaudeService, get_claude_service


class TestClaudeService:
    """Test the ClaudeService class."""
    
    @patch('utils.anthropic_utils.Anthropic')
    def test_init(self, mock_anthropic):
        """Test initialization of the Claude service."""
        # Test with explicit API key
        service = ClaudeService(api_key="test-key")
        mock_anthropic.assert_called_once_with(api_key="test-key")
        
        # Reset mock
        mock_anthropic.reset_mock()
        
        # Test with environment variable
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            service = ClaudeService()
            mock_anthropic.assert_called_once_with(api_key="env-key")
    
    @patch('utils.anthropic_utils.Anthropic')
    def test_generate_text(self, mock_anthropic):
        """Test text generation with Claude."""
        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [{"text": "Generated text"}]
        mock_client.messages.create.return_value = mock_response
        
        # Assign the mock client to the mock Anthropic instance
        mock_anthropic.return_value = mock_client
        
        # Create service and generate text
        service = ClaudeService(api_key="test-key")
        result = service.generate_text(
            prompt="Test prompt",
            system_prompt="System instructions",
            temperature=0.5,
            max_tokens=500
        )
        
        # Verify client was called correctly
        mock_client.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            temperature=0.5,
            system="System instructions",
            messages=[{"role": "user", "content": "Test prompt"}]
        )
        
        # Verify result
        assert result == "Generated text"
    
    @patch('utils.anthropic_utils.Anthropic')
    def test_chat(self, mock_anthropic):
        """Test chat interaction with Claude."""
        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [{"text": "Chat response"}]
        mock_client.messages.create.return_value = mock_response
        
        # Assign the mock client to the mock Anthropic instance
        mock_anthropic.return_value = mock_client
        
        # Create service and chat messages
        service = ClaudeService(api_key="test-key")
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]
        
        result = service.chat(
            messages=messages,
            system_prompt="Chat system instructions",
            temperature=0.7,
            max_tokens=1000
        )
        
        # Verify client was called correctly
        mock_client.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.7,
            system="Chat system instructions",
            messages=messages
        )
        
        # Verify result
        assert "text" in result
        assert result["text"] == "Chat response"
    
    @patch('utils.anthropic_utils.Anthropic')
    def test_analyze_property_data(self, mock_anthropic):
        """Test property data analysis with Claude."""
        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [{"text": '{"insights": "Property analysis", "recommendations": ["Recommendation 1"]}'}]
        mock_client.messages.create.return_value = mock_response
        
        # Assign the mock client to the mock Anthropic instance
        mock_anthropic.return_value = mock_client
        
        # Create service and analyze property data
        service = ClaudeService(api_key="test-key")
        property_data = {
            "property_id": "12345-6789",
            "assessed_value": 250000,
            "tax_code": "00120",
            "levy_rate": 2.5
        }
        
        result = service.analyze_property_data(property_data)
        
        # Verify client was called with appropriate prompt
        args, kwargs = mock_client.messages.create.call_args
        assert "property_id" in str(kwargs["messages"])
        assert "assessed_value" in str(kwargs["messages"])
        assert "tax_code" in str(kwargs["messages"])
        assert "levy_rate" in str(kwargs["messages"])
        
        # Verify result structure
        assert "insights" in result
        assert "recommendations" in result
        assert result["insights"] == "Property analysis"
        assert result["recommendations"] == ["Recommendation 1"]
    
    @patch('utils.anthropic_utils.Anthropic')
    def test_generate_levy_insights(self, mock_anthropic):
        """Test levy insights generation with Claude."""
        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [{"text": '{"analysis": "Levy analysis", "highlights": ["Highlight 1"], "recommendations": ["Recommendation 1"]}'}]
        mock_client.messages.create.return_value = mock_response
        
        # Assign the mock client to the mock Anthropic instance
        mock_anthropic.return_value = mock_client
        
        # Create service and generate levy insights
        service = ClaudeService(api_key="test-key")
        levy_data = {
            "tax_codes": [
                {"code": "00120", "levy_rate": 2.5, "levy_amount": 1000000},
                {"code": "00130", "levy_rate": 3.1, "levy_amount": 500000}
            ],
            "total_assessed_value": 500000000
        }
        
        result = service.generate_levy_insights(levy_data)
        
        # Verify client was called with appropriate prompt
        args, kwargs = mock_client.messages.create.call_args
        assert "tax_codes" in str(kwargs["messages"])
        assert "levy_rate" in str(kwargs["messages"])
        assert "levy_amount" in str(kwargs["messages"])
        
        # Verify result structure
        assert "analysis" in result
        assert "highlights" in result
        assert "recommendations" in result
        assert result["analysis"] == "Levy analysis"
        assert result["highlights"] == ["Highlight 1"]
        assert result["recommendations"] == ["Recommendation 1"]


def test_get_claude_service():
    """Test getting a Claude service instance."""
    # Test with no API key
    with patch.dict(os.environ, {}, clear=True):
        service = get_claude_service()
        assert service is None
    
    # Test with API key
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch('utils.anthropic_utils.ClaudeService') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            
            service = get_claude_service()
            
            assert service is mock_instance
            mock_service.assert_called_once_with(api_key="test-key")