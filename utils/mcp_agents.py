"""
Model Content Protocol (MCP) Agent System

This module implements the agent architecture defined in the MCP, enabling
autonomous agent workflows for the SaaS Levy Calculation Application.
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum

from utils.mcp_core import (
    ContentBlock, 
    ContentType, 
    MCPMessage,
    FunctionRegistry,
    mcp_function_registry,
    create_text_block,
    create_structured_data_block,
    create_function_call_block,
    create_function_response_block
)

# Agent State Types
class AgentStateType(Enum):
    CONVERSATION = "conversation"
    TASK = "task"
    KNOWLEDGE = "knowledge"
    PERFORMANCE = "performance"

# Agent Lifecycle Phases
class AgentPhase(Enum):
    INITIALIZATION = "initialization"
    PERCEPTION = "perception"
    REASONING = "reasoning"
    EXECUTION = "execution"
    RESPONSE_GENERATION = "response_generation"
    LEARNING = "learning"

class AgentState:
    """Represents the state of an agent following MCP's agent state management."""
    
    def __init__(self):
        self.conversation_state = {}  # User interaction history and context
        self.task_state = {           # Current execution phase and subtask status
            "current_phase": AgentPhase.INITIALIZATION.value,
            "tasks": [],
            "active_task_id": None
        }
        self.knowledge_state = {}     # Information gathered and belief confidence
        self.performance_state = {    # Execution metrics and patterns
            "task_durations": {},
            "error_counts": {},
            "success_rates": {}
        }
    
    def update_phase(self, phase: AgentPhase):
        """Update the current agent phase."""
        self.task_state["current_phase"] = phase.value
        
    def add_task(self, task_id: str, task_description: str, status: str = "pending"):
        """Add a new task to the agent's task state."""
        task = {
            "id": task_id,
            "description": task_description,
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        self.task_state["tasks"].append(task)
        
    def update_task_status(self, task_id: str, status: str):
        """Update the status of a task."""
        for task in self.task_state["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                task["updated_at"] = datetime.utcnow().isoformat()
                break
                
    def set_active_task(self, task_id: str):
        """Set the active task."""
        self.task_state["active_task_id"] = task_id
        
    def add_to_conversation(self, role: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation history."""
        if "messages" not in self.conversation_state:
            self.conversation_state["messages"] = []
            
        self.conversation_state["messages"].append({
            "role": role,
            "content": message,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        
    def update_knowledge(self, key: str, value: Any, confidence: float = 1.0):
        """Update the agent's knowledge state."""
        self.knowledge_state[key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    def record_task_duration(self, task_type: str, duration_ms: int):
        """Record the duration of a task for performance tracking."""
        if task_type not in self.performance_state["task_durations"]:
            self.performance_state["task_durations"][task_type] = []
            
        self.performance_state["task_durations"][task_type].append(duration_ms)
        
    def record_error(self, component: str):
        """Record an error for performance tracking."""
        if component not in self.performance_state["error_counts"]:
            self.performance_state["error_counts"][component] = 0
            
        self.performance_state["error_counts"][component] += 1
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent state to dictionary representation."""
        return {
            "conversation_state": self.conversation_state,
            "task_state": self.task_state,
            "knowledge_state": self.knowledge_state,
            "performance_state": self.performance_state
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Create agent state from dictionary."""
        state = cls()
        state.conversation_state = data.get("conversation_state", {})
        state.task_state = data.get("task_state", {
            "current_phase": AgentPhase.INITIALIZATION.value,
            "tasks": [],
            "active_task_id": None
        })
        state.knowledge_state = data.get("knowledge_state", {})
        state.performance_state = data.get("performance_state", {
            "task_durations": {},
            "error_counts": {},
            "success_rates": {}
        })
        return state

class Agent:
    """Base agent class following MCP's Agent Workflow model."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.state = AgentState()
        self.capabilities = {}
        
    def register_capability(self, name: str, function: Callable, metadata: Dict[str, Any]):
        """Register an agent capability."""
        self.capabilities[name] = {
            "function": function,
            "metadata": metadata
        }
        
        # Also register with the global MCP function registry
        full_capability_name = f"{self.name}.{name}"
        mcp_function_registry.register_function(
            full_capability_name, 
            function,
            {**metadata, "agent": self.name}
        )
        
    def process(self, message: MCPMessage) -> MCPMessage:
        """Process a message according to the MCP agent workflow."""
        start_time = datetime.utcnow()
        
        response_blocks = []
        response_metadata = {}
        
        try:
            # Update state
            self.state.update_phase(AgentPhase.PERCEPTION)
            
            # Perception: Extract context and intent from the message
            perception_result = self._perception_pipeline(message)
            response_metadata["perception"] = perception_result
            
            # Reasoning: Plan actions based on perception
            self.state.update_phase(AgentPhase.REASONING)
            reasoning_result = self._reasoning_engine(perception_result)
            response_metadata["reasoning"] = reasoning_result
            
            # Execution: Perform actions based on reasoning
            self.state.update_phase(AgentPhase.EXECUTION)
            execution_result = self._execution_pipeline(reasoning_result)
            
            # Response Generation: Create response based on execution results
            self.state.update_phase(AgentPhase.RESPONSE_GENERATION)
            response_blocks = self._response_generation(execution_result)
            
            # Learning: Update internal models based on interaction
            self.state.update_phase(AgentPhase.LEARNING)
            learning_result = self._learning_pipeline(execution_result)
            response_metadata["learning"] = learning_result
            
            # Track performance
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            self.state.record_task_duration("message_processing", duration_ms)
            
            # Create response message
            response = MCPMessage(
                content_blocks=response_blocks,
                parent_id=message.message_id,
                metadata=response_metadata
            )
            
            return response
            
        except Exception as e:
            # Error handling and recovery
            logging.error(f"Error in agent {self.name}: {str(e)}")
            logging.error(traceback.format_exc())
            
            self.state.record_error("process")
            
            # Create error response
            error_block = create_text_block(
                f"Error in agent {self.name}: {str(e)}",
                {"error": True}
            )
            
            return MCPMessage(
                content_blocks=[error_block],
                parent_id=message.message_id,
                metadata={"error": str(e)}
            )
    
    def _perception_pipeline(self, message: MCPMessage) -> Dict[str, Any]:
        """
        Process inputs, extract context, recognize intent, model the environment.
        Override in subclasses for specialized perception.
        """
        return {"message_id": message.message_id}
    
    def _reasoning_engine(self, perception_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan action sequences, analyze dependencies, allocate resources, form hypotheses.
        Override in subclasses for specialized reasoning.
        """
        return {"perception_result": perception_result}
    
    def _execution_pipeline(self, reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select and invoke functions, bind parameters, capture and validate results.
        Override in subclasses for specialized execution.
        """
        return {"reasoning_result": reasoning_result}
    
    def _response_generation(self, execution_result: Dict[str, Any]) -> List[ContentBlock]:
        """
        Synthesize output, verify safety and quality, format and deliver response.
        Override in subclasses for specialized response generation.
        """
        result_block = create_structured_data_block(execution_result)
        return [result_block]
    
    def _learning_pipeline(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate performance, integrate new knowledge, refine strategies, evolve capabilities.
        Override in subclasses for specialized learning.
        """
        return {"execution_result": execution_result}

# Agent Repository for multi-agent collaboration
class AgentRepository:
    """Repository for managing multiple agents and enabling collaboration."""
    
    def __init__(self):
        self.agents = {}
        
    def register_agent(self, agent: Agent):
        """Register an agent in the repository."""
        self.agents[agent.name] = agent
        logging.info(f"Registered agent: {agent.name}")
        
    def get_agent(self, name: str) -> Agent:
        """Get an agent by name."""
        if name not in self.agents:
            raise KeyError(f"Agent {name} not registered")
        return self.agents[name]
    
    def list_agents(self) -> List[str]:
        """List all registered agents."""
        return list(self.agents.keys())
    
    def get_agent_capabilities(self, agent_name: str) -> Dict[str, Dict[str, Any]]:
        """Get capabilities of a specific agent."""
        agent = self.get_agent(agent_name)
        return {name: cap["metadata"] for name, cap in agent.capabilities.items()}
    
    def discover_capabilities(self, capability_type: Optional[str] = None) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Discover capabilities across all agents, optionally filtered by type."""
        capabilities = {}
        
        for agent_name, agent in self.agents.items():
            agent_capabilities = {}
            
            for cap_name, cap_info in agent.capabilities.items():
                if capability_type is None or cap_info["metadata"].get("type") == capability_type:
                    agent_capabilities[cap_name] = cap_info["metadata"]
            
            if agent_capabilities:
                capabilities[agent_name] = agent_capabilities
                
        return capabilities
        
    def allocate_task(self, task_description: str, required_capability: str) -> Optional[str]:
        """Allocate a task to the most suitable agent based on required capability."""
        qualified_agents = []
        
        for agent_name, agent in self.agents.items():
            if required_capability in agent.capabilities:
                qualified_agents.append(agent_name)
                
        if not qualified_agents:
            return None
            
        # For now, simply return the first qualified agent
        # In a more advanced implementation, this would consider reliability, latency, cost, etc.
        return qualified_agents[0]
        
    def execute_multi_agent_workflow(self, coordinator_agent_name: str, initial_message: MCPMessage) -> MCPMessage:
        """Execute a multi-agent workflow coordinated by the specified agent."""
        coordinator = self.get_agent(coordinator_agent_name)
        return coordinator.process(initial_message)

# Create a global agent repository
agent_repository = AgentRepository()

# Example specialized agents
class AnalysisAgent(Agent):
    """Agent specialized in data analysis, following MCP's agent model."""
    
    def __init__(self, name: str):
        super().__init__(name, "Specialized in analyzing data and generating insights")
        
        # Register analysis capabilities
        self.register_capability(
            "analyze_levy_rates",
            self._analyze_levy_rates,
            {
                "type": "analysis",
                "description": "Analyze levy rates to identify trends and patterns",
                "parameters": {
                    "tax_codes": {
                        "type": "array",
                        "description": "List of tax codes with their levy rates"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Analysis results with trends and patterns"
                }
            }
        )
        
        self.register_capability(
            "compare_assessed_values",
            self._compare_assessed_values,
            {
                "type": "analysis",
                "description": "Compare assessed values across tax districts",
                "parameters": {
                    "district_data": {
                        "type": "object",
                        "description": "Data about tax districts and their assessed values"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Comparison results with insights"
                }
            }
        )
        
    def _analyze_levy_rates(self, tax_codes):
        """Analyze levy rates to identify trends and patterns."""
        # This would contain the actual analysis logic
        # For now, return a simple mock result
        return {
            "trends": {
                "increasing": [code for code, data in tax_codes.items() if data.get("levy_rate", 0) > data.get("previous_year_rate", 0)],
                "decreasing": [code for code, data in tax_codes.items() if data.get("levy_rate", 0) < data.get("previous_year_rate", 0)],
                "stable": [code for code, data in tax_codes.items() if data.get("levy_rate", 0) == data.get("previous_year_rate", 0)]
            },
            "outliers": [
                code for code, data in tax_codes.items() 
                if data.get("levy_rate", 0) > 5.5  # Approaching statutory limit
            ],
            "recommendations": [
                {
                    "tax_code": code,
                    "recommendation": "Review for statutory compliance",
                    "reason": "Approaching or exceeding 101% of previous year rate"
                }
                for code, data in tax_codes.items()
                if data.get("levy_rate", 0) > data.get("previous_year_rate", 0) * 1.005
            ]
        }
        
    def _compare_assessed_values(self, district_data):
        """Compare assessed values across tax districts."""
        # This would contain the actual comparison logic
        # For now, return a simple mock result
        districts = list(district_data.keys())
        total_values = {district: sum(area["assessed_value"] for area in areas) for district, areas in district_data.items()}
        
        return {
            "district_rankings": sorted(districts, key=lambda d: total_values[d], reverse=True),
            "total_values": total_values,
            "percent_change": {
                district: (total_values[district] - district_data[district][0].get("previous_year_value", 0)) 
                         / district_data[district][0].get("previous_year_value", 1) * 100
                for district in districts
            }
        }
        
    def _perception_pipeline(self, message: MCPMessage) -> Dict[str, Any]:
        """Specialized perception for data analysis."""
        perception_result = super()._perception_pipeline(message)
        
        # Extract data from content blocks
        data_blocks = [
            block for block in message.content_blocks 
            if block.content_type == ContentType.STRUCTURED_DATA
        ]
        
        if data_blocks:
            perception_result["data"] = [block.content for block in data_blocks]
            perception_result["data_count"] = len(data_blocks)
        
        function_call_blocks = [
            block for block in message.content_blocks 
            if block.content_type == ContentType.FUNCTION_CALL
        ]
        
        if function_call_blocks:
            perception_result["function_calls"] = [block.content for block in function_call_blocks]
            
        return perception_result
        
    def _reasoning_engine(self, perception_result: Dict[str, Any]) -> Dict[str, Any]:
        """Specialized reasoning for data analysis."""
        reasoning_result = super()._reasoning_engine(perception_result)
        
        # Determine which analysis functions to call based on the data
        reasoning_result["analysis_plan"] = []
        
        if "data" in perception_result and perception_result["data"]:
            # Analyze the first data block to determine its structure
            data = perception_result["data"][0]
            
            if isinstance(data, dict) and "tax_codes" in data:
                reasoning_result["analysis_plan"].append({
                    "function": "analyze_levy_rates",
                    "parameters": {"tax_codes": data["tax_codes"]}
                })
                
            if isinstance(data, dict) and "districts" in data:
                reasoning_result["analysis_plan"].append({
                    "function": "compare_assessed_values",
                    "parameters": {"district_data": data["districts"]}
                })
                
        # If there are explicit function calls, use those instead
        if "function_calls" in perception_result and perception_result["function_calls"]:
            reasoning_result["analysis_plan"] = [
                {
                    "function": call["function"],
                    "parameters": call["parameters"]
                }
                for call in perception_result["function_calls"]
                if call["function"] in self.capabilities
            ]
            
        return reasoning_result
            
    def _execution_pipeline(self, reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
        """Specialized execution for data analysis."""
        execution_result = super()._execution_pipeline(reasoning_result)
        
        execution_result["analysis_results"] = []
        
        # Execute each analysis function in the plan
        for analysis in reasoning_result.get("analysis_plan", []):
            try:
                function_name = analysis["function"]
                parameters = analysis["parameters"]
                
                if function_name in self.capabilities:
                    function = self.capabilities[function_name]["function"]
                    result = function(**parameters)
                    
                    execution_result["analysis_results"].append({
                        "function": function_name,
                        "parameters": parameters,
                        "result": result
                    })
                    
            except Exception as e:
                logging.error(f"Error executing analysis function {function_name}: {str(e)}")
                execution_result["analysis_results"].append({
                    "function": function_name,
                    "parameters": parameters,
                    "error": str(e)
                })
                
        return execution_result
        
    def _response_generation(self, execution_result: Dict[str, Any]) -> List[ContentBlock]:
        """Specialized response generation for data analysis."""
        response_blocks = []
        
        # Generate a summary text block
        summary_text = f"Analysis completed with {len(execution_result.get('analysis_results', []))} results."
        response_blocks.append(create_text_block(summary_text))
        
        # Add detailed results as structured data blocks
        for analysis_result in execution_result.get("analysis_results", []):
            if "error" not in analysis_result:
                function_name = analysis_result["function"]
                result = analysis_result["result"]
                
                response_blocks.append(
                    create_function_response_block(function_name, result)
                )
                
        return response_blocks

# Create a specialized prediction agent for levy calculation
class LevyPredictionAgent(Agent):
    """Agent specialized in predicting future levy rates and assessed values."""
    
    def __init__(self, name: str):
        super().__init__(name, "Specialized in predicting future levy rates and assessed values")
        
        # Register prediction capabilities
        self.register_capability(
            "predict_levy_rates",
            self._predict_levy_rates,
            {
                "type": "prediction",
                "description": "Predict future levy rates based on historical data",
                "parameters": {
                    "historical_rates": {
                        "type": "object",
                        "description": "Historical levy rates by tax code and year"
                    },
                    "years_ahead": {
                        "type": "integer",
                        "description": "Number of years to predict into the future"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Predicted levy rates with confidence intervals"
                }
            }
        )
        
        self.register_capability(
            "predict_assessed_values",
            self._predict_assessed_values,
            {
                "type": "prediction",
                "description": "Predict future assessed values based on historical data",
                "parameters": {
                    "historical_values": {
                        "type": "object",
                        "description": "Historical assessed values by property or district and year"
                    },
                    "years_ahead": {
                        "type": "integer",
                        "description": "Number of years to predict into the future"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Predicted assessed values with confidence intervals"
                }
            }
        )
        
    def _predict_levy_rates(self, historical_rates, years_ahead=1):
        """Predict future levy rates based on historical data."""
        # This would contain actual prediction logic, possibly using statistical models
        # For now, return a simplified prediction
        predictions = {}
        
        for tax_code, yearly_rates in historical_rates.items():
            # Calculate simple trend (average yearly change)
            years = sorted(yearly_rates.keys())
            if len(years) >= 2:
                rates = [yearly_rates[year] for year in years]
                avg_change = sum(rates[i] - rates[i-1] for i in range(1, len(rates))) / (len(rates) - 1)
                
                # Apply trend for prediction
                latest_year = max(years)
                latest_rate = yearly_rates[latest_year]
                
                predictions[tax_code] = {
                    f"{latest_year + i}": {
                        "predicted_rate": latest_rate + avg_change * i,
                        "confidence_low": latest_rate + avg_change * i * 0.9,
                        "confidence_high": latest_rate + avg_change * i * 1.1
                    }
                    for i in range(1, years_ahead + 1)
                }
                
        return {
            "predictions": predictions,
            "methodology": "trend_extrapolation",
            "confidence_level": 0.9,
            "prediction_date": datetime.utcnow().isoformat()
        }
        
    def _predict_assessed_values(self, historical_values, years_ahead=1):
        """Predict future assessed values based on historical data."""
        # This would contain actual prediction logic, possibly using statistical models
        # For now, return a simplified prediction
        predictions = {}
        
        for entity_id, yearly_values in historical_values.items():
            # Calculate simple trend (average yearly percentage change)
            years = sorted(yearly_values.keys())
            if len(years) >= 2:
                values = [yearly_values[year] for year in years]
                percent_changes = [(values[i] / values[i-1]) - 1 for i in range(1, len(values))]
                avg_percent_change = sum(percent_changes) / len(percent_changes)
                
                # Apply trend for prediction
                latest_year = max(years)
                latest_value = yearly_values[latest_year]
                
                predictions[entity_id] = {
                    f"{latest_year + i}": {
                        "predicted_value": latest_value * ((1 + avg_percent_change) ** i),
                        "confidence_low": latest_value * ((1 + avg_percent_change * 0.9) ** i),
                        "confidence_high": latest_value * ((1 + avg_percent_change * 1.1) ** i)
                    }
                    for i in range(1, years_ahead + 1)
                }
                
        return {
            "predictions": predictions,
            "methodology": "compound_growth",
            "confidence_level": 0.9,
            "prediction_date": datetime.utcnow().isoformat()
        }
        
    # Override agent workflow methods as needed, similar to AnalysisAgent

# Coordinator agent for orchestrating multi-agent workflows
class CoordinatorAgent(Agent):
    """Agent specialized in coordinating workflows across multiple agents."""
    
    def __init__(self, name: str):
        super().__init__(name, "Specialized in coordinating multi-agent workflows")
        
        # Register coordination capabilities
        self.register_capability(
            "coordinate_analysis_workflow",
            self._coordinate_analysis_workflow,
            {
                "type": "coordination",
                "description": "Coordinate a complete data analysis workflow",
                "parameters": {
                    "analysis_request": {
                        "type": "object",
                        "description": "Details of the analysis request"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Complete analysis results"
                }
            }
        )
        
        self.register_capability(
            "coordinate_prediction_workflow",
            self._coordinate_prediction_workflow,
            {
                "type": "coordination",
                "description": "Coordinate a complete prediction workflow",
                "parameters": {
                    "prediction_request": {
                        "type": "object",
                        "description": "Details of the prediction request"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Complete prediction results"
                }
            }
        )
        
    def _coordinate_analysis_workflow(self, analysis_request):
        """Coordinate a complete data analysis workflow."""
        results = {"workflow_id": f"analysis_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"}
        
        try:
            # 1. Find appropriate analysis agent
            analysis_agents = agent_repository.discover_capabilities("analysis")
            if not analysis_agents:
                raise ValueError("No analysis agents available")
                
            analysis_agent_name = next(iter(analysis_agents.keys()))
            analysis_agent = agent_repository.get_agent(analysis_agent_name)
            
            # 2. Prepare analysis request message
            analysis_message = MCPMessage(
                content_blocks=[
                    create_structured_data_block(analysis_request),
                    create_function_call_block(
                        f"{analysis_agent_name}.analyze_levy_rates",
                        {"tax_codes": analysis_request.get("tax_codes", {})}
                    )
                ]
            )
            
            # 3. Send request to analysis agent
            analysis_response = analysis_agent.process(analysis_message)
            
            # 4. Extract results
            analysis_results = []
            for block in analysis_response.content_blocks:
                if block.content_type == ContentType.FUNCTION_RESPONSE:
                    analysis_results.append(block.content)
                    
            results["analysis_results"] = analysis_results
            
            # 5. Return consolidated results
            return results
            
        except Exception as e:
            logging.error(f"Error in analysis workflow coordination: {str(e)}")
            results["error"] = str(e)
            return results
            
    def _coordinate_prediction_workflow(self, prediction_request):
        """Coordinate a complete prediction workflow."""
        results = {"workflow_id": f"prediction_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"}
        
        try:
            # 1. Find appropriate prediction agent
            prediction_agents = agent_repository.discover_capabilities("prediction")
            if not prediction_agents:
                raise ValueError("No prediction agents available")
                
            prediction_agent_name = next(iter(prediction_agents.keys()))
            prediction_agent = agent_repository.get_agent(prediction_agent_name)
            
            # 2. Prepare prediction request message
            prediction_message = MCPMessage(
                content_blocks=[
                    create_structured_data_block(prediction_request),
                    create_function_call_block(
                        f"{prediction_agent_name}.predict_levy_rates",
                        {
                            "historical_rates": prediction_request.get("historical_rates", {}),
                            "years_ahead": prediction_request.get("years_ahead", 1)
                        }
                    )
                ]
            )
            
            # 3. Send request to prediction agent
            prediction_response = prediction_agent.process(prediction_message)
            
            # 4. Extract results
            prediction_results = []
            for block in prediction_response.content_blocks:
                if block.content_type == ContentType.FUNCTION_RESPONSE:
                    prediction_results.append(block.content)
                    
            results["prediction_results"] = prediction_results
            
            # 5. Return consolidated results
            return results
            
        except Exception as e:
            logging.error(f"Error in prediction workflow coordination: {str(e)}")
            results["error"] = str(e)
            return results
            
    def _perception_pipeline(self, message: MCPMessage) -> Dict[str, Any]:
        """Specialized perception for coordination."""
        perception_result = super()._perception_pipeline(message)
        
        # Extract data and function calls from content blocks
        data_blocks = [
            block for block in message.content_blocks 
            if block.content_type == ContentType.STRUCTURED_DATA
        ]
        
        if data_blocks:
            perception_result["data"] = [block.content for block in data_blocks]
            
        function_call_blocks = [
            block for block in message.content_blocks 
            if block.content_type == ContentType.FUNCTION_CALL
        ]
        
        if function_call_blocks:
            perception_result["function_calls"] = [block.content for block in function_call_blocks]
            
        # Determine workflow type based on content
        perception_result["workflow_type"] = None
        if "function_calls" in perception_result:
            for call in perception_result["function_calls"]:
                function_name = call["function"]
                if "analysis" in function_name.lower():
                    perception_result["workflow_type"] = "analysis"
                elif "predict" in function_name.lower():
                    perception_result["workflow_type"] = "prediction"
                    
        return perception_result
        
    def _reasoning_engine(self, perception_result: Dict[str, Any]) -> Dict[str, Any]:
        """Specialized reasoning for coordination."""
        reasoning_result = super()._reasoning_engine(perception_result)
        
        # Determine which coordination workflow to execute
        if perception_result.get("workflow_type") == "analysis":
            reasoning_result["coordination_plan"] = {
                "function": "coordinate_analysis_workflow",
                "parameters": {
                    "analysis_request": perception_result.get("data", [{}])[0]
                }
            }
        elif perception_result.get("workflow_type") == "prediction":
            reasoning_result["coordination_plan"] = {
                "function": "coordinate_prediction_workflow",
                "parameters": {
                    "prediction_request": perception_result.get("data", [{}])[0]
                }
            }
        else:
            # Default to analysis if workflow type is unclear
            reasoning_result["coordination_plan"] = {
                "function": "coordinate_analysis_workflow",
                "parameters": {
                    "analysis_request": perception_result.get("data", [{}])[0]
                }
            }
            
        return reasoning_result
            
    def _execution_pipeline(self, reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
        """Specialized execution for coordination."""
        execution_result = super()._execution_pipeline(reasoning_result)
        
        # Execute the coordination function
        plan = reasoning_result.get("coordination_plan")
        if plan:
            try:
                function_name = plan["function"]
                parameters = plan["parameters"]
                
                if function_name in self.capabilities:
                    function = self.capabilities[function_name]["function"]
                    result = function(**parameters)
                    
                    execution_result["coordination_result"] = result
                    
            except Exception as e:
                logging.error(f"Error executing coordination function {function_name}: {str(e)}")
                execution_result["error"] = str(e)
                
        return execution_result
        
    def _response_generation(self, execution_result: Dict[str, Any]) -> List[ContentBlock]:
        """Specialized response generation for coordination."""
        response_blocks = []
        
        # Generate a summary text block
        if "coordination_result" in execution_result:
            result = execution_result["coordination_result"]
            workflow_id = result.get("workflow_id", "unknown")
            
            summary_text = f"Coordination workflow {workflow_id} completed successfully."
            if "error" in result:
                summary_text = f"Coordination workflow {workflow_id} encountered an error: {result['error']}"
                
            response_blocks.append(create_text_block(summary_text))
            
            # Add detailed results as structured data blocks
            response_blocks.append(create_structured_data_block(result))
            
        else:
            error_text = "Coordination failed: " + execution_result.get("error", "Unknown error")
            response_blocks.append(create_text_block(error_text, {"error": True}))
            
        return response_blocks

# Initialize default agents
def initialize_default_agents():
    """Initialize and register default agents for the SaaS Levy Calculation Application."""
    
    # Create agents
    analysis_agent = AnalysisAgent("LevyAnalysisAgent")
    prediction_agent = LevyPredictionAgent("LevyPredictionAgent")
    coordinator_agent = CoordinatorAgent("WorkflowCoordinatorAgent")
    
    # Register agents in the repository
    agent_repository.register_agent(analysis_agent)
    agent_repository.register_agent(prediction_agent)
    agent_repository.register_agent(coordinator_agent)
    
    return agent_repository