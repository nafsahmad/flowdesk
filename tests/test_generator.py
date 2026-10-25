"""Runs the whole generator with the fake model, on a good brief and the trap brief.

Run from the flowdesk folder with:  python -m tests.test_generator
"""

import json
import os

os.environ["FLOWDESK_FAKE_LLM"] = "1"  # never call Bedrock from tests

from shared.generator import extract_json, generate  # noqa: E402


def load_brief(name):
    with open(f"sample_data/briefs/{name}.json", encoding="utf-8") as f:
        return json.load(f)


def main():
    checks = []

    good = generate(load_brief("onboarding-checklist"))
    checks.append(("Good brief ends as checked", good["status"] == "checked"))
    checks.append(("Good brief was judged 3 times", len(good["judge"]) == 3))
    checks.append(("Record says which model and prompts", good["model"] == "fake"
                   and good["prompt_versions"]["blog"] == "v1"))
    checks.append(("{link} is still in the blog for later",
                   "{link}" in good["blog"]["body"]))

    risky = generate(load_brief("results-promise"))
    checks.append(("Trap brief ends as failed_checks", risky["status"] == "failed_checks"))
    checks.append(("Judge flagged the made-up claim",
                   risky["judge"]["blog"]["made_up_claims"] == "yes"))

    checks.append(("JSON inside ``` fences is read",
                   extract_json('```json\n{"a": 1}\n```') == {"a": 1}))
    checks.append(("Garbage gives None, not a crash", extract_json("sorry, no") is None))

    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in checks)} of {len(checks)} passed")


if __name__ == "__main__":
    main()