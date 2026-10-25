"""Checks the rule checks on a good caption and broken versions of it.

Run from the flowdesk folder with:  python -m tests.test_checks
"""

from shared.checks import check_blog, check_copy, passed

GOOD = (
    "New clients are exciting until week one turns into a chase for contracts, "
    "forms and logins. FlowDesk sends each client one link where they sign, fill in "
    "the intake form and share access. Your team gets one checklist that fills itself "
    "in, and clients get reminded automatically when something is missing. "
    "Book a 15-minute demo: {link}"
)

# (name, caption text, which check to look at, should it pass?)
CASES = [
    ("Good caption passes everything", GOOD, None, True),
    ("Full stop after the link is fine", GOOD + ".", "cta", True),
    ("Em dash", GOOD.replace("exciting until", "exciting \u2014 until"), "em_dash", False),
    ("Banned word", GOOD.replace("one checklist", "one seamless checklist"), "banned_words", False),
    ("Question", GOOD.replace("logins.", "logins. Sound familiar?"), "questions", False),
    ("No call to action", GOOD.replace(" Book a 15-minute demo: {link}", ""), "cta", False),
    ("Leftover placeholder", GOOD.replace("Your team", "[Agency Name]'s team"), "placeholders", False),
    ("Hashtag", GOOD.replace("missing.", "missing. #agencylife"), "hashtags", False),
    ("Emoji", GOOD.replace("missing.", "missing. \U0001F680"), "emojis", False),
    ("Too short", "FlowDesk helps. Book a 15-minute demo: {link}", "word_count", False),
]


def main():
    ok_count = 0
    for name, text, check, should_pass in CASES:
        results = check_copy(text, 40, 80, social=True)
        if check is None:
            ok = passed(results) == should_pass
            detail = results
        else:
            ok = (results[check] == "pass") == should_pass
            detail = results[check]
        ok_count += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    long_title = "A" * 71
    blog = check_blog(long_title, GOOD)
    ok = blog["title_length"] != "pass" and blog["word_count"] != "pass"
    ok_count += ok
    print(f"{'PASS' if ok else 'FAIL'}  Blog: long title and short body both caught")

    print(f"\n{ok_count} of {len(CASES) + 1} passed")


if __name__ == "__main__":
    main()