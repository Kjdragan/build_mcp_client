# llm.py

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class LLMOrchestrator:
    """Orchestrates LLM interactions with dynamic MCP capabilities."""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Anthropic API key is required")
            
        self.client = Anthropic(api_key=api_key)
        self.current_session: Dict[str, Any] = {}
        logger.info("LLM Orchestrator initialized")

    async def analyze_capabilities(self, capabilities: Dict[str, List[Dict[str, Any]]]) -> str:
        """Analyze available MCP capabilities."""
        try:
            capabilities_desc = json.dumps(capabilities, indent=2)
            
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze these MCP capabilities and summarize how they could be used for research:

Available Capabilities:
{capabilities_desc}

Explain:
1. What kinds of research tasks are possible
2. How the tools could be combined
3. Any limitations or gaps
4. Best practices for usage"""
                }]
            )
            
            # Extract text from the response content
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return "No capability analysis available"
            
        except Exception as e:
            logger.error(f"Capability analysis failed: {e}")
            raise

    async def plan_research(self, query: str, capabilities: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Plan research using available capabilities."""
        try:
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Research query: {query}

Available MCP capabilities:
{json.dumps(capabilities, indent=2)}

Create a research plan that:
1. Identifies which capabilities would be useful
2. Explains how to use them effectively
3. Specifies the order of operations
4. Includes any required parameters

Return the plan as JSON with:
- steps: Array of actions to take (tool/resource/prompt usage)
- parameters: Parameters for each step
- expected_outcomes: What each step should produce
- fallback_options: Alternative approaches if steps fail"""
                }]
            )
            
            # Parse JSON from the response text
            if response.content and len(response.content) > 0:
                try:
                    return json.loads(response.content[0].text)
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from response")
                    return {
                        "error": "Invalid JSON response",
                        "raw_response": response.content[0].text
                    }
            return {
                "error": "No response content available"
            }
            
        except Exception as e:
            logger.error(f"Research planning failed: {e}")
            raise

    async def execute_research_plan(self, plan: Dict[str, Any], mcp_client: Any) -> Dict[str, Any]:
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
            for step in plan.get('steps', []):
                step_result = {
                    'step': step,
                    'status': 'pending',
                    'start_time': datetime.now().isoformat()
                }
                
                try:
                    if step['type'] == 'tool':
                        result = await mcp_client.execute_tool(
                            step['name'],
                            step['parameters']
                        )
                        step_result['data'] = result
                        
                    elif step['type'] == 'resource':
                        result = await mcp_client.read_resource(
                            step['uri']
                        )
                        step_result['data'] = result
                        
                    elif step['type'] == 'prompt':
                        result = await mcp_client.get_prompt(
                            step['name'],
                            step['arguments']
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
                    if step.get('fallback'):
                        try:
                            fallback_result = await self.execute_fallback(
                                step['fallback'],
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

    async def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze research results."""
        try:
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze these research results:

Results:
{json.dumps(results, indent=2)}

Provide:
1. Key findings and insights
2. Success/failure analysis
3. Data quality assessment
4. Suggestions for improvement
5. Additional research needs

Format as JSON with:
- findings: Array of key findings
- quality: Data quality assessment
- gaps: Information gaps identified
- recommendations: Suggested next steps"""
                }]
            )
            
            # Parse JSON from the response text
            if response.content and len(response.content) > 0:
                try:
                    return json.loads(response.content[0].text)
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from response")
                    return {
                        "error": "Invalid JSON response",
                        "raw_response": response.content[0].text
                    }
            return {
                "error": "No response content available"
            }
            
        except Exception as e:
            logger.error(f"Results analysis failed: {e}")
            raise

    async def execute_fallback(self, fallback: Dict[str, Any], mcp_client: Any) -> Dict[str, Any]:
        """Execute fallback plan for failed steps."""
        try:
            if fallback['type'] == 'tool':
                return await mcp_client.execute_tool(
                    fallback['name'],
                    fallback['parameters']
                )
            elif fallback['type'] == 'resource':
                return await mcp_client.read_resource(
                    fallback['uri']
                )
            elif fallback['type'] == 'prompt':
                return await mcp_client.get_prompt(
                    fallback['name'],
                    fallback['arguments']
                )
            else:
                raise ValueError(f"Unknown fallback type: {fallback['type']}")
                
        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            raise

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