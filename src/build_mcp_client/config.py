from pathlib import Path
from dotenv import load_dotenv
import os
from typing import Dict, Optional

class Config:
    """Configuration manager for the MCP client."""
    
    _instance: Optional['Config'] = None
    _config: Dict[str, str] = {}
    
    def __new__(cls):
        """Implement singleton pattern to ensure only one config instance."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        env_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        required_vars = {
            'ANTHROPIC_API_KEY': 'API key for Claude/Anthropic',
            'SUPABASE_URL': 'Supabase project URL',
            'SUPABASE_KEY': 'Supabase API key',
            'TAVILY_API_KEY': 'Tavily API key'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                missing_vars.append(f"{var} ({description})")
            self._config[var.lower()] = value if value else ''
            
        if missing_vars:
            raise EnvironmentError(
                "Missing required environment variables:\n" + 
                "\n".join(f"- {var}" for var in missing_vars)
            )
    
    @property
    def anthropic_api_key(self) -> str:
        """Get the Anthropic API key."""
        return self._config['anthropic_api_key']
    
    @property
    def supabase_url(self) -> str:
        """Get the Supabase URL."""
        return self._config['supabase_url']
    
    @property
    def supabase_key(self) -> str:
        """Get the Supabase API key."""
        return self._config['supabase_key']
    
    @property
    def tavily_api_key(self) -> str:
        """Get the Tavily API key."""
        return self._config['tavily_api_key']