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

    async def initialize(self) -> bool:
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
            self.capability_analysis = await self.llm.analyze_capabilities(self.capabilities)

            # Initialize database
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
        print("\nDiscovered Capabilities:")
        print(f"- Tools: {len(self.capabilities.get('tools', []))}")
        print(f"- Resources: {len(self.capabilities.get('resources', []))}")
        print(f"- Prompts: {len(self.capabilities.get('prompts', []))}")

        while True:
            try:
                command = input("\n> ").strip()
                if not command:
                    continue

                # Parse command and arguments
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                # Execute command
                if cmd in self.commands:
                    handler, _ = self.commands[cmd]
                    if cmd == 'quit':
                        if await handler(args):
                            break
                    else:
                        await handler(args)
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

    async def show_help(self, args: str = ""):
        """Display available commands."""
        print("\nAvailable Commands:")
        for cmd, (_, desc) in self.commands.items():
            print(f"  {cmd:<12} - {desc}")

    async def show_capabilities(self, args: str = ""):
        """Display available MCP capabilities."""
        print("\nAvailable Capabilities:")
        
        print("\nTools:")
        for tool in self.capabilities.get('tools', []):
            print(f"\n{tool['name']}:")
            print(f"  Description: {tool['description']}")
            if tool.get('schema'):
                print("  Parameters:")
                for param, details in tool['schema'].get('properties', {}).items():
                    print(f"    - {param}: {details.get('description', 'No description')}")

        print("\nResources:")
        for resource in self.capabilities.get('resources', []):
            print(f"\n{resource['name']}:")
            print(f"  URI: {resource['uri']}")
            print(f"  Description: {resource['description']}")

        print("\nPrompts:")
        for prompt in self.capabilities.get('prompts', []):
            print(f"\n{prompt['name']}:")
            print(f"  Description: {prompt['description']}")
            if prompt.get('arguments'):
                print("  Arguments:")
                for arg in prompt['arguments']:
                    print(f"    - {arg['name']}: {arg.get('description', 'No description')}")

        if self.capability_analysis:
            print("\nCapability Analysis:")
            print(self.capability_analysis)

    async def search(self, query: str):
        """Execute a research query using available capabilities."""
        if not query:
            print("\nError: Please provide a search query")
            return

        if not self.current_session_id:
            self.current_session_id = await self.db.create_session()

        try:
            print("\nPlanning research approach...")
            plan = await self.llm.plan_research(query, self.capabilities)
            
            print("\nExecuting research plan...")
            results = await self.llm.execute_research_plan(plan, self.client)
            
            print("\nAnalyzing results...")
            analysis = await self.llm.analyze_results(results)
            
            # Save results
            await self.db.save_research_results(
                self.current_session_id,
                query,
                results,
                analysis
            )
            
            print("\nResearch Results:")
            print(f"Steps completed: {results['metadata']['success_count']}")
            print(f"Steps failed: {results['metadata']['failure_count']}")
            
            print("\nKey Findings:")
            for finding in analysis.get('findings', []):
                print(f"- {finding}")
                
            if analysis.get('gaps'):
                print("\nInformation Gaps:")
                for gap in analysis['gaps']:
                    print(f"- {gap}")
                    
            if analysis.get('recommendations'):
                print("\nRecommended Next Steps:")
                for rec in analysis['recommendations']:
                    print(f"- {rec}")

        except Exception as e:
            logger.error(f"Research error: {e}")
            print(f"\nError performing research: {str(e)}")

    async def analyze(self, topic: str):
        """Analyze research results for a specific topic."""
        if not self.current_session_id:
            print("\nError: No active session to analyze")
            return

        if not topic:
            print("\nError: Please specify an analysis topic")
            return

        try:
            print("\nRetrieving session data...")
            session_data = await self.db.get_session_data(self.current_session_id)
            
            print("\nAnalyzing research data...")
            analysis = await self.llm.analyze_research(session_data, topic)
            
            await self.db.save_analysis(
                self.current_session_id,
                topic,
                analysis
            )
            
            print("\nAnalysis Results:")
            for section, content in analysis.items():
                if isinstance(content, list):
                    print(f"\n{section.title()}:")
                    for item in content:
                        print(f"- {item}")
                else:
                    print(f"\n{section.title()}: {content}")

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            print(f"\nError performing analysis: {str(e)}")

    async def save_results(self, args: str = ""):
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

    async def show_status(self, args: str = ""):
        """Display current session and capability status."""
        print("\nSystem Status:")
        print("MCP Capabilities:")
        print(f"- Tools: {len(self.capabilities.get('tools', []))}")
        print(f"- Resources: {len(self.capabilities.get('resources', []))}")
        print(f"- Prompts: {len(self.capabilities.get('prompts', []))}")

        if self.current_session_id:
            status = await self.db.get_session_status(self.current_session_id)
            print("\nCurrent Session:")
            print(f"Session ID: {self.current_session_id}")
            print(f"Queries: {status['query_count']}")
            print(f"Results: {status['result_count']}")
            print(f"Last Updated: {status['last_updated']}")
        else:
            print("\nNo active session")

    async def show_summary(self, args: str = ""):
        """Show research session summary."""
        if not self.current_session_id:
            print("\nNo active session")
            return

        try:
            summary = await self.db.get_session_summary(self.current_session_id)
            print("\nResearch Summary:")
            print(f"Total Queries: {summary['query_count']}")
            print(f"Successful Searches: {summary['successful_searches']}")
            print(f"Failed Searches: {summary['failed_searches']}")
            
            if summary.get('key_findings'):
                print("\nTop Findings:")
                for finding in summary['key_findings']:
                    print(f"- {finding}")
                    
            if summary.get('gaps'):
                print("\nIdentified Gaps:")
                for gap in summary['gaps']:
                    print(f"- {gap}")

        except Exception as e:
            logger.error(f"Summary error: {e}")
            print(f"\nError generating summary: {str(e)}")

    async def clear_session(self, args: str = ""):
        """Clear current session."""
        if not self.current_session_id:
            print("\nNo active session to clear")
            return

        confirm = input("\nThis will clear the current session. Continue? (y/n): ").lower()
        if confirm == 'y':
            self.current_session_id = None
            print("\nSession cleared")

    async def quit(self, args: str = "") -> bool:
        """Handle program exit."""
        if self.current_session_id:
            confirm = input("\nSave current session before quitting? (y/n): ").lower()
            if confirm == 'y':
                await self.save_results()
        return True

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