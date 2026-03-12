"""Production-grade logging configuration using loguru."""
import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# File logging with rotation
logger.add(
    log_dir / "app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="500 MB",  # Rotate when file reaches 500MB
    retention="7 days",  # Keep logs for 7 days
    compression="zip",  # Compress rotated logs
    level="INFO",
    enqueue=True,  # Asynchronous logging for better performance
)

# Error file logging
logger.add(
    log_dir / "error.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
    rotation="500 MB",
    retention="14 days",  # Keep error logs longer
    compression="zip",
    level="ERROR",
    enqueue=True,
)

# Console logging (for development/debugging)
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    enqueue=True,
)

# Add context binding for structured logging
logger.configure(
    extra={"request_id": None, "session_id": None}
)

__all__ = ["logger"]
