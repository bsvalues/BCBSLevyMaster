"""
Model Content Protocol (MCP) Core Implementation

This module implements the core components of the Model Content Protocol for the 
SaaS Levy Calculation Application, enabling AI-driven autonomous operations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

# Define the MCP Content Types
class ContentType(Enum):
    TEXT = "text"
    STRUCTURED_DATA = "structured_data"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESPONSE = "function_response"
    MULTI_MODAL = "multi_modal"

# Content block structure following MCP standards
class ContentBlock:
    def __init__(
        self, 
        content_type: ContentType, 
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[Dict[str, Any]]] = None,
        references: Optional[List[Dict[str, Any]]] = None
    ):
        self.content_type = content_type
        self.content = content
        self.metadata = metadata or {}
        self.annotations = annotations or []
        self.references = references or []
        self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ContentBlock to dictionary representation."""
        return {
            "content_type": self.content_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "annotations": self.annotations,
            "references": self.references,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentBlock':
        """Create ContentBlock from dictionary."""
        return cls(
            content_type=ContentType(data["content_type"]),
            content=data["content"],
            metadata=data.get("metadata", {}),
            annotations=data.get("annotations", []),
            references=data.get("references", [])
        )

# MCP Message structure for communication
class MCPMessage:
    def __init__(
        self,
        content_blocks: List[ContentBlock],
        message_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        from uuid import uuid4
        
        self.message_id = message_id or str(uuid4())
        self.parent_id = parent_id
        self.content_blocks = content_blocks
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MCPMessage to dictionary representation."""
        return {
            "message_id": self.message_id,
            "parent_id": self.parent_id,
            "content_blocks": [block.to_dict() for block in self.content_blocks],
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create MCPMessage from dictionary."""
        return cls(
            content_blocks=[ContentBlock.from_dict(block) for block in data["content_blocks"]],
            message_id=data.get("message_id"),
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """Convert MCPMessage to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """Create MCPMessage from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

# Function Registry following MCP Function System
class FunctionRegistry:
    def __init__(self):
        self.functions = {}
    
    def register_function(self, name: str, function, metadata: Dict[str, Any]):
        """Register a function in the MCP registry."""
        self.functions[name] = {
            "function": function,
            "metadata": metadata
        }
        logging.info(f"Registered function: {name}")
    
    def get_function(self, name: str):
        """Get a function from the registry."""
        if name not in self.functions:
            raise KeyError(f"Function {name} not registered")
        return self.functions[name]["function"]
    
    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Get metadata for a function."""
        if name not in self.functions:
            raise KeyError(f"Function {name} not registered")
        return self.functions[name]["metadata"]
    
    def list_functions(self) -> List[str]:
        """List all registered functions."""
        return list(self.functions.keys())
    
    def get_function_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Get a catalog of all functions with their metadata."""
        return {name: self.functions[name]["metadata"] for name in self.functions}

# Workflow Orchestrator following MCP Workflow Orchestration
class WorkflowOrchestrator:
    def __init__(self, function_registry: FunctionRegistry):
        self.function_registry = function_registry
        self.workflows = {}
    
    def register_workflow(self, name: str, workflow_definition: Dict[str, Any]):
        """Register a workflow in the MCP orchestrator."""
        self.workflows[name] = workflow_definition
        logging.info(f"Registered workflow: {name}")
    
    def execute_workflow(self, name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow by name with the given input data."""
        if name not in self.workflows:
            raise KeyError(f"Workflow {name} not registered")
        
        workflow = self.workflows[name]
        current_state = {"input": input_data, "output": {}}
        
        for step in workflow.get("steps", []):
            step_name = step["name"]
            function_name = step["function"]
            
            # Map inputs from current state
            mapped_inputs = {}
            for param, value_path in step.get("input_mapping", {}).items():
                # Extract nested values using path notation (e.g., "output.previous_step.value")
                parts = value_path.split(".")
                current_value = current_state
                for part in parts:
                    if part in current_value:
                        current_value = current_value[part]
                    else:
                        current_value = None
                        break
                
                mapped_inputs[param] = current_value
            
            # Execute the function
            try:
                function = self.function_registry.get_function(function_name)
                result = function(**mapped_inputs)
                
                # Store the result in the current state
                if "output" not in current_state:
                    current_state["output"] = {}
                current_state["output"][step_name] = result
                
            except Exception as e:
                logging.error(f"Error executing step {step_name}: {str(e)}")
                if step.get("error_handling", "fail") == "continue":
                    continue
                else:
                    raise
        
        return current_state["output"]

# Create global instances for application-wide use
mcp_function_registry = FunctionRegistry()
mcp_workflow_orchestrator = WorkflowOrchestrator(mcp_function_registry)

# Content processing utilities
def create_text_block(text: str, metadata: Optional[Dict[str, Any]] = None) -> ContentBlock:
    """Create a ContentBlock with text content."""
    return ContentBlock(
        content_type=ContentType.TEXT,
        content=text,
        metadata=metadata
    )

def create_structured_data_block(data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ContentBlock:
    """Create a ContentBlock with structured data content."""
    return ContentBlock(
        content_type=ContentType.STRUCTURED_DATA,
        content=data,
        metadata=metadata
    )

def create_function_call_block(
    function_name: str, 
    parameters: Dict[str, Any], 
    metadata: Optional[Dict[str, Any]] = None
) -> ContentBlock:
    """Create a ContentBlock representing a function call."""
    return ContentBlock(
        content_type=ContentType.FUNCTION_CALL,
        content={
            "function": function_name,
            "parameters": parameters
        },
        metadata=metadata
    )

def create_function_response_block(
    function_name: str, 
    result: Any, 
    metadata: Optional[Dict[str, Any]] = None
) -> ContentBlock:
    """Create a ContentBlock representing a function response."""
    return ContentBlock(
        content_type=ContentType.FUNCTION_RESPONSE,
        content={
            "function": function_name,
            "result": result
        },
        metadata=metadata
    )