"""
Model Content Protocol (MCP) LLM Integration

This module provides integration with Large Language Models (LLMs) following 
the MCP standards, enabling advanced AI capabilities within the application.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from utils.mcp_core import (
    ContentBlock,
    ContentType,
    MCPMessage,
    mcp_function_registry
)
from utils.mcp_agents import Agent, AgentPhase

# Define LLM provider types
class LLMProvider(Enum):
    OPENAI = "openai"  # OpenAI API (GPT models)
    ANTHROPIC = "anthropic"  # Anthropic API (Claude models)
    PERPLEXITY = "perplexity"  # Perplexity AI API
    GEMINI = "gemini"  # Google Gemini API
    OLLAMA = "ollama"  # Local Ollama integration
    MOCK = "mock"  # Mock provider for testing without API dependency

class LLMServiceError(Exception):
    """Exception raised when LLM service encounters an error."""
    pass

class MCPLLMService:
    """
    Base LLM service class following MCP content standards.
    This class should be extended for specific LLM providers.
    """
    
    def __init__(self, provider: LLMProvider, model_name: str, api_key: Optional[str] = None):
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key or os.environ.get(f"{provider.value.upper()}_API_KEY")
        
        if not self.api_key and provider != LLMProvider.MOCK and provider != LLMProvider.OLLAMA:
            logging.warning(f"No API key provided for {provider.value}. Only mock operations will be available.")
            
    def generate_content(self, content_blocks: list, options: dict = None):
        """
        Default implementation for generate_content. Returns a mock MCPMessage with the input blocks.
        Override in subclasses for real LLM integration.
        """
        from .mcp_message import MCPMessage
        return MCPMessage(content_blocks=content_blocks)

    def generate_text(self, prompt: str, options: dict = None) -> str:
        """
        Default implementation for generate_text. Returns a mock response.
        Override in subclasses for real LLM integration.
        """
        return f"[MOCK LLM RESPONSE] {prompt[:100]}..."

    def invoke_function(self, function_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Invoke a registered function through LLM reasoning.
        
        Args:
            function_name: The name of the function to invoke
            parameters: The parameters to pass to the function
            
        Returns:
            The function result
        """
        # Get the function from the registry
        try:
            function = mcp_function_registry.get_function(function_name)
            return function(**parameters)
        except Exception as e:
            raise LLMServiceError(f"Error invoking function {function_name}: {str(e)}")
            
    def get_function_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the function definitions for use with the LLM.
        
        Returns:
            A dictionary of function definitions
        """
        return mcp_function_registry.get_function_catalog()
        
    def convert_blocks_to_prompt(self, content_blocks: List[ContentBlock]) -> str:
        """
        Convert MCP content blocks to a text prompt for non-MCP-aware LLMs.
        
        Args:
            content_blocks: The content blocks to convert
            
        Returns:
            A text prompt
        """
        prompt_parts = []
        
        for block in content_blocks:
            if block.content_type == ContentType.TEXT:
                prompt_parts.append(block.content)
                
            elif block.content_type == ContentType.STRUCTURED_DATA:
                prompt_parts.append(f"Data: {json.dumps(block.content, indent=2)}")
                
            elif block.content_type == ContentType.FUNCTION_CALL:
                function_name = block.content["function"]
                parameters = block.content["parameters"]
                prompt_parts.append(f"Function Call: {function_name}\nParameters: {json.dumps(parameters, indent=2)}")
                
            elif block.content_type == ContentType.FUNCTION_RESPONSE:
                function_name = block.content["function"]
                result = block.content["result"]
                prompt_parts.append(f"Function Response: {function_name}\nResult: {json.dumps(result, indent=2)}")
                
        return "\n\n".join(prompt_parts)
        
    def parse_text_to_content_blocks(self, text: str) -> List[ContentBlock]:
        """
        Parse text response from non-MCP-aware LLM into content blocks.
        This is a best-effort approach for backward compatibility.
        
        Args:
            text: The text response to parse
            
        Returns:
            A list of content blocks
        """
        # For simple responses, just return a text block
        blocks = [ContentBlock(content_type=ContentType.TEXT, content=text)]
        
        # Try to extract structured data or function calls if present
        # This is a simplified approach and might not work for all responses
        try:
            # Check for JSON blocks
            import re
            json_blocks = re.findall(r'```json\n(.*?)\n```', text, re.DOTALL)
            
            for json_str in json_blocks:
                try:
                    data = json.loads(json_str)
                    blocks.append(ContentBlock(
                        content_type=ContentType.STRUCTURED_DATA,
                        content=data
                    ))
                except:
                    pass
                    
            # Check for function call patterns
            function_blocks = re.findall(r'Function Call: (.*?)\nParameters: (.*?)(?:\n\n|$)', text, re.DOTALL)
            
            for function_name, params_str in function_blocks:
                try:
                    parameters = json.loads(params_str)
                    blocks.append(ContentBlock(
                        content_type=ContentType.FUNCTION_CALL,
                        content={
                            "function": function_name.strip(),
                            "parameters": parameters
                        }
                    ))
                except:
                    pass
                    
        except Exception as e:
            logging.warning(f"Error parsing text to content blocks: {str(e)}")
            
        return blocks

class OpenAIService(MCPLLMService):
    """OpenAI LLM service implementation following MCP standards."""
    
    def __init__(self, model_name: str = "gpt-4", api_key: Optional[str] = None):
        super().__init__(LLMProvider.OPENAI, model_name, api_key)
        
        # Import OpenAI SDK
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            logging.error("OpenAI SDK not installed. Please install with 'pip install openai'")
            self.client = None
            
    def generate_text(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generate text using OpenAI API."""
        if not self.client:
            raise LLMServiceError("OpenAI SDK not available")
            
        if not self.api_key:
            raise LLMServiceError("OpenAI API key not provided")
            
        options = options or {}
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=options.get("max_tokens", 1024),
                temperature=options.get("temperature", 0.7)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise LLMServiceError(f"OpenAI API error: {str(e)}")
            
    def generate_content(self, content_blocks: List[ContentBlock], options: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Generate content using OpenAI API following MCP standards."""
        if not self.client:
            raise LLMServiceError("OpenAI SDK not available")
            
        if not self.api_key:
            raise LLMServiceError("OpenAI API key not provided")
            
        options = options or {}
        
        try:
            # Convert content blocks to OpenAI messages format
            messages = []
            
            for block in content_blocks:
                if block.content_type == ContentType.TEXT:
                    messages.append({
                        "role": block.metadata.get("role", "user"),
                        "content": block.content
                    })
                elif block.content_type == ContentType.STRUCTURED_DATA:
                    messages.append({
                        "role": block.metadata.get("role", "user"),
                        "content": json.dumps(block.content)
                    })
                elif block.content_type == ContentType.FUNCTION_CALL:
                    # For older OpenAI API versions that don't support function_call format
                    messages.append({
                        "role": "user",
                        "content": f"Please call function: {block.content['function']} with parameters: {json.dumps(block.content['parameters'])}"
                    })
                    
            # Check if we need to include functions
            functions = None
            function_call = None
            
            if options.get("enable_functions", True):
                function_defs = self.get_function_definitions()
                if function_defs:
                    functions = []
                    for name, metadata in function_defs.items():
                        functions.append({
                            "name": name,
                            "description": metadata.get("description", ""),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    param_name: {
                                        "type": param_info.get("type", "string"),
                                        "description": param_info.get("description", "")
                                    }
                                    for param_name, param_info in metadata.get("parameters", {}).items()
                                },
                                "required": list(metadata.get("parameters", {}).keys())
                            }
                        })
                    
                    if options.get("auto_function_call", False):
                        function_call = "auto"
                    elif options.get("function_name"):
                        function_call = {"name": options["function_name"]}
                    
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                functions=functions,
                function_call=function_call,
                max_tokens=options.get("max_tokens", 1024),
                temperature=options.get("temperature", 0.7)
            )
            
            # Process the response
            assistant_message = response.choices[0].message
            result_blocks = []
            
            # Check for text response
            if assistant_message.content:
                result_blocks.append(ContentBlock(
                    content_type=ContentType.TEXT,
                    content=assistant_message.content,
                    metadata={"role": "assistant"}
                ))
                
            # Check for function call
            if hasattr(assistant_message, 'function_call') and assistant_message.function_call:
                function_name = assistant_message.function_call.name
                arguments = json.loads(assistant_message.function_call.arguments)
                
                result_blocks.append(ContentBlock(
                    content_type=ContentType.FUNCTION_CALL,
                    content={
                        "function": function_name,
                        "parameters": arguments
                    },
                    metadata={"role": "assistant"}
                ))
                
                # If auto execution is enabled, also invoke the function
                if options.get("auto_execute_functions", False):
                    try:
                        result = self.invoke_function(function_name, arguments)
                        
                        result_blocks.append(ContentBlock(
                            content_type=ContentType.FUNCTION_RESPONSE,
                            content={
                                "function": function_name,
                                "result": result
                            },
                            metadata={"auto_executed": True}
                        ))
                    except Exception as e:
                        logging.error(f"Error auto-executing function {function_name}: {str(e)}")
                        
            return MCPMessage(content_blocks=result_blocks)
            
        except Exception as e:
            raise LLMServiceError(f"OpenAI API error: {str(e)}")

class AnthropicService(MCPLLMService):
    """Anthropic LLM service implementation following MCP standards."""
    
    def __init__(self, model_name: str = "claude-2", api_key: Optional[str] = None):
        super().__init__(LLMProvider.ANTHROPIC, model_name, api_key)
        
        # Import Anthropic SDK if available
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            logging.error("Anthropic SDK not installed. Please install with 'pip install anthropic'")
            self.client = None
            
    def generate_text(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generate text using Anthropic API."""
        if not self.client:
            raise LLMServiceError("Anthropic SDK not available")
            
        if not self.api_key:
            raise LLMServiceError("Anthropic API key not provided")
            
        options = options or {}
        
        try:
            response = self.client.completions.create(
                model=self.model_name,
                prompt=f"{anthropic.HUMAN_PROMPT} {prompt}{anthropic.AI_PROMPT}",
                max_tokens_to_sample=options.get("max_tokens", 1024),
                temperature=options.get("temperature", 0.7)
            )
            
            return response.completion
            
        except Exception as e:
            raise LLMServiceError(f"Anthropic API error: {str(e)}")
            
    def generate_content(self, content_blocks: List[ContentBlock], options: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Generate content using Anthropic API following MCP standards."""
        if not self.client:
            raise LLMServiceError("Anthropic SDK not available")
            
        if not self.api_key:
            raise LLMServiceError("Anthropic API key not provided")
            
        options = options or {}
        
        # Since Anthropic doesn't natively support MCP, convert blocks to prompt text
        prompt = self.convert_blocks_to_prompt(content_blocks)
        
        # Add function definitions if enabled
        if options.get("enable_functions", True):
            function_defs = self.get_function_definitions()
            if function_defs:
                prompt += "\n\nAvailable functions:\n"
                for name, metadata in function_defs.items():
                    prompt += f"- {name}: {metadata.get('description', '')}\n"
                    prompt += f"  Parameters: {json.dumps(metadata.get('parameters', {}), indent=2)}\n\n"
                    
                prompt += "\nYou can call these functions using the format:\n"
                prompt += "Function Call: function_name\n"
                prompt += "Parameters: {\n  \"param1\": \"value1\",\n  \"param2\": \"value2\"\n}\n\n"
                
        try:
            # Generate response
            response_text = self.generate_text(prompt, options)
            
            # Parse the response into content blocks
            result_blocks = self.parse_text_to_content_blocks(response_text)
            
            # Auto-execute functions if enabled
            if options.get("auto_execute_functions", False):
                for block in list(result_blocks):  # Create a copy to avoid modification during iteration
                    if block.content_type == ContentType.FUNCTION_CALL:
                        function_name = block.content["function"]
                        parameters = block.content["parameters"]
                        
                        try:
                            result = self.invoke_function(function_name, parameters)
                            
                            result_blocks.append(ContentBlock(
                                content_type=ContentType.FUNCTION_RESPONSE,
                                content={
                                    "function": function_name,
                                    "result": result
                                },
                                metadata={"auto_executed": True}
                            ))
                        except Exception as e:
                            logging.error(f"Error auto-executing function {function_name}: {str(e)}")
                            
            return MCPMessage(content_blocks=result_blocks)
            
        except Exception as e:
            raise LLMServiceError(f"Anthropic API error: {str(e)}")

class PerplexityService(MCPLLMService):
    """
    Perplexity AI LLM service implementation following MCP standards.
    """
    def __init__(self, model_name: str = "pplx-70b-online", api_key: Optional[str] = None):
        super().__init__(LLMProvider.PERPLEXITY, model_name, api_key)
        self.endpoint = os.environ.get("PERPLEXITY_API_URL", "https://api.perplexity.ai/v1/completions")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def generate_text(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        import requests
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": options.get("max_tokens", 1024) if options else 1024,
            "temperature": options.get("temperature", 0.7) if options else 0.7
        }
        resp = requests.post(self.endpoint, headers=self.headers, json=payload)
        if resp.status_code == 200:
            result = resp.json()
            # This assumes Perplexity returns {"choices": [{"text": ...}]}
            return result.get("choices", [{}])[0].get("text", "")
        else:
            raise LLMServiceError(f"Perplexity API error: {resp.status_code} {resp.text}")
            
    def generate_content(self, content_blocks: List[Any], options: Optional[Dict[str, Any]] = None):
        prompt = "\n".join([str(cb) for cb in content_blocks])
        return self.generate_text(prompt, options)

class GeminiService(MCPLLMService):
    """
    Google Gemini (Generative AI) LLM service implementation following MCP standards.
    """
    def __init__(self, model_name: str = "gemini-pro", api_key: Optional[str] = None):
        super().__init__(LLMProvider.GEMINI, model_name, api_key)
        try:
            import google.generativeai as genai
            self.client = genai.GenerativeModel(model_name)
        except ImportError:
            logging.error("Google Generative AI SDK not installed. Please install with 'pip install google-generativeai'")
            self.client = None
            
    def generate_text(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        if not self.client:
            raise LLMServiceError("Gemini SDK not available.")
        response = self.client.generate_content(prompt)
        return response.text if hasattr(response, 'text') else str(response)
        
    def generate_content(self, content_blocks: List[Any], options: Optional[Dict[str, Any]] = None):
        prompt = "\n".join([str(cb) for cb in content_blocks])
        return self.generate_text(prompt, options)

class OllamaService(MCPLLMService):
    """
    Ollama LLM service implementation following MCP standards.
    This allows for using local LLMs with Ollama.
    """
    
    def __init__(self, model_name: str = "llama2", base_url: str = "http://localhost:11434"):
        super().__init__(LLMProvider.OLLAMA, model_name)
        self.base_url = base_url
        
        # Set API client
        self.client = None
        
    def generate_text(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generate text using Ollama API."""
        options = options or {}
        
        import requests
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "options": {
                        "temperature": options.get("temperature", 0.7),
                        "num_predict": options.get("max_tokens", 1024)
                    }
                }
            )
            
            response.raise_for_status()
            return response.json().get("response", "")
            
        except Exception as e:
            raise LLMServiceError(f"Ollama API error: {str(e)}")
            
    def generate_content(self, content_blocks: List[ContentBlock], options: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Generate content using Ollama API following MCP standards."""
        options = options or {}
        
        # Since Ollama doesn't natively support MCP, convert blocks to prompt text
        prompt = self.convert_blocks_to_prompt(content_blocks)
        
        # Add function definitions if enabled
        if options.get("enable_functions", True):
            function_defs = self.get_function_definitions()
            if function_defs:
                prompt += "\n\nAvailable functions:\n"
                for name, metadata in function_defs.items():
                    prompt += f"- {name}: {metadata.get('description', '')}\n"
                    prompt += f"  Parameters: {json.dumps(metadata.get('parameters', {}), indent=2)}\n\n"
                    
                prompt += "\nYou can call these functions using the format:\n"
                prompt += "Function Call: function_name\n"
                prompt += "Parameters: {\n  \"param1\": \"value1\",\n  \"param2\": \"value2\"\n}\n\n"
                
        try:
            # Generate response
            response_text = self.generate_text(prompt, options)
            
            # Parse the response into content blocks
            result_blocks = self.parse_text_to_content_blocks(response_text)
            
            # Auto-execute functions if enabled
            if options.get("auto_execute_functions", False):
                for block in list(result_blocks):  # Create a copy to avoid modification during iteration
                    if block.content_type == ContentType.FUNCTION_CALL:
                        function_name = block.content["function"]
                        parameters = block.content["parameters"]
                        
                        try:
                            result = self.invoke_function(function_name, parameters)
                            
                            result_blocks.append(ContentBlock(
                                content_type=ContentType.FUNCTION_RESPONSE,
                                content={
                                    "function": function_name,
                                    "result": result
                                },
                                metadata={"auto_executed": True}
                            ))
                        except Exception as e:
                            logging.error(f"Error auto-executing function {function_name}: {str(e)}")
                            
            return MCPMessage(content_blocks=result_blocks)
            
        except Exception as e:
            raise LLMServiceError(f"Ollama API error: {str(e)}")

class MockLLMService(MCPLLMService):
    """Mock LLM service for testing without API dependency."""
    
    def __init__(self):
        super().__init__(LLMProvider.MOCK, "mock-model")
            
    def generate_text(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generate mock text response."""
        options = options or {}
        
        # Generate a simple echo response
        return f"MOCK RESPONSE: You said: {prompt[:100]}..."
            
    def generate_content(self, content_blocks: List[ContentBlock], options: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Generate mock content response following MCP standards."""
        options = options or {}
        result_blocks = []
        
        # Generate a mock text response
        prompt = self.convert_blocks_to_prompt(content_blocks)
        result_blocks.append(ContentBlock(
            content_type=ContentType.TEXT,
            content=f"MOCK RESPONSE: Received {len(content_blocks)} content blocks."
        ))
        
        # If there's a structured data block, echo it back
        for block in content_blocks:
            if block.content_type == ContentType.STRUCTURED_DATA:
                result_blocks.append(ContentBlock(
                    content_type=ContentType.STRUCTURED_DATA,
                    content={"echo": block.content}
                ))
                break
                
        # If function calls are enabled, generate a mock function call
        if options.get("enable_functions", True):
            function_defs = self.get_function_definitions()
            if function_defs and options.get("auto_function_call", False):
                # Pick the first function
                function_name = next(iter(function_defs.keys()))
                parameters = {}
                
                # Generate mock parameters
                for param_name, param_info in function_defs[function_name].get("parameters", {}).items():
                    if param_info.get("type") == "string":
                        parameters[param_name] = "mock_value"
                    elif param_info.get("type") == "number":
                        parameters[param_name] = 42
                    elif param_info.get("type") == "boolean":
                        parameters[param_name] = True
                    else:
                        parameters[param_name] = "mock_value"
                        
                result_blocks.append(ContentBlock(
                    content_type=ContentType.FUNCTION_CALL,
                    content={
                        "function": function_name,
                        "parameters": parameters
                    }
                ))
                
                # Auto-execute if enabled
                if options.get("auto_execute_functions", False):
                    try:
                        result = self.invoke_function(function_name, parameters)
                        
                        result_blocks.append(ContentBlock(
                            content_type=ContentType.FUNCTION_RESPONSE,
                            content={
                                "function": function_name,
                                "result": result
                            },
                            metadata={"auto_executed": True}
                        ))
                    except Exception as e:
                        logging.error(f"Error auto-executing function {function_name}: {str(e)}")
                        
        return MCPMessage(content_blocks=result_blocks)

# LLM-enhanced agent that uses LLMs for reasoning
class LLMAgent(Agent):
    """Agent that uses LLM for reasoning, following the MCP agent model."""
    
    def __init__(self, name: str, description: str, llm_service: MCPLLMService):
        super().__init__(name, description)
        self.llm_service = llm_service
        
    def _reasoning_engine(self, perception_result: Dict[str, Any]) -> Dict[str, Any]:
        """Override the reasoning engine to use LLM."""
        try:
            # Create a structured data block with the perception result
            perception_block = ContentBlock(
                content_type=ContentType.STRUCTURED_DATA,
                content=perception_result
            )
            
            # Create a text block with the reasoning prompt
            prompt_text = f"""
            You are assisting the agent '{self.name}' with reasoning about the following perception result.
            Please analyze the data and determine the best course of action.
            
            Your task is to determine which functions to call and with what parameters.
            
            Return your reasoning in a structured format that can be used for execution.
            """
            
            prompt_block = ContentBlock(
                content_type=ContentType.TEXT,
                content=prompt_text
            )
            
            # Generate content using LLM
            llm_response = self.llm_service.generate_content(
                [prompt_block, perception_block],
                {
                    "enable_functions": True,
                    "auto_function_call": True,
                    "temperature": 0.3  # Lower temperature for more deterministic reasoning
                }
            )
            
            # Extract reasoning from LLM response
            reasoning_result = {"perception_result": perception_result, "llm_reasoning": {}}
            
            for block in llm_response.content_blocks:
                if block.content_type == ContentType.TEXT:
                    reasoning_result["llm_reasoning"]["explanation"] = block.content
                    
                elif block.content_type == ContentType.STRUCTURED_DATA:
                    reasoning_result["llm_reasoning"]["structured_output"] = block.content
                    
                elif block.content_type == ContentType.FUNCTION_CALL:
                    if "function_calls" not in reasoning_result:
                        reasoning_result["function_calls"] = []
                        
                    reasoning_result["function_calls"].append({
                        "function": block.content["function"],
                        "parameters": block.content["parameters"]
                    })
                    
            return reasoning_result
            
        except Exception as e:
            logging.error(f"Error in LLM reasoning: {str(e)}")
            # Fallback to default reasoning
            return super()._reasoning_engine(perception_result)
            
    def _response_generation(self, execution_result: Dict[str, Any]) -> List[ContentBlock]:
        """Override the response generation to use LLM."""
        try:
            # Create a structured data block with the execution result
            execution_block = ContentBlock(
                content_type=ContentType.STRUCTURED_DATA,
                content=execution_result
            )
            
            # Create a text block with the response generation prompt
            prompt_text = f"""
            You are assisting the agent '{self.name}' with generating a response based on the execution result.
            Please synthesize a clear and helpful response that conveys the important information.
            
            Your response should be well-structured and easy to understand.
            """
            
            prompt_block = ContentBlock(
                content_type=ContentType.TEXT,
                content=prompt_text
            )
            
            # Generate content using LLM
            llm_response = self.llm_service.generate_content(
                [prompt_block, execution_block],
                {"temperature": 0.5}
            )
            
            # Return the generated content blocks
            return llm_response.content_blocks
            
        except Exception as e:
            logging.error(f"Error in LLM response generation: {str(e)}")
            # Fallback to default response generation
            return super()._response_generation(execution_result)

# Create a global LLM service instance
def create_llm_service(provider_name: str = None, model_name: str = None, api_key: str = None):
    """Create an LLM service instance based on available APIs and configuration."""
    
    # If explicit provider is specified, try to use it
    if provider_name:
        if provider_name.lower() == "openai":
            try:
                return OpenAIService(model_name or "gpt-4", api_key)
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI service: {str(e)}")
                
        elif provider_name.lower() == "anthropic":
            try:
                return AnthropicService(model_name or "claude-2", api_key)
            except Exception as e:
                logging.error(f"Failed to initialize Anthropic service: {str(e)}")
                
        elif provider_name.lower() == "perplexity":
            try:
                return PerplexityService(model_name or "pplx-70b-online", api_key)
            except Exception as e:
                logging.error(f"Failed to initialize Perplexity service: {str(e)}")
                
        elif provider_name.lower() == "gemini":
            try:
                return GeminiService(model_name or "gemini-pro", api_key)
            except Exception as e:
                logging.error(f"Failed to initialize Gemini service: {str(e)}")
                
        elif provider_name.lower() == "ollama":
            try:
                return OllamaService(model_name or "llama2")
            except Exception as e:
                logging.error(f"Failed to initialize Ollama service: {str(e)}")
                
    # Try to initialize services in order of preference
    # 1. OpenAI (if API key is available)
    if os.environ.get("OPENAI_API_KEY") or api_key:
        try:
            return OpenAIService(model_name or "gpt-4", api_key or os.environ.get("OPENAI_API_KEY"))
        except Exception as e:
            logging.warning(f"Failed to initialize OpenAI service: {str(e)}")
            
    # 2. Anthropic (if API key is available)
    if os.environ.get("ANTHROPIC_API_KEY") or api_key:
        try:
            return AnthropicService(model_name or "claude-2", api_key or os.environ.get("ANTHROPIC_API_KEY"))
        except Exception as e:
            logging.warning(f"Failed to initialize Anthropic service: {str(e)}")
            
    # 3. Perplexity (if API key is available)
    if os.environ.get("PERPLEXITY_API_KEY") or api_key:
        try:
            return PerplexityService(model_name or "pplx-70b-online", api_key or os.environ.get("PERPLEXITY_API_KEY"))
        except Exception as e:
            logging.warning(f"Failed to initialize Perplexity service: {str(e)}")
            
    # 4. Gemini (if API key is available)
    if os.environ.get("GEMINI_API_KEY") or api_key:
        try:
            return GeminiService(model_name or "gemini-pro", api_key or os.environ.get("GEMINI_API_KEY"))
        except Exception as e:
            logging.warning(f"Failed to initialize Gemini service: {str(e)}")
            
    # 5. Local Ollama (if installed)
    try:
        import requests
        requests.get("http://localhost:11434/api/version")
        return OllamaService(model_name or "llama2")
    except Exception as e:
        logging.warning(f"Failed to initialize Ollama service: {str(e)}")
            
    # 6. Fallback to mock
    logging.warning("No LLM service available, using mock service")
    return MockLLMService()

# Initialize a global LLM service
global_llm_service = create_llm_service()

# Create an LLM-enhanced agent
def create_llm_agent(name: str, description: str, llm_service=None):
    """Create an agent enhanced with LLM reasoning capabilities."""
    return LLMAgent(name, description, llm_service or global_llm_service)