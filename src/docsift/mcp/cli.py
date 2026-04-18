"""
MCP Server CLI

Command-line interface for running the DocSift MCP server.
"""

import sys
import logging
import argparse
import asyncio

from .transport_stdio import run_stdio
from .transport_http import run_http_server


def setup_logging(level: str = "info"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DocSift MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in stdio mode (for Claude Desktop)
  %(prog)s stdio
  
  # Run in HTTP mode
  %(prog)s http --host 0.0.0.0 --port 8080
  
  # Run with debug logging
  %(prog)s http --log-level debug
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Transport mode")

    # Stdio mode
    stdio_parser = subparsers.add_parser("stdio", help="Run in stdio mode (for Claude Desktop)")
    stdio_parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )

    # HTTP mode
    http_parser = subparsers.add_parser("http", help="Run in HTTP mode")
    http_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    http_parser.add_argument(
        "--port", type=int, default=8080, help="Port to bind to (default: 8080)"
    )
    http_parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )
    http_parser.add_argument(
        "--cors-origins", nargs="*", default=["*"], help="CORS allowed origins (default: *)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.log_level)

    if args.command == "stdio":
        run_stdio()
    elif args.command == "http":
        asyncio.run(
            run_http_server(
                host=args.host,
                port=args.port,
                cors_origins=args.cors_origins,
                log_level=args.log_level,
            )
        )


if __name__ == "__main__":
    main()
