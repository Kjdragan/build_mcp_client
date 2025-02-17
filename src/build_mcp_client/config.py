# client.py
import os
import logging
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
    async def connect_to_tavily(self):
        """Connect to the Tavily MCP server with detailed error handling"""
        try:
            logger.debug("Attempting to connect to Tavily MCP server...")
            
            # Use npx to run the Tavily MCP server
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "tavily-mcp"],
                env={"TAVILY_API_KEY": os.getenv("TAVILY_API_KEY")}
            )
            
            logger.debug(f"Server parameters configured: {server_params}")
            
            # Create the transport
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            logger.debug("Transport created successfully")
            
            # Create and initialize the session
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            logger.debug("Session created successfully")
            
            # Initialize the connection
            await self.session.initialize()
            logger.info("Successfully connected to Tavily MCP server")
            
            # List available tools
            tools = await self.session.list_tools()
            logger.info(f"Available tools: {[tool.name for tool in tools.tools]}")
            
        except FileNotFoundError as e:
            logger.error(f"Failed to find npx or Tavily MCP server: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Tavily MCP server: {e}")
            raise

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            try:
                await self.exit_stack.aclose()
                logger.info("Successfully cleaned up MCP client resources")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")