#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path
import json
from dotenv import load_dotenv

from .client import MCPClient
from .llm import LLMOrchestrator
from .database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path('_logs') / f'console_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class ResearchConsole:
    def __init__(self):
        """Initialize the research console with MCP client and LLM orchestration."""
        self.client: Optional[MCPClient] = None
        self.llm: Optional[LLMOrchestrator] = None
        self.db: Optional[DatabaseManager] = None
        self.current_session_id: Optional[str] = None
        self.commands = {
            'help': self.show_help,
            'quit': self.quit,
            'status': self.show_status,
            'tools': self.list_tools,
            'search': self.search,
            'analyze': self.analyze,
            'save': self.save_results,
            'load': self.load_session,
            'clear': self.clear_session,
        }

    async def initialize(self):
        """Initialize all components and connections."""
        try:
            # Load environment variables
            load_dotenv()
            required_vars = ['ANTHROPIC_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY', 'TAVILY_API_KEY']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

            # Create logs directory if it doesn't exist
            Path('_logs').mkdir(exist_ok=True)

            # Initialize components
            logger.info("Initializing components...")
            self.client = MCPClient()
            self.llm = LLMOrchestrator()
            self.db = DatabaseManager()

            # Connect to Tavily MCP server
            logger.info("Connecting to Tavily MCP server...")
            await self.client.connect_to_tavily()

            # Initialize database connection
            logger.info("Connecting to database...")
            await self.db.initialize()

            logger.info("Initialization complete")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def run(self):
        """Main console loop."""
        print("\nResearch Console")
        print("Type 'help' for commands, 'quit' to exit")

        while True:
            try:
                command = input("\n> ").strip().lower()
                if not command:
                    continue

                # Parse command and arguments
                parts = command.split(maxsplit=1)
                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ""

                # Execute command
                if cmd in self.commands:
                    if cmd == 'quit':
                        if await self.commands[cmd]():
                            break
                    else:
                        await self.commands[cmd](args)
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                print(f"Error: {str(e)}")

    async def cleanup(self):
        """Clean up resources and connections."""
        try:
            if self.current_session_id:
                await self.save_results()

            if self.client:
                await self.client.cleanup()
            if self.db:
                await self.db.cleanup()
            
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def show_help(self, args=""):
        """Display available commands."""
        print("\nAvailable Commands:")
        print("  help              - Show this help message")
        print("  quit              - Exit the program")
        print("  status            - Show current session status")
        print("  tools             - List available MCP tools")
        print("  search <query>    - Perform a research search")
        print("  analyze <topic>   - Analyze collected research")
        print("  save             - Save current session")
        print("  load <session_id> - Load a previous session")
        print("  clear            - Clear current session")

    async def quit(self, args=""):
        """Handle program exit."""
        confirm = input("\nSave current session before quitting? (y/n): ").lower()
        if confirm == 'y':
            await self.save_results()
        return True

    async def show_status(self, args=""):
        """Display current session status."""
        if not self.current_session_id:
            print("\nNo active session")
            return

        status = await self.db.get_session_status(self.current_session_id)
        print("\nCurrent Session Status:")
        print(f"Session ID: {self.current_session_id}")
        print(f"Queries: {status['query_count']}")
        print(f"Results: {status['result_count']}")
        print(f"Last Updated: {status['last_updated']}")

    async def list_tools(self, args=""):
        """List available MCP tools."""
        if not self.client or not self.client.session:
            print("\nError: Not connected to MCP server")
            return

        tools = await self.client.session.list_tools()
        print("\nAvailable Tools:")
        for tool in tools.tools:
            print(f"\n{tool.name}:")
            print(f"  Description: {tool.description}")
            if tool.inputSchema:
                print("  Parameters:")
                for param, details in tool.inputSchema.get("properties", {}).items():
                    print(f"    - {param}: {details.get('description', 'No description')}")

    async def search(self, query: str):
        """Perform a research search."""
        if not query:
            print("\nError: Please provide a search query")
            return

        if not self.current_session_id:
            self.current_session_id = await self.db.create_session()

        try:
            print("\nProcessing search request...")
            result = await self.llm.process_search(self.client, query)
            
            # Save search results
            await self.db.save_search_results(
                self.current_session_id,
                query,
                result
            )
            
            print("\nSearch completed and results saved")
            print("\nKey Findings:")
            for idx, finding in enumerate(result.get('key_findings', []), 1):
                print(f"{idx}. {finding}")

        except Exception as e:
            logger.error(f"Search error: {e}")
            print(f"\nError performing search: {str(e)}")

    async def analyze(self, topic: str):
        """Analyze collected research."""
        if not self.current_session_id:
            print("\nError: No active session to analyze")
            return

        if not topic:
            print("\nError: Please specify an analysis topic")
            return

        try:
            print("\nPerforming analysis...")
            session_data = await self.db.get_session_data(self.current_session_id)
            analysis = await self.llm.analyze_research(session_data, topic)
            
            # Save analysis results
            await self.db.save_analysis(
                self.current_session_id,
                topic,
                analysis
            )
            
            print("\nAnalysis completed and saved")
            print("\nKey Insights:")
            for idx, insight in enumerate(analysis.get('insights', []), 1):
                print(f"{idx}. {insight}")

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            print(f"\nError performing analysis: {str(e)}")

    async def save_results(self, args=""):
        """Save current session results."""
        if not self.current_session_id:
            print("\nNo active session to save")
            return

        try:
            await self.db.save_session(self.current_session_id)
            print(f"\nSession {self.current_session_id} saved successfully")
        except Exception as e:
            logger.error(f"Save error: {e}")
            print(f"\nError saving session: {str(e)}")

    async def load_session(self, session_id: str):
        """Load a previous session."""
        if not session_id:
            print("\nError: Please provide a session ID")
            return

        try:
            if await self.db.session_exists(session_id):
                self.current_session_id = session_id
                print(f"\nLoaded session {session_id}")
                await self.show_status("")
            else:
                print(f"\nSession {session_id} not found")
        except Exception as e:
            logger.error(f"Load error: {e}")
            print(f"\nError loading session: {str(e)}")

    async def clear_session(self, args=""):
        """Clear current session."""
        if not self.current_session_id:
            print("\nNo active session to clear")
            return

        confirm = input("\nThis will clear the current session. Continue? (y/n): ").lower()
        if confirm == 'y':
            self.current_session_id = None
            print("\nSession cleared")

async def main():
    """Main entry point for the research console."""
    console = ResearchConsole()
    
    try:
        print("\nInitializing Research Console...")
        if await console.initialize():
            await console.run()
        else:
            print("\nInitialization failed. Please check logs for details.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\nFatal error: {str(e)}")
    finally:
        await console.cleanup()
        print("\nSession ended.")

if __name__ == "__main__":
    asyncio.run(main())