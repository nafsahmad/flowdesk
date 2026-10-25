"""Prints a prompt filled in with a brief, ready to paste into the Bedrock playground.

Run:  python -m scripts.preview_prompt blog_v1.txt sample_data/briefs/onboarding-checklist.json
"""

import json
import sys

from shared.prompts import brief_values, fill, load


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m scripts.preview_prompt <prompt file> <brief file>")
    template = load(sys.argv[1])
    with open(sys.argv[2], encoding="utf-8") as f:
        brief = json.load(f)
    print(fill(template, brief_values(brief)))


if __name__ == "__main__":
    main()