# client.py

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPClient:
    """Dynamic MCP client implementation."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.capabilities: Dict[str, List[Dict[str, Any]]] = {
            'tools': [],
            'resources': [],
            'prompts': []
        }
        self.transport = None
        
    async def discover_capabilities(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover all available MCP capabilities."""
        if not self.session:
            raise ValueError("Client not initialized")
            
        try:
            # Discover tools
            tools_result = await self.session.list_tools()
            self.capabilities['tools'] = [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'schema': tool.inputSchema
                }
                for tool in tools_result.tools
            ]
            logger.info(f"Discovered {len(self.capabilities['tools'])} tools")

            # Discover resources
            try:
                resources_result = await self.session.list_resources()
                self.capabilities['resources'] = [
                    {
                        'uri': resource.uri,
                        'name': resource.name,
                        'description': resource.description,
                        'mime_type': resource.mimeType
                    }
                    for resource in resources_result.resources
                ]
                logger.info(f"Discovered {len(self.capabilities['resources'])} resources")
            except Exception as e:
                logger.debug(f"Resource discovery failed: {e}")

            # Discover prompts
            try:
                prompts_result = await self.session.list_prompts()
                self.capabilities['prompts'] = [
                    {
                        'name': prompt.name,
                        'description': prompt.description,
                        'arguments': prompt.arguments
                    }
                    for prompt in prompts_result.prompts
                ]
                logger.info(f"Discovered {len(self.capabilities['prompts'])} prompts")
            except Exception as e:
                logger.debug(f"Prompt discovery failed: {e}")

            return self.capabilities

        except Exception as e:
            logger.error(f"Capability discovery failed: {e}")
            raise

    async def connect_to_server(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """Connect to an MCP server."""
        try:
            logger.debug(f"Connecting to MCP server: {command} {' '.join(args)}")
            
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env or {}
            )
            
            self.transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            self.stdio, self.write = self.transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            await self.session.initialize()
            
            # Discover capabilities
            await self.discover_capabilities()
            
            logger.info("Successfully connected to MCP server")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with parameters."""
        if not self.session:
            raise ValueError("Client not initialized")
            
        tool = next(
            (t for t in self.capabilities['tools'] if t['name'] == tool_name),
            None
        )
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
            
        try:
            logger.debug(f"Executing tool {tool_name} with parameters: {parameters}")
            result = await self.session.call_tool(tool_name, parameters)
            
            return {
                'tool': tool_name,
                'parameters': parameters,
                'result': result.content,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        if not self.session:
            raise ValueError("Client not initialized")
            
        resource = next(
            (r for r in self.capabilities['resources'] if r['uri'] == uri),
            None
        )
        if not resource:
            raise ValueError(f"Resource not found: {uri}")
            
        try:
            logger.debug(f"Reading resource: {uri}")
            result = await self.session.read_resource(uri)
            
            return {
                'uri': uri,
                'content': result.content,
                'mime_type': resource['mime_type'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Resource read failed: {e}")
            raise

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a prompt with arguments."""
        if not self.session:
            raise ValueError("Client not initialized")
            
        prompt = next(
            (p for p in self.capabilities['prompts'] if p['name'] == prompt_name),
            None
        )
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_name}")
            
        try:
            logger.debug(f"Getting prompt {prompt_name} with arguments: {arguments}")
            result = await self.session.get_prompt(prompt_name, arguments)
            
            return {
                'prompt': prompt_name,
                'arguments': arguments,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Prompt execution failed: {e}")
            raise

    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.session:
                await self.exit_stack.aclose()
                logger.info("Cleaned up MCP client resources")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        return next(
            (t for t in self.capabilities['tools'] if t['name'] == tool_name),
            None
        )

    def get_resource_info(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific resource."""
        return next(
            (r for r in self.capabilities['resources'] if r['uri'] == uri),
            None
        )

    def get_prompt_info(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific prompt."""
        return next(
            (p for p in self.capabilities['prompts'] if p['name'] == prompt_name),
            None
        )