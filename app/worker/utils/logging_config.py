"""
Logging configuration for XMonitor Worker (Ported from XMonitor-Agent)
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
import sys


def setup_logging(
    config: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
    log_file: str = "logs/xmonitor.log",
    console: bool = True
):
    """
    Setup logging configuration

    Args:
        config: Application configuration (optional, overrides other params if provided)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        console: Whether to enable console logging
    """
    # Use config dict if provided, otherwise use direct parameters
    if config:
        log_config = config.get('logging', {})
        level = log_config.get('level', level).upper()
        log_file = log_config.get('file', log_file)
        console = log_config.get('console', console)
    else:
        level = level.upper()

    # Get numeric log level
    numeric_level = getattr(logging, level, logging.INFO)

    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler with colors
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    max_bytes = 50 * 1024 * 1024  # 50 MB
    backup_count = 5
    if config:
        log_config = config.get('logging', {})
        max_bytes = log_config.get('max_size_mb', 50) * 1024 * 1024
        backup_count = log_config.get('backup_count', 5)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(numeric_level)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Reduce noise from external libraries
    logging.getLogger('mistralai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)

    logger.info(f"Logging initialized: level={level}, file={log_file}")


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[1;31m' # Bold Red
    }
    RESET = '\033[0m'

    def format(self, record):
        # Make a copy to avoid modifying the original record (which affects file logs)
        record_copy = logging.makeLogRecord(record.__dict__)

        # Add color to level name in the copy only
        if record_copy.levelname in self.COLORS:
            record_copy.levelname = (
                f"{self.COLORS[record_copy.levelname]}"
                f"{record_copy.levelname}"
                f"{self.RESET}"
            )

        return super().format(record_copy)
