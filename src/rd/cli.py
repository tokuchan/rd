"""Command-line entry point for the ReliableData server."""

import logging

import click
import uvicorn
from rich.logging import RichHandler


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


@click.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (development).")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable debug logging.")
def main(host: str, port: int, reload: bool, verbose: bool) -> None:
    """Start the ReliableData BlockCache REST server."""
    _configure_logging(verbose)
    logger = logging.getLogger(__name__)
    logger.info("Starting BlockCache server on %s:%d", host, port)
    uvicorn.run(
        "rd.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
