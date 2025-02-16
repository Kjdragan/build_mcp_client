from typing import Optional, Dict, Any, List
import asyncio
from contextlib import AsyncExitStack
import json
from datetime import datetime
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from supabase import create_client, Client as SupabaseClient

from .config import Config
from .llm import LLMOrchestrator
from .database import DatabaseManager

class MCPClient:
    """
    MCP client implementation with LLM orchestration.
    Manages connections to MCP servers and coordinates research sessions.
    """
    
    def __init__(self, log_dir: str = None):
        """
        Initialize the MCP client with all required components.
        
        Args:
            log_dir: Optional directory for log files. If None, logs to stderr only.
        """
        self.logger = logging.getLogger('mcp_client')
        if log_dir:
            handler = logging.FileHandler(f"{log_dir}/mcp_client.log")
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
        
        self.config = Config()
        self.logger.info("Initializing MCP client")
        
        # Initialize components
        self.supabase: SupabaseClient = create_client(
            self.config.supabase_url,
            self.config.supabase_key
        )
        self.db_manager = DatabaseManager(self.supabase)
        self.llm = LLMOrchestrator(self.config.anthropic_api_key)
        
        # Session management
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.server_capabilities: Dict[str, Dict] = {}
        self.current_research_session_id: Optional[str] = None
        
    async def connect_to_server(self, server_name: str, server_params: StdioServerParameters) -> Dict[str, Any]:
        """
        Connect to an MCP server and discover its capabilities.
        
        Args:
            server_name: Identifier for this server connection
            server_params: Connection parameters for the server
            
        Returns:
            Dictionary containing discovered capabilities and tools
        """
        self.logger.info(f"Connecting to MCP server: {server_name}")
        
        try:
            # Create transport and session
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.sessions[server_name] = await self.exit_stack.enter_async_context(
                ClientSession(*stdio_transport)
            )
            
            # Initialize and discover capabilities
            init_result = await self.sessions[server_name].initialize()
            self.server_capabilities[server_name] = init_result.capabilities
            
            # Discover available tools
            tools_result = await self.sessions[server_name].list_tools()
            self.logger.info(f"Discovered {len(tools_result.tools)} tools for {server_name}")
            
            server_info = {
                'capabilities': self.server_capabilities[server_name],
                'tools': tools_result.tools,
                'resources': [],
                'prompts': []
            }
            
            # Discover available resources if supported
            if self.server_capabilities[server_name].get('resources'):
                resources_result = await self.sessions[server_name].list_resources()
                server_info['resources'] = resources_result.resources
                
            # Discover available prompts if supported
            if self.server_capabilities[server_name].get('prompts'):
                prompts_result = await self.sessions[server_name].list_prompts()
                server_info['prompts'] = prompts_result.prompts
                
            return server_info
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server {server_name}: {str(e)}")
            raise
            
    async def start_research_session(self, topic: str) -> str:
        """
        Start a new research session.
        
        Args:
            topic: The research topic
            
        Returns:
            Session ID
        """
        session_data = await self.supabase.table('research_sessions').insert({
            'topic': topic,
            'metadata': {
                'started_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
        }).execute()
        
        self.current_research_session_id = session_data.data[0]['id']
        return self.current_research_session_id
        
    async def process_query(self, user_query: str) -> str:
        """
        Process a user query using LLM orchestration.
        
        Args:
            user_query: The user's query
            
        Returns:
            Processed response
        """
        if not self.sessions:
            raise RuntimeError("No MCP servers connected. Connect to servers first.")
            
        # Store the query
        query_data = await self.supabase.table('research_queries').insert({
            'session_id': self.current_research_session_id,
            'query': user_query,
            'metadata': {
                'timestamp': datetime.utcnow().isoformat()
            }
        }).execute()
        
        query_id = query_data.data[0]['id']
        
        # Collect available tools from all connected servers
        available_tools = []
        for server_name, session in self.sessions.items():
            tools_result = await session.list_tools()
            available_tools.extend([{
                "name": f"{server_name}.{tool.name}",
                "description": tool.description,
                "input_schema": tool.inputSchema,
                "server": server_name
            } for tool in tools_result.tools])
            
        # Get recent results for context
        recent_results = None
        if self.current_research_session_id:
            results = await self.supabase.table('research_results')\
                .select('*')\
                .eq('query_id', query_id)\
                .order('timestamp', desc=True)\
                .limit(5)\
                .execute()
            
            if results.data:
                recent_results = "\n\n".join(
                    f"Previous result ({r['tool_name']}): {r['result_content'][:500]}..."
                    for r in results.data
                )
        
        # Let LLM orchestrate the processing
        response = await self.llm.process_user_input(
            user_query,
            available_tools,
            recent_results
        )
        
        # Store the final response
        await self.supabase.table('research_results').insert({
            'query_id': query_id,
            'server_name': 'llm',
            'tool_name': 'orchestrator',
            'result_content': response,
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'final_response'
            }
        }).execute()
        
        return response
        
    async def analyze_stored_results(self, analysis_query: str) -> str:
        """
        Analyze stored research results.
        
        Args:
            analysis_query: Query describing the analysis to perform
            
        Returns:
            Analysis results
        """
        if not self.current_research_session_id:
            raise ValueError("No active research session")
            
        # Get session results
        results = await self.supabase.table('complete_research_sessions')\
            .select('*')\
            .eq('session_id', self.current_research_session_id)\
            .execute()
            
        if not results.data:
            return "No results found to analyze."
            
        # Let LLM analyze the results
        analysis = await self.llm.analyze_stored_results(analysis_query)
        
        # Store the analysis
        await self.supabase.table('analysis_results').insert({
            'session_id': self.current_research_session_id,
            'analysis_query': analysis_query,
            'analysis_result': analysis,
            'metadata': {
                'timestamp': datetime.utcnow().isoformat()
            }
        }).execute()
        
        return analysis
        
    async def execute_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a specific tool on a server.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to execute
            args: Tool arguments
            
        Returns:
            Tool execution results
        """
        if server_name not in self.sessions:
            raise ValueError(f"Unknown server: {server_name}")
            
        result = await self.sessions[server_name].call_tool(tool_name, args)
        return result
        
    async def close(self):
        """Close all connections and clean up resources."""
        self.logger.info("Closing MCP client connections")
        
        if self.current_research_session_id:
            # Update session status
            await self.supabase.table('research_sessions')\
                .update({'metadata': {'status': 'completed'}})\
                .eq('id', self.current_research_session_id)\
                .execute()
        
        await self.exit_stack.aclose()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()