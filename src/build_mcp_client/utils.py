import logging
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: str = None) -> logging.Logger:
    """
    Set up logging for the MCP client.
    
    Args:
        log_dir: Optional directory for log files. Defaults to _logs directory in project root.
    
    Returns:
        Logger instance configured for safe MCP usage
    """
    logger = logging.getLogger('mcp_client')
    logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Always log to stderr to avoid interfering with stdout used by MCP
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)
    
    # Set up file logging with timestamp in filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = Path('C:/Users/kevin/repos/build_mcp_client/_logs') / f'mcp_client_{timestamp}.log'
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized. Log file: {log_path}")
    
    return logger