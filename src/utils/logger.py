"""
Logging utilities for mov3 video automation engine.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from colorama import Fore, Back, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"

        # Format the message
        result = super().format(record)

        # Reset levelname for file handlers
        record.levelname = levelname

        return result


class Logger:
    """Centralized logger for the application."""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self, log_dir: str = "logs", log_level: str = "INFO"):
        """Setup the logger with console and file handlers."""

        # Create logs directory
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Create logger
        self._logger = logging.getLogger("mov3")
        self._logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Prevent duplicate handlers
        if self._logger.handlers:
            return

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColoredFormatter(
            '%(levelname)s | %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # File handler without colors
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            Path(log_dir) / f"mov3_{timestamp}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Add handlers
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """Get the logger instance."""
        return self._logger

    def set_level(self, level: str):
        """Set logging level."""
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    @staticmethod
    def debug(msg: str, *args, **kwargs):
        """Log debug message."""
        Logger()._logger.debug(msg, *args, **kwargs)

    @staticmethod
    def info(msg: str, *args, **kwargs):
        """Log info message."""
        Logger()._logger.info(msg, *args, **kwargs)

    @staticmethod
    def warning(msg: str, *args, **kwargs):
        """Log warning message."""
        Logger()._logger.warning(msg, *args, **kwargs)

    @staticmethod
    def error(msg: str, *args, **kwargs):
        """Log error message."""
        Logger()._logger.error(msg, *args, **kwargs)

    @staticmethod
    def critical(msg: str, *args, **kwargs):
        """Log critical message."""
        Logger()._logger.critical(msg, *args, **kwargs)

    @staticmethod
    def exception(msg: str, *args, **kwargs):
        """Log exception with traceback."""
        Logger()._logger.exception(msg, *args, **kwargs)


# Convenience functions
def get_logger() -> logging.Logger:
    """Get the logger instance."""
    return Logger().get_logger()


def setup_logger(log_dir: str = "logs", log_level: str = "INFO"):
    """Setup logger with custom settings."""
    logger = Logger()
    logger._setup_logger(log_dir, log_level)
    return logger.get_logger()


# Module-level convenience functions
debug = Logger.debug
info = Logger.info
warning = Logger.warning
error = Logger.error
critical = Logger.critical
exception = Logger.exception
