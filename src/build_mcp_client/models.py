"""Models for the build_mcp_client package."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_serializer, root_validator

class MCPBaseModel(BaseModel):
    """Base model with JSON serialization support."""
    
    @model_serializer
    def serialize(self) -> Dict[str, Any]:
        """Serialize the model to a JSON-compatible dict."""
        data = self.model_dump()
        # Convert any special types to their string representation
        for key, value in data.items():
            if hasattr(value, 'text'):  # Handle TextContent objects
                data[key] = value.text
            elif hasattr(value, 'model_dump'):  # Handle nested Pydantic models
                data[key] = value.model_dump()
        return data

class MCPCapability(MCPBaseModel):
    """Represents any MCP capability (tool, resource, prompt, etc.)."""
    name: str = Field(..., description="Name of the capability")
    capability_type: str = Field(..., description="Type of capability (tool, resource, prompt, etc.)")
    description: Optional[str] = Field(None, description="Description of the capability")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    capability_schema: Optional[Dict[str, Any]] = Field(None, description="Optional schema for the capability")

class MCPAction(MCPBaseModel):
    """Represents an action to be taken using an MCP capability."""
    capability: str = Field(..., description="Name of the capability to use")
    capability_type: str = Field(..., description="Type of capability (tool, resource, prompt, etc.)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class MCPResult(MCPBaseModel):
    """Represents the result of executing an MCP action."""
    capability: str = Field(..., description="Name of the capability used")
    capability_type: str = Field(..., description="Type of capability used")
    success: bool = Field(..., description="Whether the action was successful")
    data: Any = Field(..., description="Result data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Result metadata")
    error: Optional[str] = Field(None, description="Error message if action failed")
    timestamp: str = Field(..., description="Execution timestamp")

class ResearchPlan(MCPBaseModel):
    """A flexible research plan that can work with any MCP capabilities."""
    actions: List[MCPAction] = Field(..., description="Actions to execute")
    expected_outcomes: List[str] = Field(..., description="Expected outcomes from actions")
    fallbacks: List[MCPAction] = Field(default_factory=list, description="Fallback actions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional plan metadata")

class ResearchResults(MCPBaseModel):
    """Results from executing a research plan."""
    results: List[MCPResult] = Field(..., description="Results from each action")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    summary: Optional[str] = Field(None, description="Optional summary of results")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")

    @property
    def success_count(self) -> int:
        """Get the number of successful actions."""
        return len([r for r in self.results if r.success])

    @property
    def failure_count(self) -> int:
        """Get the number of failed actions."""
        return len([r for r in self.results if not r.success])

class ResearchSession(MCPBaseModel):
    """Represents a research session with any MCP server."""
    session_id: str = Field(..., description="Unique session identifier")
    capabilities: List[MCPCapability] = Field(..., description="Available capabilities")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    results: List[ResearchResults] = Field(default_factory=list, description="Research results")
    start_time: str = Field(..., description="Session start time")
    last_update: str = Field(..., description="Last update time")

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of research actions."""
        total_results = sum(len(r.results) for r in self.results)
        if total_results == 0:
            return 0.0
        successful = sum(r.success_count for r in self.results)
        return (successful / total_results) * 100
