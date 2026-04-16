# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Command Line Interface for ChiralDB."""

import argparse

import uvicorn


def main() -> None:
    """Run the ChiralDB CLI."""
    parser = argparse.ArgumentParser(description="ChiralDB CLI")
    parser.add_argument("command", choices=["serve"], help="Command to run")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")

    args = parser.parse_args()

    if args.command == "serve":
        print(f"Starting ChiralDB Server on port {args.port}...")
        uvicorn.run("chiral.main:app", host="0.0.0.0", port=args.port, reload=False)  # noqa: S104


if __name__ == "__main__":
    main()
