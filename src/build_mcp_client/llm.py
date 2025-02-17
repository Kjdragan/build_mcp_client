# llm.py

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from anthropic import Anthropic
import instructor
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class CapabilityAnalysis(BaseModel):
    """Analysis of MCP capabilities."""
    possible_tasks: List[str] = Field(..., description="Research tasks that are possible")
    combinations: List[str] = Field(..., description="How tools can be combined")
    limitations: List[str] = Field(..., description="Limitations and gaps")
    best_practices: List[str] = Field(..., description="Best practices for usage")
    summary: str = Field(..., description="Overall summary of capabilities")

class ResearchStep(BaseModel):
    """A single step in a research plan."""
    type: str = Field(..., description="Type of step (tool, resource, prompt)")
    name: str = Field(..., description="Name of the capability to use")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the step")

class ResearchPlan(BaseModel):
    """A structured research plan."""
    steps: List[ResearchStep] = Field(..., description="Steps to execute")
    expected_outcomes: List[str] = Field(..., description="Expected outcomes from each step")
    fallback_options: List[ResearchStep] = Field(default_factory=list, description="Fallback steps if primary steps fail")

class ResearchQuality(BaseModel):
    """Quality assessment of research results."""
    score: int = Field(..., ge=0, le=100, description="Quality score from 0-100")
    assessment: str = Field(..., description="Brief quality assessment")

class ResearchAnalysis(BaseModel):
    """Analysis of research results."""
    findings: List[str] = Field(..., description="Key findings from the research")
    quality: ResearchQuality = Field(..., description="Quality assessment")
    gaps: List[str] = Field(..., description="Information gaps identified")
    recommendations: List[str] = Field(..., description="Recommended next steps")

class LLMOrchestrator:
    """Orchestrates LLM interactions with dynamic MCP capabilities."""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Anthropic API key is required")
            
        # Initialize Anthropic client with Instructor
        anthropic = Anthropic(api_key=api_key)
        self.client = instructor.from_anthropic(anthropic)
        self.current_session: Dict[str, Any] = {}
        logger.info("LLM Orchestrator initialized")

    def analyze_capabilities(self, capabilities: Dict[str, List[Dict[str, Any]]]) -> CapabilityAnalysis:
        """Analyze available MCP capabilities."""
        try:
            capabilities_desc = "\n".join([
                f"Tool: {tool['name']}\nDescription: {tool['description']}\n"
                for tool in capabilities.get('tools', [])
            ])
            
            return self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze these MCP capabilities and explain how they could be used for research:

Available Capabilities:
{capabilities_desc}

Provide a detailed analysis covering:
1. What research tasks are possible
2. How the tools could be combined
3. Any limitations or gaps
4. Best practices for usage"""
                }],
                response_model=CapabilityAnalysis
            )
            
        except Exception as e:
            logger.error(f"Capability analysis failed: {e}")
            return CapabilityAnalysis(
                possible_tasks=["Basic web search and content extraction"],
                combinations=["Search followed by detailed content analysis"],
                limitations=["Limited to web-based research"],
                best_practices=["Use focused search queries", "Validate extracted content"],
                summary="Basic web research capabilities available through Tavily integration"
            )

    def plan_research(self, query: str, capabilities: Dict[str, List[Dict[str, Any]]]) -> ResearchPlan:
        """Plan research using available capabilities."""
        try:
            # Create research plan using Instructor's structured output
            return self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Research query: {query}

Available MCP capabilities:
{str(capabilities)}

Create a research plan that uses these capabilities effectively."""
                }],
                response_model=ResearchPlan
            )
            
        except Exception as e:
            logger.error(f"Research planning failed: {e}")
            # Return a basic fallback plan
            return ResearchPlan(
                steps=[
                    ResearchStep(
                        type="tool",
                        name="tavily-search",
                        parameters={
                            "query": query,
                            "search_depth": "basic",
                            "max_results": 5
                        }
                    )
                ],
                expected_outcomes=["Basic search results for the query"],
                fallback_options=[]
            )

    def execute_research_plan(self, plan: ResearchPlan, mcp_client: Any) -> Dict[str, Any]:
        """Execute a research plan using available capabilities."""
        results = {
            'steps': [],
            'data': [],
            'metadata': {
                'start_time': datetime.now().isoformat(),
                'success_count': 0,
                'failure_count': 0
            }
        }
        
        try:
            for step in plan.steps:
                step_result = {
                    'step': step.model_dump(),  # Use Pydantic's model_dump
                    'status': 'pending',
                    'start_time': datetime.now().isoformat()
                }
                
                try:
                    if step.type == 'tool':
                        result = mcp_client.execute_tool_sync(
                            step.name,
                            step.parameters
                        )
                        step_result['data'] = result
                        
                    elif step.type == 'resource':
                        result = mcp_client.read_resource_sync(
                            step.parameters.get('uri')
                        )
                        step_result['data'] = result
                        
                    elif step.type == 'prompt':
                        result = mcp_client.get_prompt_sync(
                            step.name,
                            step.parameters
                        )
                        step_result['data'] = result
                        
                    step_result['status'] = 'completed'
                    step_result['end_time'] = datetime.now().isoformat()
                    results['metadata']['success_count'] += 1
                    
                except Exception as e:
                    step_result['status'] = 'failed'
                    step_result['error'] = str(e)
                    step_result['end_time'] = datetime.now().isoformat()
                    results['metadata']['failure_count'] += 1
                    
                    # Try fallback if available
                    matching_fallbacks = [
                        f for f in plan.fallback_options 
                        if f.type == step.type and f.name != step.name
                    ]
                    
                    if matching_fallbacks:
                        try:
                            fallback = matching_fallbacks[0]
                            fallback_result = self.execute_fallback(
                                fallback,
                                mcp_client
                            )
                            step_result['fallback_data'] = fallback_result
                            step_result['status'] = 'completed_with_fallback'
                        except Exception as fallback_e:
                            step_result['fallback_error'] = str(fallback_e)
                
                results['steps'].append(step_result)
                if step_result.get('data'):
                    results['data'].append(step_result['data'])
                
            results['metadata']['end_time'] = datetime.now().isoformat()
            return results
            
        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            raise

    def analyze_results(self, results: Dict[str, Any]) -> ResearchAnalysis:
        """Analyze research results."""
        try:
            # Analyze results using Instructor's structured output
            return self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze these research results:

Results:
{str(results)}

Provide a detailed analysis including key findings, quality assessment, gaps, and recommendations."""
                }],
                response_model=ResearchAnalysis
            )
            
        except Exception as e:
            logger.error(f"Results analysis failed: {e}")
            return ResearchAnalysis(
                findings=["Analysis failed due to an error"],
                quality=ResearchQuality(
                    score=0,
                    assessment="Analysis failed: " + str(e)
                ),
                gaps=["Complete analysis not available"],
                recommendations=["Retry analysis with simplified results"]
            )

    def execute_fallback(self, fallback: ResearchStep, mcp_client: Any) -> Any:
        """Execute a fallback action."""
        if fallback.type == 'tool':
            return mcp_client.execute_tool_sync(
                fallback.name,
                fallback.parameters
            )
        elif fallback.type == 'resource':
            return mcp_client.read_resource_sync(
                fallback.parameters.get('uri')
            )
        elif fallback.type == 'prompt':
            return mcp_client.get_prompt_sync(
                fallback.name,
                fallback.parameters
            )
        else:
            raise ValueError(f"Unknown fallback type: {fallback.type}")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current research session."""
        return {
            'query_count': len(self.current_session),
            'successful_queries': sum(
                1 for q in self.current_session.values()
                if q.get('status') == 'completed'
            ),
            'failed_queries': sum(
                1 for q in self.current_session.values()
                if q.get('status') == 'failed'
            ),
            'latest_query': max(
                (q.get('timestamp') for q in self.current_session.values()),
                default=None
            )
        }