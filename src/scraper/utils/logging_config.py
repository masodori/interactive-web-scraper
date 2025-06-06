# src/scraper/utils/logging_config.py
"""
Centralized logging configuration for the scraper application.
"""

import logging
import logging.config
from pathlib import Path

from ..config import Config


def setup_logging(log_level: int = logging.INFO):
    """
    Configures logging for the entire application using settings from the
    main Config class.

    It sets up a main 'scraper' logger with two handlers:
    1.  A console handler for INFO-level messages.
    2.  A rotating file handler for DEBUG-level messages, which are saved
        to the 'logs' directory.

    Args:
        log_level: The logging level for the console handler.
    """
    log_config = Config.LOGGING_CONFIG

    # Ensure the logs directory exists
    log_dir = Config.LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set the filename for the file handler dynamically
    log_file_path = log_dir / 'scraper.log'
    log_config['handlers']['file']['filename'] = str(log_file_path)

    # Apply the configuration
    logging.config.dictConfig(log_config)

    # Get the main scraper logger and set its level
    logger = logging.getLogger('scraper')
    logger.setLevel(log_level)

    logger.info("Logging configured successfully.")