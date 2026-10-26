"""Checks the HTML and link building, without calling WordPress.

Run from the flowdesk folder with:  python -m tests.test_wordpress_format
"""

from shared.links import tracked_link
from shared.wordpress import REVIEW_MARKER, body_to_html, review_notes_html

BODY = ("Week one shouldn't be a chase.\n\n"
        "Contracts & forms arrive in one link.\n\n"
        "Book a 15-minute demo: {link}")
LINK = "https://tally.so/r/abc123?utm_source=blog&utm_campaign=test&utm_content=blog"


def main():
    html_out = body_to_html(BODY, LINK)
    link = tracked_link("https://tally.so/r/abc123", "blog", "onboarding-checklist", "blog")
    checks = [
        ("Three paragraphs become three blocks", html_out.count("<!-- wp:paragraph -->") == 3),
        ("{link} is replaced by a real link", "{link}" not in html_out
         and 'href="https://tally.so/r/abc123?' in html_out),
        ("& is made safe for HTML", "Contracts &amp; forms" in html_out),
        ("Apostrophes stay readable", "shouldn't" in html_out),
        ("Tracked link has all three UTM values", link ==
         "https://tally.so/r/abc123?utm_source=blog&utm_campaign=onboarding-checklist"
         "&utm_content=blog"),
        ("A URL that already has ? gets & instead",
         tracked_link("https://x.com/f?ref=1", "a", "b", "c").startswith("https://x.com/f?ref=1&utm_")),
        ("Review box names the marker and each flagged sentence",
         REVIEW_MARKER in review_notes_html({"blog": ["You get <updates>"]})
         and "You get &lt;updates&gt;" in review_notes_html({"blog": ["You get <updates>"]})),
    ]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in checks)} of {len(checks)} passed")


if __name__ == "__main__":
    main()