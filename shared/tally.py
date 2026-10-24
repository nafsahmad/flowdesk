"""Turns a Tally form submission into a HubSpot contact.

This file never talks to HubSpot or AWS. It takes Tally's JSON
(already turned into a Python dictionary) and returns the
properties to save, or a reason the lead can't be saved.
"""

import re

# Tally label (lowercase) -> HubSpot internal property name.
# Matching ignores capitals, so "First Name" and "First name" both work.
LABEL_TO_PROPERTY = {
    "first name": "firstname",
    "last name": "lastname",
    "work email": "email",
    "company": "company",
    "job title": "jobtitle",
    "company size": "fd_company_size",
    "utm_source": "fd_utm_source",
    "utm_campaign": "fd_utm_campaign",
    "utm_content": "fd_utm_content",
}

# something@something.something with no spaces. Simple on purpose.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidLead(Exception):
    """Raised when a submission can never become a contact."""


def parse_tally(payload):
    """Return (properties, submission_id) for HubSpot, or raise InvalidLead."""
    if payload.get("eventType") != "FORM_RESPONSE":
        raise InvalidLead(f"Not a form response: {payload.get('eventType')}")

    data = payload.get("data") or {}
    submission_id = data.get("submissionId", "unknown")
    properties = {}

    for field in data.get("fields") or []:
        label = (field.get("label") or "").strip().lower()
        prop = LABEL_TO_PROPERTY.get(label)
        if prop is None:
            continue  # a question we don't map, so ignore it
        value = field.get("value")
        if value is None or value == "":
            continue  # left blank, so don't send it
        properties[prop] = str(value).strip()

    email = properties.get("email", "").lower()
    if not email:
        raise InvalidLead(f"Submission {submission_id} has no email")
    if not EMAIL_PATTERN.match(email):
        raise InvalidLead(f"Submission {submission_id} has a broken email")
    properties["email"] = email

    return properties, submission_id


if __name__ == "__main__":
    import json
    from shared.scoring import score_contact

    with open("sample_data/tally_payload.json", encoding="utf-8") as f:
        payload = json.load(f)
    properties, submission_id = parse_tally(payload)
    print("Submission:", submission_id)
    for name, value in properties.items():
        print(f"  {name:<16} {value}")
    print("Score:", score_contact(properties))