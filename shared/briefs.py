"""Turns a Tally "FlowDesk Content Brief" submission into a brief for the content generator.

This file never talks to AWS. It takes Tally's JSON and returns the brief,
or raises InvalidBrief with the reason.
"""

import re
import secrets
from datetime import datetime, timezone

# Tally label (lowercase) -> field name in the brief.
LABEL_TO_FIELD = {
    "topic": "topic",
    "audience": "audience",
    "facts": "facts",
    "notes": "notes",
    "your email": "requested_by",
}
REQUIRED = ["topic", "audience", "facts"]

# Every post ends with "Book a 15-minute demo: {link}" (prompts/brand_rules.md),
# so the form doesn't ask for an offer. A typed offer could promise one thing
# while the link at the end goes somewhere else.
OFFER = "A 15-minute demo"

MAX_FACTS = 10
MAX_LENGTH = {"topic": 150, "audience": 150, "notes": 600}
MAX_FACT_LENGTH = 300


class InvalidBrief(Exception):
    """Raised when a submission can never become a usable brief."""


def slugify(text, max_length=40):
    """'Stop chasing logins!' -> 'stop-chasing-logins'. Lowercase letters, numbers and hyphens only."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "brief"


def make_brief_id(topic, created_at=None, submission_id=None):
    """Topic words, submission date and Tally's submission id: stop-chasing-logins-20261027-mvz4kq

    It's built only from the submission, so if Tally sends the same one twice
    it gets the same id, and the handler can spot the repeat.
    """
    if created_at and re.match(r"^\d{4}-\d{2}-\d{2}", created_at):
        day = created_at[:10].replace("-", "")
    else:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
    tail = re.sub(r"[^a-z0-9]", "", (submission_id or "").lower())[:8] or secrets.token_hex(3)
    return f"{slugify(topic)}-{day}-{tail}"


def answer_text(field):
    """The answer as plain text. Dropdowns send option ids, so swap in the option text."""
    value = field.get("value")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        names = {option.get("id"): option.get("text") or "" for option in field.get("options") or []}
        chosen = [names.get(item, "").strip() for item in value]
        return ", ".join(text for text in chosen if text)
    return ""


def split_facts(text):
    """One fact per line. Blank lines and bullet marks are dropped."""
    facts = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*•").strip()
        if line:
            facts.append(line)
    return facts


def build_brief(payload):
    """Return (brief, submission_id), or raise InvalidBrief."""
    if payload.get("eventType") != "FORM_RESPONSE":
        raise InvalidBrief(f"Not a form response: {payload.get('eventType')}")

    data = payload.get("data") or {}
    submission_id = data.get("submissionId") or "unknown"

    answers = {}
    for field in data.get("fields") or []:
        name = LABEL_TO_FIELD.get((field.get("label") or "").strip().lower())
        text = answer_text(field)
        if name and text:
            answers[name] = text

    missing = [name for name in REQUIRED if not answers.get(name)]
    if missing:
        raise InvalidBrief(f"Missing: {', '.join(missing)}")

    for name, limit in MAX_LENGTH.items():
        if len(answers.get(name, "")) > limit:
            raise InvalidBrief(f"{name} is {len(answers[name])} characters, the limit is {limit}")

    facts = split_facts(answers["facts"])
    if not facts:
        raise InvalidBrief("No facts")
    if len(facts) > MAX_FACTS:
        raise InvalidBrief(f"{len(facts)} facts, the limit is {MAX_FACTS}")
    for fact in facts:
        if len(fact) > MAX_FACT_LENGTH:
            raise InvalidBrief(f"A fact is {len(fact)} characters, the limit is {MAX_FACT_LENGTH}")

    brief = {
        "brief_id": make_brief_id(answers["topic"], data.get("createdAt"), data.get("submissionId")),
        "topic": answers["topic"],
        "audience": answers["audience"],
        "offer": OFFER,
        "facts": facts,
        "source": "brief-form",
        "submission_id": submission_id,
    }
    if answers.get("notes"):
        brief["notes"] = answers["notes"]
    if answers.get("requested_by"):
        brief["requested_by"] = answers["requested_by"].lower()
    return brief, submission_id
