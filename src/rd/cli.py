"""Command-line entry point for the ReliableData server."""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rd-server",
        description="Start the ReliableData key/value REST server.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    args = parser.parse_args()

    uvicorn.run(
        "rd.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
