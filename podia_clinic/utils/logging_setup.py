"""Logging setup utilities."""

import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from ..config import Config


def setup_logging() -> Any:
    """
    Configure application logging.
    
    Returns:
        Logger instance configured for the application
    """
    # Create formatter
    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        mode='a',
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Create application logger
    app_log = logging.getLogger('AsistIA_V5')
    app_log.setLevel(getattr(logging, Config.LOG_LEVEL))
    app_log.addHandler(file_handler)
    app_log.info("=== SISTEMA ASISTIA V5 INICIADO ===")
    
    return app_log
