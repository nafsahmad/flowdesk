"""Runs every test file and prints one line each, then an overall result.

Run from the flowdesk folder with:  python -m scripts.run_all_tests
It ends with an error if anything fails, so it can guard a build later.
"""

import re
import subprocess
import sys

TESTS = [
    "tests.test_scoring",
    "tests.test_tally",
    "tests.test_signature",
    "tests.test_checks",
    "tests.test_generator",
    "tests.test_wordpress_format",
    "tests.test_report",
    "tests.test_briefs",
    "tests.test_brief_intake",
]

RESULT_LINE = re.compile(r"(\d+) of (\d+) passed")


def main():
    failed = []
    for name in TESTS:
        result = subprocess.run([sys.executable, "-m", name], capture_output=True, text=True)
        match = RESULT_LINE.search(result.stdout)
        ok = (result.returncode == 0 and match is not None
              and match.group(1) == match.group(2))
        summary = match.group(0) if match else "no result line (it crashed)"
        print(f"{'PASS' if ok else 'FAIL'}  {name:<28} {summary}")
        if not ok:
            failed.append(name)
            details = (result.stdout + result.stderr).strip().splitlines()
            for line in details[-8:]:
                print(f"        {line}")

    print()
    if failed:
        raise SystemExit(f"{len(failed)} test file(s) failed: {', '.join(failed)}")
    print(f"All {len(TESTS)} test files passed")


if __name__ == "__main__":
    main()