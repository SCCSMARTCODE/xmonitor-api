"""
Logging configuration for SafeX Worker (Ported from SafeX-Agent)
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any
import sys


def setup_logging(config: Dict[str, Any]):
    """
    Setup logging configuration

    Args:
        config: Application configuration
    """
    log_config = config.get('logging', {})

    # Get log level
    level_str = log_config.get('level', 'INFO').upper()
    level = getattr(logging, level_str, logging.INFO)

    # Create logs directory
    log_file = log_config.get('file', 'logs/safex-worker.log')
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler with colors
    if log_config.get('console', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    max_bytes = log_config.get('max_size_mb', 50) * 1024 * 1024
    backup_count = log_config.get('backup_count', 5)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
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

    logger.info(f"Logging initialized: level={level_str}, file={log_file}")


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
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.RESET}"
            )

        return super().format(record)
