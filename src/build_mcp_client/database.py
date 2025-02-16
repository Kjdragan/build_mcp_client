from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from dataclasses import dataclass

@dataclass
class SearchResult:
    """Structure for storing search results from MCP tools."""
    query: str
    tool_name: str
    server_name: str
    result_content: str
    metadata: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class DatabaseManager:
    """Manages Supabase database operations."""
    
    def __init__(self, supabase_client):
        """
        Initialize database manager.
        
        Args:
            supabase_client: Initialized Supabase client
        """
        self.supabase = supabase_client
        
    async def initialize_tables(self):
        """
        Initialize required tables if they don't exist.
        Creates tables for storing queries and results.
        """
        # Note: Supabase table creation is typically done through the dashboard
        # This method is for documentation purposes
        """
        Required table structure:
        
        CREATE TABLE IF NOT EXISTS mcp_queries (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            query TEXT NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB
        );
        
        CREATE TABLE IF NOT EXISTS mcp_results (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            query_id UUID REFERENCES mcp_queries(id),
            server_name TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            result_content TEXT NOT NULL,
            metadata JSONB,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        pass
        
    async def store_search_result(self, result: SearchResult) -> str:
        """
        Store a search result and its associated query.
        
        Args:
            result: SearchResult object containing query and result information
            
        Returns:
            ID of the stored result
        """
        # Store the query first
        query_response = await self.supabase.table('mcp_queries').insert({
            'query': result.query,
            'timestamp': result.timestamp.isoformat(),
            'metadata': result.metadata
        }).execute()
        
        # Get the query ID
        query_id = query_response.data[0]['id']
        
        # Store the result
        result_response = await self.supabase.table('mcp_results').insert({
            'query_id': query_id,
            'server_name': result.server_name,
            'tool_name': result.tool_name,
            'result_content': result.result_content,
            'metadata': result.metadata,
            'timestamp': result.timestamp.isoformat()
        }).execute()
        
        return result_response.data[0]['id']
        
    async def get_results_for_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve all results associated with a specific query.
        
        Args:
            query: The query string to search for
            
        Returns:
            List of result records
        """
        response = await self.supabase.table('mcp_queries')\
            .select('*, mcp_results(*)')\
            .eq('query', query)\
            .execute()
            
        return response.data
        
    async def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent queries and their results.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of query records with associated results
        """
        response = await self.supabase.table('mcp_queries')\
            .select('*, mcp_results(*)')\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
            
        return response.data