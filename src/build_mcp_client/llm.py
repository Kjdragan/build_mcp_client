# llm.py

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from anthropic import Anthropic
import instructor
from .models import (
    MCPCapability,
    MCPAction,
    MCPResult,
    ResearchPlan,
    ResearchResults,
    ResearchSession
)

logger = logging.getLogger(__name__)

class LLMOrchestrator:
    """Orchestrates LLM interactions with dynamic MCP capabilities."""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Anthropic API key is required")
            
        # Initialize Anthropic client with Instructor
        anthropic = Anthropic(api_key=api_key)
        self.client = instructor.from_anthropic(anthropic)
        self.current_session: Optional[ResearchSession] = None
        logger.info("LLM Orchestrator initialized")

    def analyze_capabilities(self, capabilities: Dict[str, List[Dict[str, Any]]]) -> List[MCPCapability]:
        """Analyze available MCP capabilities."""
        try:
            # Convert raw capabilities to MCPCapability objects
            mcp_capabilities = []
            for cap_type, items in capabilities.items():
                for item in items:
                    cap = MCPCapability(
                        name=item.get('name', ''),
                        capability_type=cap_type,
                        description=item.get('description', ''),
                        capability_schema=item.get('schema'),
                        metadata=item
                    )
                    mcp_capabilities.append(cap)

            # Have Claude analyze the capabilities
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze these MCP capabilities and explain how they could be used:

Available Capabilities:
{[cap.model_dump() for cap in mcp_capabilities]}

Create a research plan template that demonstrates how to effectively use these capabilities."""
                }]
            )
            
            return mcp_capabilities
            
        except Exception as e:
            logger.error(f"Capability analysis failed: {e}")
            return []

    def plan_research(self, query: str, capabilities: List[MCPCapability]) -> ResearchPlan:
        """Plan research using available capabilities."""
        try:
            # Have Claude create a research plan using available capabilities
            return self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Research query: {query}

Available MCP capabilities:
{[cap.model_dump() for cap in capabilities]}

Create a research plan that uses these capabilities effectively. Consider:
1. Which capabilities are most relevant
2. How to sequence the actions
3. What parameters to use
4. Potential fallback approaches"""
                }],
                response_model=ResearchPlan
            )
            
        except Exception as e:
            logger.error(f"Research planning failed: {e}")
            # Return a basic fallback plan using the first available capability
            if capabilities:
                cap = capabilities[0]
                return ResearchPlan(
                    actions=[
                        MCPAction(
                            capability=cap.name,
                            capability_type=cap.capability_type,
                            parameters={"query": query},
                            metadata={"fallback": True}
                        )
                    ],
                    expected_outcomes=["Basic search results"],
                    fallbacks=[],
                    metadata={"error": str(e)}
                )
            return ResearchPlan(
                actions=[],
                expected_outcomes=[],
                fallbacks=[],
                metadata={"error": str(e)}
            )

    def execute_research_plan(self, plan: ResearchPlan, mcp_client: Any) -> ResearchResults:
        """Execute a research plan using available capabilities."""
        results = ResearchResults(
            results=[],
            metadata={
                'start_time': datetime.now().isoformat(),
                'plan_id': id(plan)
            },
            errors=[]
        )
        
        try:
            for action in plan.actions:
                result = MCPResult(
                    capability=action.capability,
                    capability_type=action.capability_type,
                    success=False,
                    data=None,
                    metadata={
                        'start_time': datetime.now().isoformat(),
                        'parameters': action.parameters
                    },
                    timestamp=datetime.now().isoformat()
                )
                
                try:
                    if action.capability_type == 'tool':
                        data = mcp_client.execute_tool_sync(
                            action.capability,
                            action.parameters
                        )
                    elif action.capability_type == 'resource':
                        data = mcp_client.read_resource_sync(
                            action.parameters.get('uri')
                        )
                    elif action.capability_type == 'prompt':
                        data = mcp_client.get_prompt_sync(
                            action.capability,
                            action.parameters
                        )
                    else:
                        raise ValueError(f"Unknown capability type: {action.capability_type}")

                    result.success = True
                    result.data = data
                    
                except Exception as e:
                    result.success = False
                    result.error = str(e)
                    results.errors.append(str(e))
                    
                    # Try fallback if available
                    matching_fallbacks = [
                        f for f in plan.fallbacks 
                        if f.capability_type == action.capability_type and f.capability != action.capability
                    ]
                    
                    if matching_fallbacks:
                        try:
                            fallback = matching_fallbacks[0]
                            fallback_result = self.execute_fallback(
                                fallback,
                                mcp_client
                            )
                            result.data = fallback_result
                            result.success = True
                            result.metadata['used_fallback'] = True
                        except Exception as fallback_e:
                            result.error = f"{result.error}\nFallback error: {str(fallback_e)}"
                            results.errors.append(str(fallback_e))
                
                results.results.append(result)
                
            results.metadata['end_time'] = datetime.now().isoformat()
            return results
            
        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            results.errors.append(str(e))
            return results

    def analyze_results(self, results: ResearchResults) -> Dict[str, Any]:
        """Analyze research results."""
        try:
            # Have Claude analyze the results
            return self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze these research results:

Results:
{results.model_dump()}

Provide a detailed analysis including:
1. Key findings from successful actions
2. Impact of any failures
3. Quality of the data collected
4. Suggestions for improvement"""
                }],
                response_model=Dict[str, Any]
            )
            
        except Exception as e:
            logger.error(f"Results analysis failed: {e}")
            return {
                "error": str(e),
                "success_rate": f"{results.success_count}/{len(results.results)}",
                "findings": ["Analysis failed due to error"],
                "suggestions": ["Retry with simplified analysis"]
            }

    def execute_fallback(self, fallback: MCPAction, mcp_client: Any) -> Any:
        """Execute a fallback action."""
        if fallback.capability_type == 'tool':
            return mcp_client.execute_tool_sync(
                fallback.capability,
                fallback.parameters
            )
        elif fallback.capability_type == 'resource':
            return mcp_client.read_resource_sync(
                fallback.parameters.get('uri')
            )
        elif fallback.capability_type == 'prompt':
            return mcp_client.get_prompt_sync(
                fallback.capability,
                fallback.parameters
            )
        else:
            raise ValueError(f"Unknown capability type: {fallback.capability_type}")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current research session."""
        if self.current_session:
            return self.current_session.model_dump()
        return {}