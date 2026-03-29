"""
Structured logger using Rich for colourful, readable output.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

_THEME = Theme(
    {
        "info": "bold cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "step": "bold magenta",
    }
)

_console = Console(theme=_THEME, stderr=True)


def get_logger(name: str = "proposal_agent", level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(
            console=_console,
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


# Default logger for the whole package
log = get_logger()
