"""Lead scoring rules for FlowDesk.

The rules here must match docs/decisions.md (Lead scoring rules v1).
This file never talks to HubSpot. It takes a contact's properties
as a plain dictionary and returns a score from 0 to 100.
"""

SENIOR_WORDS = ["head", "director", "founder"]
MIN_COMPANY_SIZE = 10

POINTS_SENIOR_TITLE = 40
POINTS_COMPANY_SIZE = 30
POINTS_COMPANY_NAME = 15
POINTS_CAMPAIGN = 15


def _to_number(value):
    """Turn HubSpot's text ("250") into a number. Blank or junk becomes 0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def score_contact(props):
    """Score one contact. props is the 'properties' dictionary from HubSpot."""
    score = 0

    title = (props.get("jobtitle") or "").lower()
    if any(word in title for word in SENIOR_WORDS):
        score += POINTS_SENIOR_TITLE

    if _to_number(props.get("fd_company_size")) >= MIN_COMPANY_SIZE:
        score += POINTS_COMPANY_SIZE

    if (props.get("company") or "").strip():
        score += POINTS_COMPANY_NAME

    if (props.get("fd_utm_campaign") or "").strip():
        score += POINTS_CAMPAIGN

    return score