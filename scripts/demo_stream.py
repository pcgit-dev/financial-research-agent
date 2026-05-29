"""Minimal CLI client for the streaming endpoint.

Usage:
    python scripts/demo_stream.py "Current EUR/USD rate?"
    python scripts/demo_stream.py "What is diversification?" --url http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream an answer from the agent.")
    parser.add_argument("query", help="The financial research question.")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL.")
    parser.add_argument("--conversation-id", default=None, help="Continue a conversation.")
    parser.add_argument("--api-key", default=None, help="X-API-Key if auth is enabled.")
    args = parser.parse_args()

    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    payload = {"query": args.query, "conversation_id": args.conversation_id}

    with httpx.stream(
        "POST", f"{args.url}/query/stream", json=payload, headers=headers, timeout=120
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: "):])
            etype = event.get("type")
            if etype == "route":
                print(f"\n[route: {event['route']}] {event.get('reason', '')}\n", flush=True)
            elif etype == "token":
                sys.stdout.write(event["content"])
                sys.stdout.flush()
            elif etype == "done":
                print("\n\n--- stream complete ---")
            elif etype == "error":
                print(f"\n[error] {event['message']}", file=sys.stderr)


if __name__ == "__main__":
    main()
