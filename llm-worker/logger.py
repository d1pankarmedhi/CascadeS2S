import logging
import sys
from typing import Optional


def setup_logger(name: str, log_level: Optional[str] = None) -> logging.Logger:
    """
    Setup and configure a logger instance.

    Args:
        name: The name of the logger
        log_level: Optional log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Defaults to INFO if not specified

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)

    # Set log level
    level = getattr(logging, (log_level or "INFO").upper())
    logger.setLevel(level)

    # Create console handler and set level
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add formatter to handler
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger
