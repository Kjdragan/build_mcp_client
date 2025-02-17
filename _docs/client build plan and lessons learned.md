# MCP Client Build Plan and Lessons Learned

## Project Overview

Building an LLM-orchestrated MCP client that integrates with Tavily search and Supabase storage, with Claude as the primary orchestrator for research sessions.

## Build Plan

### Phase 1: Initial Setup and Core Infrastructure 
- [x] Project structure established
- [x] Environment configuration
- [x] Basic MCP client implementation
- [x] Console interface foundation

### Phase 2: MCP Server Integration (Current)
- [x] Tavily MCP server connection
- [x] Tool discovery and execution
- [x] Error handling and retry logic
- [x] Server connection state management

### Phase 3: Database Layer
- [x] Supabase integration
- [x] Schema design
- [x] Session management
- [x] Result storage

### Phase 4: LLM Orchestration
- [x] Claude integration
- [x] Research flow management
- [x] Tool selection logic
- [x] Result analysis

### Phase 5: User Interface Enhancement
- [x] Advanced command processing
- [x] Progress feedback
- [x] Result visualization
- [x] Session management commands

## Lessons Learned

### Day 1 (2025-02-17)

#### Environment Setup
1. **Issue**: Initial connection to Tavily MCP server failed
   ```
   Fatal error: [WinError 2] The system cannot find the file specified
   ```
   - **Root Cause**: Missing proper Node.js/npx setup and error handling
   - **Solution**: Added comprehensive error handling and initialization checks
   - **Best Practice**: Always validate external dependencies during startup

2. **Project Structure**
   - Importance of separating concerns (client, LLM, database)
   - Benefits of using a modular approach for easier testing
   - Value of comprehensive logging from the start

3. **Documentation**
   - Created dedicated docs folder for tracking progress
   - Implementing documentation-driven development
   - Maintaining clear record of decisions and lessons

### Technical Insights

#### MCP Client Implementation
```python
# Key Pattern: Proper resource management
async def cleanup(self):
    """Clean up resources"""
    if self.session:
        try:
            await self.exit_stack.aclose()
            logger.info("Successfully cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
```

#### Best Practices Identified
1. **Error Handling**
   - Use specific exception types
   - Implement proper cleanup in finally blocks
   - Log errors with context

2. **Resource Management**
   - Use async context managers
   - Implement proper cleanup methods
   - Handle disconnections gracefully

3. **Configuration**
   - Use environment variables for sensitive data
   - Validate all required variables at startup
   - Provide clear error messages for missing config

## Architecture Decisions

### MCP Client Design
1. **Decision**: Use AsyncExitStack for resource management
   - **Context**: Need to manage multiple async resources
   - **Consequence**: Cleaner resource cleanup
   - **Trade-off**: Added complexity vs. robustness

2. **Decision**: Implement comprehensive logging
   - **Context**: Debug complex integrations
   - **Consequence**: Better troubleshooting
   - **Trade-off**: Performance impact vs. observability

### Database Integration
1. **Decision**: Use Supabase for storage
   - **Context**: Need for structured data storage
   - **Consequence**: SQL capabilities with modern API
   - **Trade-off**: External dependency vs. functionality

## Next Steps

### Immediate Priorities
1. Resolve Tavily MCP server connection
2. Implement robust error handling
3. Add session management
4. Enhance logging system

### Future Considerations
1. Performance optimization
2. Enhanced error recovery
3. Better user feedback
4. Result caching

## Questions to Address

1. How to handle long-running research sessions?
2. What's the best way to structure research results?
3. How to implement efficient result caching?
4. What metrics should we track for optimization?

## Appendix

### Project Structure
```
build_mcp_client/
├── .env
├── _logs/
├── docs/
│   └── client-build-plan-and-lessons-learned.md
├── src/
│   └── build_mcp_client/
│       ├── __init__.py
│       ├── client.py
│       ├── config.py
│       ├── console.py
│       ├── database.py
│       ├── llm.py
│       └── utils.py
```

### Key Dependencies
- mcp[cli]
- anthropic
- supabase
- python-dotenv
- httpx

### Environment Setup
Required environment variables:
```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
TAVILY_API_KEY=
```

## Contributing

When adding to this documentation:
1. Date all entries
2. Include context for decisions
3. Document both successes and failures
4. Add code examples where relevant
5. Update status of build plan items

## References

1. [MCP Documentation](https://modelcontextprotocol.io)
2. [Tavily API Documentation](https://docs.tavily.com)
3. [Supabase Documentation](https://supabase.com/docs)
4. [Anthropic Claude Documentation](https://docs.anthropic.com)

## Recent Changes and Lessons Learned

### MCP Client Implementation, Instructor Integration, and Async/Sync Handling

#### Architecture Overview

The build_mcp_client is designed to facilitate research tasks using Model Context Protocol (MCP) capabilities. It consists of three main components:

1. **LLM Orchestrator**: Manages interactions with Claude
2. **Database Manager**: Handles session and research data persistence
3. **MCP Client**: Interfaces with MCP-compatible tools

#### Key Design Decisions

### Synchronous vs Asynchronous Operations

Initially, we attempted to make everything asynchronous, but this led to several issues:

1. **LLM Conversation Flow**: The LLM's interactions are inherently sequential - each step depends on previous context. Making these async added unnecessary complexity.
2. **Database Operations**: While Supabase supports async operations, our use case doesn't benefit from concurrent database access.
3. **MCP Client**: The MCP transport layer (especially stdio) requires careful async context management.

**Solution**: 
- Keep MCP client async (required by the protocol)
- Make LLM and Database operations synchronous
- Use a small async runtime in the console to manage MCP lifecycle

#### Structured Output Handling

We evolved through several approaches for handling LLM outputs:

1. **Initial Approach**: Manual JSON parsing with error handling
   - Prone to errors
   - Required extensive cleanup of markdown formatting
   - Inconsistent output structures

2. **Current Approach**: Instructor with Pydantic models
   - Automatic validation
   - Type safety
   - Built-in retries
   - Clear data structures

Key Pydantic models:
```python
class CapabilityAnalysis(BaseModel):
    possible_tasks: List[str]
    combinations: List[str]
    limitations: List[str]
    best_practices: List[str]
    summary: str

class ResearchPlan(BaseModel):
    steps: List[ResearchStep]
    expected_outcomes: List[str]
    fallback_options: List[ResearchStep]

class ResearchAnalysis(BaseModel):
    findings: List[str]
    quality: ResearchQuality
    gaps: List[str]
    recommendations: List[str]
```

#### Database Design

Using Supabase with three main tables:

1. `sessions`: Tracks research sessions
   - UUID primary key
   - Capabilities snapshot
   - Session metadata

2. `research`: Stores research queries and results
   - Links to session
   - Stores query, plan, results, and analysis

3. `capabilities`: Tracks available tools and resources
   - Links to session
   - Stores capability metadata

#### Lessons Learned

1. **MCP Transport Handling**:
   - MCP's stdio transport requires careful lifecycle management
   - Use `anyio` task groups correctly
   - Keep transport operations in the same async context

2. **LLM Integration**:
   - Instructor simplifies structured output handling
   - Use `instructor.patch()` instead of `from_anthropic()`
   - Define clear Pydantic models for all structured data

3. **Error Handling**:
   - Provide meaningful fallbacks for LLM failures
   - Handle MCP transport errors gracefully
   - Keep database operations atomic

4. **Session Management**:
   - Store capabilities snapshot with each session
   - Track session metrics (success rate, query count)
   - Maintain clear session lifecycle

#### Best Practices

1. **MCP Client**:
   ```python
   # Initialize with proper cleanup
   async with stdio_client(params) as streams:
       async with ClientSession(streams[0], streams[1]) as session:
           await session.initialize()
   ```

2. **LLM Structured Output**:
   ```python
   # Use Instructor with Pydantic
   client = instructor.patch(anthropic)
   result = client.chat.completions.create(
       response_model=YourModel,
       messages=[...]
   )
   ```

3. **Database Operations**:
   ```python
   # Use synchronous operations with proper error handling
   try:
       result = self.client.table('table_name').select('*').execute()
   except Exception as e:
       logger.error(f"Database operation failed: {e}")
       raise
   ```

#### Future Improvements

1. **Caching Layer**:
   - Add caching for frequently accessed data
   - Implement result caching for identical queries

2. **Parallel Operations**:
   - Identify operations that can be parallelized
   - Implement batch processing for large datasets

3. **Enhanced Error Recovery**:
   - Add automatic retry mechanisms
   - Implement session recovery

4. **Monitoring and Metrics**:
   - Add detailed performance tracking
   - Implement query success metrics

#### Dependencies

- `instructor[anthropic]`: Structured output handling
- `supabase`: Database operations
- `mcp`: Model Context Protocol client
- `anthropic`: Claude API client

#### Environment Setup

Required environment variables:
```
ANTHROPIC_API_KEY=your_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
TAVILY_API_KEY=your_tavily_key
```

#### Running the Project

1. Create virtual environment:
   ```powershell
   uv venv
   ```

2. Install dependencies:
   ```powershell
   uv pip install -e .
   ```

3. Run the console:
   ```powershell
   uv run python -m build_mcp_client.console
   ```

### Build MCP Client - Implementation Notes and Lessons Learned

## Build Plan

### Phase 1: Initial Setup and Core Infrastructure 
- [x] Project structure established
- [x] Environment configuration
- [x] Basic MCP client implementation
- [x] Initial documentation

### Phase 2: MCP Server Integration
- [x] Tavily MCP server connection
- [x] Tool discovery and execution
- [x] Error handling and retry logic
- [x] Server connection state management

### Phase 3: Database Layer
- [x] Supabase integration
- [x] Schema design
- [x] Session management
- [x] Result storage

### Phase 4: LLM Orchestration
- [x] Claude integration
- [x] Research flow management
- [x] Tool selection logic
- [x] Result analysis

### Phase 5: User Interface Enhancement
- [x] Advanced command processing
- [x] Progress feedback
- [x] Result visualization
- [x] Session management commands

## Implementation Timeline and Lessons Learned

### Day 1 (2025-02-17 Morning)

#### Initial Implementation Approach

**Code Organization**
- Created basic project structure
- Implemented initial MCP client
- Added basic configuration handling

**Initial Challenges**
1. Import Structure Issues
   ```python
   # Initial incorrect approach
   from .config import Config  # Config didn't exist
   ```
   - Solution: Created proper Config class
   - Learning: Define clear class responsibilities early

2. Configuration Management
   ```python
   @dataclass
   class Config:
       """Configuration settings for the MCP client."""
       anthropic_api_key: str
       supabase_url: str
       supabase_key: str
       tavily_api_key: str
   ```
   - Learning: Using dataclasses provides better type safety

3. Error Handling Strategy
   - Added comprehensive error handling
   - Implemented proper cleanup
   - Added logging throughout

### Day 1 (2025-02-17 Afternoon)

#### Major Architecture Evolution

**Initial Async Approach** (Later Changed)
```python
async def search(self, query: str):
    result = await self.client.execute_tool(
        "tavily-search",  # Hardcoded tool
        {"query": query}
    )
```

**Dynamic Capability Discovery**
```python
# Evolution to dynamic approach
async def search(self, query: str):
    capabilities = await self.client.discover_capabilities()
    plan = await self.llm.plan_research(query, capabilities)
    results = await self.execute_plan(plan)
```

### Day 1 (2025-02-17 Evening) - Major Architecture Shift

#### Async to Sync Evolution

**Previous Approach** (Before 2025-02-17 15:00)
- Everything was async
- Complex error handling for async operations
- Difficult to maintain conversation context

**Current Approach** (After 2025-02-17 15:00)
1. **Simplified Architecture**
   - MCP Client: Remains async (protocol requirement)
   - LLM Orchestrator: Now sync
   - Database Manager: Now sync

2. **Structured Output Evolution**
   - Previous: Manual JSON parsing
   ```python
   # Old approach with manual JSON handling
   try:
       return json.loads(response.content[0].text)
   except json.JSONDecodeError:
       logger.error("Failed to parse JSON")
   ```

   - Current: Instructor with Pydantic
   ```python
   # New approach with Instructor
   client = instructor.patch(anthropic)
   result = client.chat.completions.create(
       response_model=YourModel,
       messages=[...]
   )
   ```

3. **New Pydantic Models**
   ```python
   class ResearchPlan(BaseModel):
       steps: List[ResearchStep]
       expected_outcomes: List[str]
       fallback_options: List[ResearchStep]
   ```

#### Database Evolution

**Initial Implementation**
- Direct async calls to Supabase
- Complex error handling
- No structured response types

**Current Implementation**
- Synchronous operations
- Structured data models
- Clear session management
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    capabilities JSONB,
    metadata JSONB
);
```

## Technical Insights and Best Practices

### Current Best Practices (as of 2025-02-17 Evening)

1. **MCP Transport Handling**
   ```python
   async with stdio_client(params) as streams:
       async with ClientSession(streams[0], streams[1]) as session:
           await session.initialize()
   ```

2. **LLM Integration**
   ```python
   # Use Instructor for structured outputs
   client = instructor.patch(anthropic)
   ```

3. **Error Handling**
   - Provide fallbacks for LLM failures
   - Handle transport errors gracefully
   - Keep database operations atomic

### Future Improvements Planned

1. **Caching Layer**
   - Add result caching
   - Implement capability caching

2. **Enhanced Error Recovery**
   - Add automatic retry mechanisms
   - Implement session recovery

3. **Monitoring**
   - Add performance tracking
   - Implement success metrics

## References and Resources

1. [Model Context Protocol Documentation](https://modelcontextprotocol.io)
2. [Instructor Documentation](https://instructor-ai.github.io)
3. [Supabase Documentation](https://supabase.com/docs)
4. [Anthropic Claude Documentation](https://docs.anthropic.com)

## Contributing

When adding to this documentation:
1. Add date stamps to all entries
2. Include code examples where relevant
3. Document both successes and failures
4. Update status of build plan items
5. Add context for technical decisions
6. When approaches change, keep old approaches documented with clear timestamps