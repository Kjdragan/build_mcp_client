# database.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from supabase import create_client, Client
from .config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for research sessions."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.config: Optional[Config] = None
        
    async def initialize(self):
        """
        Initialize database connection and create tables.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            self.config = Config.load_from_env()
            self.client = create_client(
                self.config.supabase_url,
                self.config.supabase_key
            )
            
            # Create required tables
            await self.create_tables()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
            
    async def create_tables(self):
        """Create required database tables."""
        try:
            # Sessions table
            await self.client.table('sessions').execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
                    capabilities JSONB,
                    metadata JSONB
                )
            """)
            
            # Research table
            await self.client.table('research').execute("""
                CREATE TABLE IF NOT EXISTS research (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    session_id UUID REFERENCES sessions(id),
                    query TEXT,
                    plan JSONB,
                    results JSONB,
                    analysis JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
                )
            """)
            
            # Capabilities table
            await self.client.table('capabilities').execute("""
                CREATE TABLE IF NOT EXISTS capabilities (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    session_id UUID REFERENCES sessions(id),
                    capability_type TEXT,
                    name TEXT,
                    description TEXT,
                    schema JSONB,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
                )
            """)
            
            logger.info("Database tables created/verified")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def create_session(self, capabilities: Dict[str, Any]) -> str:
        """
        Create a new research session.
        
        Args:
            capabilities (Dict[str, Any]): Discovered MCP capabilities
            
        Returns:
            str: Session ID
            
        Raises:
            Exception: If session creation fails
        """
        try:
            result = await self.client.table('sessions').insert({
                'capabilities': capabilities,
                'metadata': {
                    'start_time': datetime.now().isoformat(),
                    'tool_count': len(capabilities.get('tools', [])),
                    'resource_count': len(capabilities.get('resources', [])),
                    'prompt_count': len(capabilities.get('prompts', [])),
                    'status': 'active'
                }
            }).execute()
            
            session_id = result.data[0]['id']
            
            # Store individual capabilities
            for capability_type, items in capabilities.items():
                for item in items:
                    await self.client.table('capabilities').insert({
                        'session_id': session_id,
                        'capability_type': capability_type,
                        'name': item.get('name'),
                        'description': item.get('description'),
                        'schema': item.get('schema'),
                        'metadata': {
                            k: v for k, v in item.items()
                            if k not in ['name', 'description', 'schema']
                        }
                    }).execute()
            
            logger.info(f"Created new session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def save_research_results(
        self,
        session_id: str,
        query: str,
        plan: Dict[str, Any],
        results: Dict[str, Any],
        analysis: Dict[str, Any]
    ):
        """
        Save research results.
        
        Args:
            session_id (str): Session identifier
            query (str): Research query
            plan (Dict[str, Any]): Research plan
            results (Dict[str, Any]): Research results
            analysis (Dict[str, Any]): Result analysis
            
        Raises:
            Exception: If save fails
        """
        try:
            # Save research entry
            await self.client.table('research').insert({
                'session_id': session_id,
                'query': query,
                'plan': plan,
                'results': results,
                'analysis': analysis
            }).execute()
            
            # Get current session metadata
            session = await self.client.table('sessions')\
                .select('metadata')\
                .eq('id', session_id)\
                .single()\
                .execute()
            
            current_metadata = session.data['metadata']
            
            # Update session metadata
            updated_metadata = {
                **current_metadata,
                'last_query': query,
                'last_query_time': datetime.now().isoformat(),
                'query_count': current_metadata.get('query_count', 0) + 1,
                'successful_queries': current_metadata.get('successful_queries', 0) + (
                    1 if not results.get('error') else 0
                ),
                'failed_queries': current_metadata.get('failed_queries', 0) + (
                    1 if results.get('error') else 0
                )
            }
            
            # Update session
            await self.client.table('sessions').update({
                'updated_at': datetime.now().isoformat(),
                'metadata': updated_metadata
            }).eq('id', session_id).execute()
            
            logger.info(f"Saved research results for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save research results: {e}")
            raise

    async def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Get all data for a session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Dict[str, Any]: Session data including:
                - capabilities
                - research results
                - analyses
                
        Raises:
            Exception: If retrieval fails
        """
        try:
            # Get session
            session = await self.client.table('sessions')\
                .select('*')\
                .eq('id', session_id)\
                .single()\
                .execute()
                
            # Get research results
            research = await self.client.table('research')\
                .select('*')\
                .eq('session_id', session_id)\
                .order('created_at.asc')\
                .execute()
                
            # Get capabilities
            capabilities = await self.client.table('capabilities')\
                .select('*')\
                .eq('session_id', session_id)\
                .execute()
                
            return {
                'session': session.data,
                'research': research.data,
                'capabilities': capabilities.data
            }
            
        except Exception as e:
            logger.error(f"Failed to get session data: {e}")
            raise

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session status.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Dict[str, Any]: Session status including:
                - query_count: Total queries
                - success_rate: Percentage of successful queries
                - last_update: Timestamp of last update
                - capabilities: Available capability counts
                
        Raises:
            Exception: If status retrieval fails
        """
        try:
            # Get session metadata
            session = await self.client.table('sessions')\
                .select('metadata, capabilities, updated_at')\
                .eq('id', session_id)\
                .single()\
                .execute()
            
            metadata = session.data['metadata']
            capabilities = session.data['capabilities']
            
            # Calculate success rate
            total_queries = metadata.get('query_count', 0)
            successful_queries = metadata.get('successful_queries', 0)
            success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0
            
            return {
                'query_count': total_queries,
                'successful_queries': successful_queries,
                'failed_queries': metadata.get('failed_queries', 0),
                'success_rate': round(success_rate, 2),
                'last_query': metadata.get('last_query'),
                'last_query_time': metadata.get('last_query_time'),
                'last_updated': session.data['updated_at'],
                'capabilities': {
                    'tools': len(capabilities.get('tools', [])),
                    'resources': len(capabilities.get('resources', [])),
                    'prompts': len(capabilities.get('prompts', []))
                },
                'status': metadata.get('status', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            raise

    async def save_session(self, session_id: str):
        """
        Save current session state.
        
        Args:
            session_id (str): Session identifier
            
        Raises:
            Exception: If save fails
        """
        try:
            # Update session metadata
            await self.client.table('sessions').update({
                'updated_at': datetime.now().isoformat(),
                'metadata': self.client.table('sessions')
                    .select('metadata')
                    .eq('id', session_id)
                    .execute()
                    .data[0]['metadata'] | {
                        'last_saved': datetime.now().isoformat()
                    }
            }).eq('id', session_id).execute()
            
            logger.info(f"Saved session state: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            raise

    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            bool: True if session exists
        """
        try:
            result = await self.client.table('sessions')\
                .select('id')\
                .eq('id', session_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to check session existence: {e}")
            return False

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of session research.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Dict[str, Any]: Session summary including:
                - query_count: Total queries
                - success_metrics: Success/failure statistics
                - top_findings: Most significant findings
                - capabilities_used: Tools and resources used
                
        Raises:
            Exception: If summary generation fails
        """
        try:
            # Get session data
            session_data = await self.get_session_data(session_id)
            
            # Get research statistics
            research_data = session_data['research']
            total_queries = len(research_data)
            successful_queries = sum(1 for r in research_data if not r['results'].get('error'))
            
            # Get capability usage
            capabilities_used = set()
            for research in research_data:
                for step in research['results'].get('steps', []):
                    if step.get('type') in ['tool', 'resource', 'prompt']:
                        capabilities_used.add(f"{step['type']}:{step.get('name')}")
            
            # Get top findings
            findings = []
            for research in research_data:
                findings.extend(research['analysis'].get('findings', []))
            
            return {
                'query_count': total_queries,
                'success_metrics': {
                    'successful_queries': successful_queries,
                    'failed_queries': total_queries - successful_queries,
                    'success_rate': round(successful_queries / total_queries * 100, 2) if total_queries > 0 else 0
                },
                'capabilities_used': list(capabilities_used),
                'top_findings': findings[:10] if findings else [],
                'session_duration': (
                    datetime.fromisoformat(session_data['session']['updated_at']) -
                    datetime.fromisoformat(session_data['session']['created_at'])
                ).total_seconds() / 3600  # Duration in hours
            }
            
        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
            raise

    async def cleanup(self):
        """Clean up database resources."""
        try:
            # Implement any necessary cleanup
            # Currently a placeholder as the Supabase client handles most cleanup
            logger.info("Database cleanup completed")
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            raise