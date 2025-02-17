# console.py

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
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
        logging.FileHandler(
            Path('_logs') / f'console_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
    ]
)
logger = logging.getLogger(__name__)

class ResearchConsole:
    """Interactive console for dynamic MCP-based research."""
    
    def __init__(self):
        """Initialize the research console."""
        self.client: Optional[MCPClient] = None
        self.llm: Optional[LLMOrchestrator] = None
        self.db: Optional[DatabaseManager] = None
        self.current_session_id: Optional[str] = None
        self.capabilities: Dict[str, Any] = {}
        self.capability_analysis: Optional[str] = None
        
        # Command definitions
        self.commands = {
            'help': (self.show_help, 'Show this help message'),
            'quit': (self.quit, 'Exit the program'),
            'status': (self.show_status, 'Show current session status'),
            'capabilities': (self.show_capabilities, 'Show available MCP capabilities'),
            'search': (self.search, 'Perform a research search'),
            'analyze': (self.analyze, 'Analyze collected research'),
            'save': (self.save_results, 'Save current session'),
            'load': (self.load_session, 'Load a previous session'),
            'clear': (self.clear_session, 'Clear current session'),
            'summary': (self.show_summary, 'Show research summary')
        }

    async def async_initialize(self) -> bool:
        """Initialize components and discover capabilities."""
        try:
            # Load environment variables
            load_dotenv()
            required_vars = [
                'ANTHROPIC_API_KEY',
                'SUPABASE_URL',
                'SUPABASE_KEY',
                'TAVILY_API_KEY'
            ]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

            # Create required directories
            Path('_logs').mkdir(exist_ok=True)
            Path('_data').mkdir(exist_ok=True)

            # Initialize components
            logger.info("Initializing components...")
            self.client = MCPClient()
            self.llm = LLMOrchestrator(api_key=os.getenv('ANTHROPIC_API_KEY'))
            self.db = DatabaseManager()

            # Connect to MCP server and discover capabilities
            logger.info("Connecting to MCP server...")
            await self.client.connect_to_server(
                command="node",
                env={"TAVILY_API_KEY": os.getenv('TAVILY_API_KEY')}
            )

            # Discover and analyze capabilities
            self.capabilities = await self.client.discover_capabilities()
            self.capability_analysis = self.llm.analyze_capabilities(self.capabilities)

            # Initialize database
            logger.info("Connecting to database...")
            self.db.initialize()

            # Create initial session
            self.current_session_id = self.db.create_session(self.capabilities)

            logger.info("Initialization complete")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def async_cleanup(self):
        """Clean up resources."""
        try:
            if self.client:
                await self.client.cleanup()
            if self.db:
                self.db.cleanup()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def run(self):
        """Run the main console loop."""
        async def async_run():
            try:
                if not await self.async_initialize():
                    return
                    
                print("\nResearch Console Initialized")
                print("Type 'help' for available commands")
                
                while True:
                    try:
                        command = input("\nEnter command: ").strip().lower()
                        
                        if not command:
                            continue
                            
                        if command in self.commands:
                            self.commands[command][0]()
                        else:
                            print(f"Unknown command: {command}")
                            print("Type 'help' for available commands")
                            
                    except KeyboardInterrupt:
                        print("\nUse 'quit' to exit")
                    except Exception as e:
                        logger.error(f"Command execution failed: {e}")
                        print(f"Error: {e}")
                        
            finally:
                await self.async_cleanup()

        # Run the async event loop
        asyncio.run(async_run())

    def show_help(self):
        """Show available commands."""
        print("\nAvailable commands:")
        for cmd, (_, desc) in self.commands.items():
            print(f"  {cmd:12} - {desc}")

    def quit(self):
        """Exit the program."""
        print("\nExiting...")
        sys.exit(0)

    def show_status(self):
        """Show current session status."""
        if not self.current_session_id:
            print("No active session")
            return
            
        try:
            status = self.db.get_session_status(self.current_session_id)
            print("\nCurrent Session Status:")
            print(f"  Queries: {status['query_count']}")
            print(f"  Success Rate: {status['success_rate']}%")
            print(f"  Last Update: {status['last_update']}")
            print("\nAvailable Capabilities:")
            print(f"  Tools: {status['capabilities']['tools']}")
            print(f"  Resources: {status['capabilities']['resources']}")
            print(f"  Prompts: {status['capabilities']['prompts']}")
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            print("Error retrieving status")

    def show_capabilities(self):
        """Show available MCP capabilities."""
        if not self.capabilities:
            print("No capabilities discovered")
            return
            
        print("\nAvailable Capabilities:")
        print("\nTools:")
        for tool in self.capabilities['tools']:
            print(f"  {tool['name']}")
            print(f"    {tool['description']}")
            
        if self.capabilities['resources']:
            print("\nResources:")
            for resource in self.capabilities['resources']:
                print(f"  {resource['name']}")
                print(f"    {resource['description']}")
                
        if self.capabilities['prompts']:
            print("\nPrompts:")
            for prompt in self.capabilities['prompts']:
                print(f"  {prompt['name']}")
                print(f"    {prompt['description']}")

    def search(self):
        """Perform a research search."""
        if not self.current_session_id:
            print("No active session")
            return
            
        query = input("Enter search query: ").strip()
        if not query:
            print("Empty query")
            return
            
        try:
            # Plan research
            plan = self.llm.plan_research(query, self.capabilities)
            
            # Execute plan
            results = self.llm.execute_research_plan(plan, self.client)
            
            # Analyze results
            analysis = self.llm.analyze_results(results)
            
            # Save results
            self.db.save_research_results(
                self.current_session_id,
                query,
                plan,
                results,
                analysis
            )
            
            # Show summary
            print("\nSearch Results:")
            if 'findings' in analysis:
                print("\nKey Findings:")
                for finding in analysis['findings']:
                    print(f"  - {finding}")
                    
            if 'recommendations' in analysis:
                print("\nRecommendations:")
                for rec in analysis['recommendations']:
                    print(f"  - {rec}")
                    
        except Exception as e:
            logger.error(f"Search failed: {e}")
            print(f"Error: {e}")

    def analyze(self):
        """Analyze collected research."""
        if not self.current_session_id:
            print("No active session")
            return
            
        try:
            data = self.db.get_session_data(self.current_session_id)
            
            print("\nResearch Analysis:")
            print(f"Total Queries: {len(data['research'])}")
            
            if data['research']:
                print("\nRecent Queries:")
                for entry in data['research'][:5]:
                    print(f"\n{entry['query']}")
                    if 'findings' in entry['analysis']:
                        print("Findings:")
                        for finding in entry['analysis']['findings']:
                            print(f"  - {finding}")
                            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            print(f"Error: {e}")

    def save_results(self):
        """Save current session."""
        if not self.current_session_id:
            print("No active session")
            return
            
        try:
            self.db.save_session(self.current_session_id)
            print("Session saved successfully")
        except Exception as e:
            logger.error(f"Save failed: {e}")
            print(f"Error: {e}")

    def load_session(self):
        """Load a previous session."""
        session_id = input("Enter session ID: ").strip()
        if not session_id:
            print("Empty session ID")
            return
            
        try:
            if not self.db.session_exists(session_id):
                print("Session not found")
                return
                
            self.current_session_id = session_id
            print("Session loaded successfully")
            
        except Exception as e:
            logger.error(f"Load failed: {e}")
            print(f"Error: {e}")

    def clear_session(self):
        """Clear current session."""
        self.current_session_id = None
        print("Session cleared")

    def show_summary(self):
        """Show research summary."""
        if not self.current_session_id:
            print("No active session")
            return
            
        try:
            summary = self.db.get_session_summary(self.current_session_id)
            
            print("\nSession Summary:")
            print(f"Total Queries: {summary['query_count']}")
            print(f"Success Rate: {summary['success_rate']}%")
            
            if summary.get('top_findings'):
                print("\nKey Findings:")
                for finding in summary['top_findings']:
                    print(f"  - {finding}")
                    
            if summary.get('recommendations'):
                print("\nRecommendations:")
                for rec in summary['recommendations']:
                    print(f"  - {rec}")
                    
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            print(f"Error: {e}")

def main():
    """Main entry point for the research console."""
    print("\nInitializing Research Console...")
    console = ResearchConsole()
    console.run()

if __name__ == "__main__":
    main()