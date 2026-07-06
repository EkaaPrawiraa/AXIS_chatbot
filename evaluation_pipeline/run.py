#!/usr/bin/env python3
import argparse
import sys

from config import DEFAULT_USER_ID
from chatbot import chat


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baseline chatbot (pgvector only, no KG) for evaluation."
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=DEFAULT_USER_ID,
        help="UUID of the user whose memories to retrieve.",
    )
    parser.add_argument(
        "--message",
        type=str,
        required=True,
        help="The user message to send to the chatbot.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of memories to retrieve (default: 5).",
    )

    args = parser.parse_args()

    if not args.user_id:
        print("Error: --user-id is required (or set USER_ID in .env).", file=sys.stderr)
        sys.exit(1)

    print(f"[run] user_id={args.user_id}")
    print(f"[run] message={args.message!r}")
    print()

    response = chat(user_id=args.user_id, user_message=args.message, top_k=args.top_k)

    print("=== Response ===")
    print(response)


if __name__ == "__main__":
    main()
