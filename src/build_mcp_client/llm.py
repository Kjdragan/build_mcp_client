from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
from datetime import datetime

from anthropic import AsyncAnthropic

@dataclass
class PlanStep:
    """Represents a step in the LLM's action plan."""
    action: str  # 'search', 'analyze', 'synthesize', 'clarify'
    description: str
    parameters: Dict[str, Any]

@dataclass
class ExecutionResult:
    """Results from executing a plan step."""
    success: bool
    content: str
    metadata: Dict[str, Any]

class LLMOrchestrator:
    """
    Orchestrates interactions between user, MCP tools, and database.
    Acts as the primary decision maker for all operations.
    """
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """Initialize the orchestrator with required clients."""
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.conversation_context: List[Dict[str, Any]] = []
        
    async def process_user_input(
        self,
        user_input: str,
        available_tools: List[Dict[str, Any]],
        recent_results: Optional[str] = None
    ) -> str:
        """
        Process user input and orchestrate necessary actions.
        
        Args:
            user_input: The user's query or command
            available_tools: List of available MCP tools
            recent_results: Optional recent search results
            
        Returns:
            Formatted response for user
        """
        # First, plan what actions to take
        plan = await self._create_action_plan(user_input, available_tools, recent_results)
        
        # Execute the plan
        results = []
        for step in plan:
            result = await self._execute_plan_step(step, available_tools)
            results.append(result)
            
        # Synthesize results into a coherent response
        final_response = await self._synthesize_results(user_input, results)
        
        return final_response
    
    async def _create_action_plan(
        self,
        user_input: str,
        available_tools: List[Dict[str, Any]],
        recent_results: Optional[str] = None
    ) -> List[PlanStep]:
        """Create a plan of actions to take based on user input."""
        
        # Construct prompt for planning
        tool_descriptions = "\n".join(
            f"- {tool['name']}: {tool['description']}"
            for tool in available_tools
        )
        
        context = f"""Available tools:\n{tool_descriptions}

Recent results: {recent_results if recent_results else 'None'}

Create a plan to address this user query: {user_input}

Response should be a JSON list of steps, each with:
- action: 'search' (use tavily tools), 'analyze' (analyze stored data), 'synthesize' (combine results), or 'clarify' (ask user for clarification)
- description: what this step will do
- parameters: specific parameters for the action"""
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": context
            }]
        )
        
        try:
            plan_data = json.loads(response.content[0].text)
            return [PlanStep(**step) for step in plan_data]
        except Exception as e:
            # Fallback to single search step if parsing fails
            return [PlanStep(
                action="search",
                description="Perform initial search based on user query",
                parameters={"query": user_input}
            )]
    
    async def _execute_plan_step(
        self,
        step: PlanStep,
        available_tools: List[Dict[str, Any]]
    ) -> ExecutionResult:
        """Execute a single step from the plan."""
        
        if step.action == "search":
            result = await self._execute_tool_step(step, available_tools)
        elif step.action == "analyze":
            result = await self._analyze_data(step)
        elif step.action == "synthesize":
            result = await self._synthesize_data(step)
        elif step.action == "clarify":
            result = ExecutionResult(
                success=True,
                content=step.description,
                metadata={"needs_clarification": True}
            )
        else:
            result = ExecutionResult(
                success=False,
                content=f"Unknown action: {step.action}",
                metadata={}
            )
            
        return result
    
    async def _execute_tool_step(
        self,
        step: PlanStep,
        available_tools: List[Dict[str, Any]]
    ) -> ExecutionResult:
        """Execute a tool-based step using MCP tools."""
        
        messages = [
            {
                "role": "user",
                "content": f"Execute this search: {step.parameters.get('query', '')}"
            }
        ]
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )
        
        tool_results = []
        for content in response.content:
            if content.type == 'tool_calls':
                for tool_call in content.tool_calls:
                    tool_results.append({
                        "tool": tool_call.name,
                        "parameters": tool_call.parameters
                    })
        
        return ExecutionResult(
            success=True,
            content=response.content[0].text,
            metadata={"tool_calls": tool_results}
        )
    
    async def _analyze_data(self, step: PlanStep) -> ExecutionResult:
        """Analyze stored data based on plan step."""
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert data analyst. Analyze the provided data and generate insights."
            },
            {
                "role": "user",
                "content": f"Analysis task: {step.description}\n\nParameters: {json.dumps(step.parameters)}"
            }
        ]
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=messages
        )
        
        return ExecutionResult(
            success=True,
            content=response.content[0].text,
            metadata={"analysis_type": step.parameters.get("type", "general")}
        )
    
    async def _synthesize_data(self, step: PlanStep) -> ExecutionResult:
        """Synthesize multiple results into coherent information."""
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert at synthesizing information into clear, coherent summaries."
            },
            {
                "role": "user",
                "content": f"Synthesize this information: {step.parameters.get('content', '')}"
            }
        ]
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=messages
        )
        
        return ExecutionResult(
            success=True,
            content=response.content[0].text,
            metadata={"synthesis_type": step.parameters.get("type", "general")}
        )
    
    async def _synthesize_results(
        self,
        original_query: str,
        results: List[ExecutionResult]
    ) -> str:
        """Create final response from all results."""
        
        # Compile results into a format for synthesis
        results_text = "\n\n".join(
            f"Step Result:\n{result.content}"
            for result in results
            if result.success
        )
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert at creating clear, helpful responses that accurately address user queries."
            },
            {
                "role": "user",
                "content": f"""Original query: {original_query}

Execution results:
{results_text}

Create a clear, coherent response that addresses the original query using these results.
Include relevant specific details but maintain clarity.
Suggest follow-up questions or areas for further investigation if appropriate."""
            }
        ]
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=messages
        )
        
        return response.content[0].text