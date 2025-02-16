import asyncio
from typing import Optional
from mcp import StdioServerParameters
from datetime import datetime
from .client import MCPClient
from .database import DatabaseManager

async def interactive_session():
    """Run an interactive console session with the LLM-orchestrated MCP client."""
    
    print("\nInitializing MCP Client with LLM Orchestration...")
    print("(Type 'quit' to exit, 'help' for commands)")
    
    # Initialize client with logging
    async with MCPClient(log_dir="_logs") as client:
        print("\nConnecting to Tavily MCP server...")
        
        # Connect to Tavily server
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "tavily-mcp@0.1.3"],
            env={"TAVILY_API_KEY": client.config.tavily_api_key}
        )
        
        # Get server capabilities and tools
        server_info = await client.connect_to_server("tavily", server_params)
        
        print("\nConnection established!")
        print("\nAvailable commands:")
        print("  'research <topic>' - Start a new research session")
        print("  'analyze'         - Analyze stored results")
        print("  'help'            - Show this help message")
        print("  'quit'            - Exit the program")
        
        while True:
            try:
                # Get user input
                user_input = input("\n> ").strip()
                
                # Process commands
                if user_input.lower() == 'quit':
                    break
                    
                elif user_input.lower() == 'help':
                    print("\nCommands:")
                    print("  'research <topic>' - Start a new research session")
                    print("  'analyze'         - Analyze stored results")
                    print("  'help'            - Show this help message")
                    print("  'quit'            - Exit the program")
                    continue
                    
                elif user_input.lower() == 'analyze':
                    analysis_query = input("\nWhat would you like to analyze? ").strip()
                    if analysis_query:
                        print("\nAnalyzing data...")
                        result = await client.analyze_stored_results(analysis_query)
                        print("\nAnalysis Results:")
                        print(result)
                    continue
                    
                elif user_input.lower().startswith('research '):
                    topic = user_input[9:].strip()  # Remove 'research ' prefix
                    if not topic:
                        print("Please specify a research topic")
                        continue
                    user_input = f"I want to research the topic of {topic}. Please plan and conduct this research."
                
                # Process the query through the LLM orchestrator
                print("\nProcessing your request...")
                
                try:
                    result = await client.process_query(user_input)
                    print("\nResults:")
                    print(result)
                    
                    # Ask for follow-up
                    print("\nOptions:")
                    print("1. Continue with a follow-up question")
                    print("2. Start a new research topic")
                    print("3. Analyze the results")
                    print("4. Return to main menu")
                    
                    choice = input("\nWhat would you like to do? (1-4) ").strip()
                    
                    if choice == '1':
                        print("\nEnter your follow-up question:")
                    elif choice == '2':
                        print("\nEnter new research topic:")
                    elif choice == '3':
                        print("\nWhat aspect would you like to analyze?")
                    else:
                        continue
                        
                except Exception as e:
                    print(f"\nError processing query: {str(e)}")
                
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit properly.")
            except Exception as e:
                print(f"\nError: {str(e)}")

def main():
    """Entry point for the console interface."""
    try:
        asyncio.run(interactive_session())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
    finally:
        print("\nSession ended.")

if __name__ == "__main__":
    main()