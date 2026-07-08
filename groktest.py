#!/usr/bin/env python3
"""
Groq API Quick Test
Type a question, get the raw response back. Simplest possible way to confirm
the API key and connection work.
"""

import os
import sys

try:
    from groq import Groq
except ImportError:
    print("✗ 'groq' library not installed.")
    print("  Fix: pip install groq")
    sys.exit(1)


MODEL_NAME = "openai/gpt-oss-120b"


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("✗ GROQ_API_KEY environment variable is not set.")
        print("  Fix: export GROQ_API_KEY='your-key-here'")
        print("  Get a free key at: https://console.groq.com/keys")
        sys.exit(1)

    client = Groq(api_key=api_key)

    question = input("Ask something: ").strip()
    if not question:
        print("No question entered, exiting.")
        sys.exit(0)

    print("\nSending to Groq...\n")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=500,
            messages=[
                {"role": "user", "content": question}
            ]
        )
        print("-" * 60)
        print(response.choices[0].message.content)
        print("-" * 60)
    except Exception as e:
        print(f"✗ Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()