"""Command-line entry point for the ReliableData server."""

import logging

import click
import uvicorn
from rich.logging import RichHandler

# Logging levels in order from most to least verbose.
# Default is INFO (index 1).
_LEVELS = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
_DEFAULT_LEVEL_INDEX = 1  # INFO


def _display_host(host: str) -> str:
    if host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return host


def _configure_logging(verbosity: int) -> None:
    # Clamp index to valid range
    index = max(0, min(_DEFAULT_LEVEL_INDEX - verbosity, len(_LEVELS) - 1))
    level = _LEVELS[index]
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
    _configure_logging(verbosity - quietness)
    logger = logging.getLogger(__name__)
    display_host = _display_host(host)
    base_url = f"http://{display_host}:{port}"
    logger.info("Starting BlockCache server on %s:%d", host, port)
    logger.info("API: %s", base_url)
    logger.info("Interactive API docs: %s/docs", base_url)
    logger.info("ReDoc API docs: %s/redoc", base_url)
    uvicorn.run(
        "rd.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
