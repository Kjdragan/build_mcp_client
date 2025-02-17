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
        
    def initialize(self):
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
            self.create_tables()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
            
    def create_tables(self):
        """Create required database tables."""
        try:
            # For Supabase, we'll use raw SQL to create tables
            # This needs to be done through the Supabase dashboard or migration
            # as the Python client doesn't support DDL operations directly
            
            # Verify tables exist by attempting to select from them
            try:
                self.client.table('sessions').select("id").limit(1).execute()
                self.client.table('research').select("id").limit(1).execute()
                self.client.table('capabilities').select("id").limit(1).execute()
                logger.info("Database tables verified")
            except Exception as e:
                logger.error(f"Tables verification failed: {e}")
                raise Exception("Required tables do not exist. Please create them using the provided SQL script.")
            
        except Exception as e:
            logger.error(f"Failed to verify tables: {e}")
            raise

    def create_session(self, capabilities: Dict[str, Any]) -> str:
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
            session_data = {
                'capabilities': capabilities,
                'metadata': {
                    'start_time': datetime.now().isoformat(),
                    'tool_count': len(capabilities.get('tools', [])),
                    'resource_count': len(capabilities.get('resources', [])),
                    'prompt_count': len(capabilities.get('prompts', [])),
                    'status': 'active'
                }
            }
            
            result = self.client.table('sessions').insert(session_data).execute()
            
            if not result.data:
                raise Exception("Failed to create session - no data returned")
                
            session_id = result.data[0]['id']
            
            # Store individual capabilities
            for capability_type, items in capabilities.items():
                for item in items:
                    capability_data = {
                        'session_id': session_id,
                        'capability_type': capability_type,
                        'name': item.get('name'),
                        'description': item.get('description'),
                        'schema': item.get('schema'),
                        'metadata': {
                            k: v for k, v in item.items()
                            if k not in ['name', 'description', 'schema']
                        }
                    }
                    
                    self.client.table('capabilities').insert(capability_data).execute()
            
            logger.info(f"Created new session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    def save_research_results(
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
            research_data = {
                'session_id': session_id,
                'query': query,
                'plan': plan,
                'results': results,
                'analysis': analysis
            }
            
            self.client.table('research').insert(research_data).execute()
            
            # Get current session metadata
            session_result = self.client.table('sessions')\
                .select('metadata')\
                .eq('id', session_id)\
                .single()\
                .execute()
            
            if not session_result.data:
                raise Exception(f"Session {session_id} not found")
                
            current_metadata = session_result.data['metadata']
            
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
            self.client.table('sessions').update({
                'updated_at': datetime.now().isoformat(),
                'metadata': updated_metadata
            }).eq('id', session_id).execute()
            
            logger.info(f"Saved research results for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save research results: {e}")
            raise

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get research history for a session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            List[Dict[str, Any]]: List of research entries
            
        Raises:
            Exception: If retrieval fails
        """
        try:
            result = self.client.table('research')\
                .select('*')\
                .eq('session_id', session_id)\
                .order('created_at', desc=True)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            raise

    def get_session_data(self, session_id: str) -> Dict[str, Any]:
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
            session = self.client.table('sessions')\
                .select('*')\
                .eq('id', session_id)\
                .single()\
                .execute()
                
            # Get research results
            research = self.client.table('research')\
                .select('*')\
                .eq('session_id', session_id)\
                .order('created_at', desc=True)\
                .execute()
                
            # Get capabilities
            capabilities = self.client.table('capabilities')\
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

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
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
            session = self.client.table('sessions')\
                .select('metadata, capabilities, updated_at')\
                .eq('id', session_id)\
                .single()\
                .execute()
            
            metadata = session.data['metadata']
            capabilities = session.data['capabilities']
            
            return {
                'query_count': metadata.get('query_count', 0),
                'success_rate': (
                    metadata.get('successful_queries', 0) /
                    metadata.get('query_count', 1) * 100
                    if metadata.get('query_count', 0) > 0 else 0
                ),
                'last_update': session.data['updated_at'],
                'capabilities': {
                    'tools': len(capabilities.get('tools', [])),
                    'resources': len(capabilities.get('resources', [])),
                    'prompts': len(capabilities.get('prompts', []))
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            raise

    def save_session(self, session_id: str):
        """
        Save current session state.
        
        Args:
            session_id (str): Session identifier
            
        Raises:
            Exception: If save fails
        """
        try:
            # Get current metadata
            metadata_result = self.client.table('sessions')\
                .select('metadata')\
                .eq('id', session_id)\
                .execute()
            
            current_metadata = metadata_result.data[0]['metadata']
            updated_metadata = {
                **current_metadata,
                'last_saved': datetime.now().isoformat()
            }
            
            # Update session with new metadata
            self.client.table('sessions').update({
                'updated_at': datetime.now().isoformat(),
                'metadata': updated_metadata
            }).eq('id', session_id).execute()
            
            logger.info(f"Saved session state: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            raise

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            bool: True if session exists
        """
        try:
            result = self.client.table('sessions')\
                .select('id')\
                .eq('id', session_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to check session existence: {e}")
            return False

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
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
            session_data = self.get_session_data(session_id)
            
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

    def cleanup(self):
        """Clean up database resources."""
        try:
            # Supabase client doesn't require explicit cleanup
            logger.info("Database cleanup completed")
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            raise