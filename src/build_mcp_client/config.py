# config.py

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """MCP server configuration settings."""
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    max_connections: int = 10
    timeout: int = 30
    pool_timeout: int = 30
    retry_limit: int = 3
    retry_timeout: int = 5

@dataclass
class Config:
    """Configuration settings for the MCP client."""
    # API Keys and URLs
    anthropic_api_key: str
    supabase_url: str
    supabase_key: str
    tavily_api_key: str
    
    # MCP Server Settings
    mcp_server: MCPServerConfig
    
    # Application Settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    max_retries: int = 3
    request_timeout: int = 30
    
    # Database Settings
    db_config: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    # File Paths
    log_dir: Path = field(default_factory=lambda: Path("_logs"))
    data_dir: Path = field(default_factory=lambda: Path("_data"))
    cache_dir: Path = field(default_factory=lambda: Path("_cache"))
    
    @classmethod
    def load_from_env(cls, env_file: str = ".env") -> 'Config':
        """
        Load configuration from environment variables.
        
        Args:
            env_file (str): Path to .env file
            
        Returns:
            Config: Configuration instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        # Load environment variables
        if Path(env_file).exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment from {env_file}")
        else:
            logger.warning(f".env file not found at {env_file}")
            
        # Check required variables
        required_vars = [
            'ANTHROPIC_API_KEY',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'TAVILY_API_KEY'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
            
        # Create directories
        log_dir = Path(os.getenv('LOG_DIR', '_logs'))
        data_dir = Path(os.getenv('DATA_DIR', '_data'))
        cache_dir = Path(os.getenv('CACHE_DIR', '_cache'))
        
        for directory in [log_dir, data_dir, cache_dir]:
            directory.mkdir(exist_ok=True)
            logger.debug(f"Created directory: {directory}")
        
        # Configure MCP server
        mcp_server = MCPServerConfig(
            command=os.getenv('MCP_COMMAND', 'npx'),
            args=os.getenv('MCP_ARGS', '-y tavily-mcp').split(),
            env={
                "TAVILY_API_KEY": os.getenv('TAVILY_API_KEY'),
                "NODE_ENV": os.getenv('NODE_ENV', 'production')
            }
        )
        
        # Configure database
        db_config = DatabaseConfig(
            max_connections=int(os.getenv('DB_MAX_CONNECTIONS', '10')),
            timeout=int(os.getenv('DB_TIMEOUT', '30')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            retry_limit=int(os.getenv('DB_RETRY_LIMIT', '3')),
            retry_timeout=int(os.getenv('DB_RETRY_TIMEOUT', '5'))
        )
        
        return cls(
            # API Keys and URLs
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_key=os.getenv('SUPABASE_KEY'),
            tavily_api_key=os.getenv('TAVILY_API_KEY'),
            
            # MCP Server Settings
            mcp_server=mcp_server,
            
            # Application Settings
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE'),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30')),
            
            # Database Settings
            db_config=db_config,
            
            # File Paths
            log_dir=log_dir,
            data_dir=data_dir,
            cache_dir=cache_dir
        )
    
    def setup_logging(self):
        """Configure logging based on settings."""
        log_level = getattr(logging, self.log_level.upper())
        
        handlers = [logging.StreamHandler()]
        if self.log_file:
            log_path = self.log_dir / self.log_file
            handlers.append(logging.FileHandler(log_path))
            
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        logger.info(f"Logging configured at level {self.log_level}")
    
    def validate(self) -> bool:
        """
        Validate the configuration.
        
        Returns:
            bool: True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate API keys and URLs
        if not all([self.anthropic_api_key, self.supabase_url, 
                   self.supabase_key, self.tavily_api_key]):
            raise ValueError("Missing required API keys or URLs")
            
        # Validate numeric values
        if not all([
            self.max_retries > 0,
            self.request_timeout > 0,
            self.db_config.max_connections > 0,
            self.db_config.timeout > 0
        ]):
            raise ValueError("Invalid numeric configuration values")
            
        # Validate directories
        if not all([
            self.log_dir.exists(),
            self.data_dir.exists(),
            self.cache_dir.exists()
        ]):
            raise ValueError("Required directories do not exist")
            
        return True
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.
        
        Returns:
            dict: Configuration as dictionary with sensitive data redacted
        """
        return {
            'anthropic_api_key': '[REDACTED]',
            'supabase_url': self.supabase_url,
            'supabase_key': '[REDACTED]',
            'tavily_api_key': '[REDACTED]',
            'mcp_server': {
                'command': self.mcp_server.command,
                'args': self.mcp_server.args,
                'env': {k: '[REDACTED]' if 'key' in k.lower() else v 
                       for k, v in self.mcp_server.env.items()}
            },
            'log_level': self.log_level,
            'log_file': str(self.log_file) if self.log_file else None,
            'max_retries': self.max_retries,
            'request_timeout': self.request_timeout,
            'db_config': {
                'max_connections': self.db_config.max_connections,
                'timeout': self.db_config.timeout,
                'pool_timeout': self.db_config.pool_timeout,
                'retry_limit': self.db_config.retry_limit,
                'retry_timeout': self.db_config.retry_timeout
            },
            'log_dir': str(self.log_dir),
            'data_dir': str(self.data_dir),
            'cache_dir': str(self.cache_dir)
        }