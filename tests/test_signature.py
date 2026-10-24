"""Checks signature_is_valid against a known answer.

Run from the flowdesk folder with:  python -m tests.test_signature
"""

from shared.tally import signature_is_valid

BODY = b'{"hello": "world"}'
SECRET = "test-secret"
# HMAC-SHA256 of BODY with SECRET, base64-encoded, worked out outside this code.
GOOD_SIGNATURE = "RNV9H4Y2F7uCoUIK3fbxiUdAw+5J66U3N42dG6+Fxx8="

CASES = [
    ("Correct signature", BODY, GOOD_SIGNATURE, SECRET, True),
    ("Body changed by one letter", b'{"hello": "World"}', GOOD_SIGNATURE, SECRET, False),
    ("Wrong secret", BODY, GOOD_SIGNATURE, "not-the-secret", False),
    ("No signature header", BODY, None, SECRET, False),
    ("No secret configured", BODY, GOOD_SIGNATURE, "", False),
]


def main():
    passed = 0
    for name, body, signature, secret, expected in CASES:
        actual = signature_is_valid(body, signature, secret)
        ok = actual == expected
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: expected {expected}, got {actual}")
    print(f"\n{passed} of {len(CASES)} passed")


if __name__ == "__main__":
    main()