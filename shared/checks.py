"""Rule checks for generated copy.

They're free, instant and never wrong about the rules they cover,
so they run before the AI judge. Each check returns "pass" or a reason.
"""

import re

BANNED_WORDS = [
    "game-changer", "game changer", "revolutionary", "seamless",
    "leverage", "synergy", "unlock", "supercharge",
]
CTA_AT_END = re.compile(r"Book a 15-minute demo:\s*\{link\}\W*$")
LEFTOVER = re.compile(r"\{(?!link\})[a-z_]+\}|\[[A-Z][A-Za-z ]+\]")
HASHTAG = re.compile(r"#\w")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
EM_DASH = "\u2014"


# Made-up claims the model has actually produced in our runs. Code catches these
# for certain; the AI judge looks for new ones. Add to this list after each review.
CLAIM_PHRASES = [
    "real time", "real-time", "in minutes", "save hours", "saves hours",
    "hours each week", "more clients", "integrates", "connects to",
    "fits into your existing", "agencies using flowdesk", "minutes instead of hours", "live view",
]


def check_copy(text, min_words, max_words, social=False):
    """Run every rule on one piece of copy. Returns {check name: "pass" or a reason}."""
    lower = text.lower()
    results = {}

    words = len(text.split())
    results["word_count"] = ("pass" if min_words <= words <= max_words
                             else f"{words} words, wanted {min_words} to {max_words}")

    results["em_dash"] = "pass" if EM_DASH not in text else "contains an em dash"

    found = [w for w in BANNED_WORDS if w in lower]
    results["banned_words"] = "pass" if not found else "uses " + ", ".join(found)

    results["questions"] = "pass" if "?" not in text else "contains a question"
    
    claims = [p for p in CLAIM_PHRASES if p in lower]
    results["claim_phrases"] = ("pass" if not claims
                                else "known made-up claim: " + ", ".join(claims))

    results["cta"] = ("pass" if CTA_AT_END.search(text)
                      else "doesn't end with the call to action and {link}")

    leftovers = LEFTOVER.findall(text)
    results["placeholders"] = ("pass" if not leftovers
                               else "leftover placeholder: " + ", ".join(leftovers))

    if social:
        results["hashtags"] = "pass" if not HASHTAG.search(text) else "contains a hashtag"
        results["emojis"] = "pass" if not EMOJI.search(text) else "contains an emoji"

    return results


def check_blog(title, body):
    """Checks for a blog post: the copy rules on the body, plus the title length."""
    results = check_copy(body, 250, 400)
    results["title_length"] = ("pass" if len(title) <= 70
                               else f"title is {len(title)} characters, wanted 70 or fewer")
    return results


def passed(results):
    """True if every check passed."""
    return all(value == "pass" for value in results.values())