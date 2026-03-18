"""Command-line entry point for the ReliableData server."""

import logging

import click
import uvicorn
from rich.logging import RichHandler

# Logging levels in order from most to least verbose.
# Default is INFO (index 1).
Levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
DefaultLevelIndex = 1  # INFO


def _displayHost(host: str) -> str:
    if host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return host


def _configureLogging(verbosity: int) -> None:
    # Clamp index to valid range
    index = max(0, min(DefaultLevelIndex - verbosity, len(Levels) - 1))
    level = Levels[index]
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


@click.group()
def main() -> None:
    """ReliableData command-line interface."""


@main.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (development).")
@click.option("-v", "verbosity", count=True, help="Increase verbosity (repeatable).")
@click.option("-q", "quietness", count=True, help="Decrease verbosity (repeatable).")
def cache(host: str, port: int, reload: bool, verbosity: int, quietness: int) -> None:
    """Start the ReliableData BlockCache REST server."""
    _configureLogging(verbosity - quietness)
    logger = logging.getLogger(__name__)
    displayHost = _displayHost(host)
    baseUrl = f"http://{displayHost}:{port}"
    logger.info("Starting BlockCache server on %s:%d", host, port)
    logger.info("API: %s", baseUrl)
    logger.info("Interactive API docs: %s/docs", baseUrl)
    logger.info("ReDoc API docs: %s/redoc", baseUrl)
    uvicorn.run(
        "rd.main:app",
        host=host,
        port=port,
        reload=reload,
    )

