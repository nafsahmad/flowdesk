"""Checks build_brief on a sample brief submission and messy versions of it.

Run from the flowdesk folder with:  python -m tests.test_briefs
"""

import copy
import re

from shared.briefs import InvalidBrief, build_brief

# The same rule the content generator uses for brief_id.
SAFE_ID = re.compile(r"^[a-z0-9-]{3,60}$")


def field(label, value, kind="INPUT_TEXT"):
    return {"key": f"question_{label.lower()}", "label": label, "type": kind, "value": value}


SAMPLE = {
    "eventType": "FORM_RESPONSE",
    "data": {
        "submissionId": "mVZ4kq",
        "createdAt": "2026-10-27T09:00:00.000Z",
        "fields": [
            field("Topic", "Stop chasing clients for logins in week one"),
            field("Audience", "Operations leads at small marketing agencies"),
            field("Facts", "- Clients share access from one FlowDesk page\n\n"
                           "* The agency sees what's missing at a glance\n"
                           "FlowDesk reminds clients automatically", "TEXTAREA"),
            field("Notes", "", "TEXTAREA"),
            field("Your email", "Nafs.Test@Example.com", "INPUT_EMAIL"),
        ],
    },
}


def with_answer(label, value, **extra):
    payload = copy.deepcopy(SAMPLE)
    for f in payload["data"]["fields"]:
        if f["label"] == label:
            f["value"] = value
            f.update(extra)
    return payload


def with_data(**changes):
    payload = copy.deepcopy(SAMPLE)
    payload["data"].update(changes)
    return payload


def brief_id(payload):
    return build_brief(payload)[0]["brief_id"]


def rejected(payload):
    try:
        build_brief(payload)
    except InvalidBrief:
        return True
    return False


def main():
    brief, submission = build_brief(SAMPLE)
    dropdown = with_answer("Audience", ["opt-2"], type="DROPDOWN", options=[
        {"id": "opt-1", "text": "Agency owners"},
        {"id": "opt-2", "text": "Operations leads at agencies"}])
    checks = [
        ("brief_id is topic words, date and submission id",
         brief["brief_id"] == "stop-chasing-clients-for-logins-in-week-20261027-mvz4kq"),
        ("brief_id passes the generator's rule", SAFE_ID.match(brief["brief_id"]) is not None),
        ("The same submission twice gets the same id", brief_id(SAMPLE) == brief["brief_id"]),
        ("Another submission on the same topic gets a different id",
         brief_id(with_data(submissionId="pQ81zz")) != brief["brief_id"]),
        ("No submission id still gives a safe id", SAFE_ID.match(brief_id(with_data(submissionId=None))) is not None),
        ("Offer is always the 15-minute demo", brief["offer"] == "A 15-minute demo"),
        ("Facts split into 3, bullets and blank lines dropped", brief["facts"] == [
            "Clients share access from one FlowDesk page",
            "The agency sees what's missing at a glance",
            "FlowDesk reminds clients automatically"]),
        ("Blank notes are left out", "notes" not in brief),
        ("Requester email is lowercased", brief["requested_by"] == "nafs.test@example.com"),
        ("Marked as coming from the form", brief["source"] == "brief-form" and submission == "mVZ4kq"),
        ("A 150-character topic still gives a safe id", SAFE_ID.match(brief_id(with_answer("Topic", "x" * 150))) is not None),
        ("A topic of only symbols still gives a safe id", SAFE_ID.match(brief_id(with_answer("Topic", "!!! ???"))) is not None),
        ("A dropdown answer becomes its option text",
         build_brief(dropdown)[0]["audience"] == "Operations leads at agencies"),
        ("Missing facts are rejected", rejected(with_answer("Facts", "   "))),
        ("Missing topic is rejected", rejected(with_answer("Topic", ""))),
        ("A topic over 150 characters is rejected", rejected(with_answer("Topic", "x" * 151))),
        ("More than 10 facts are rejected", rejected(with_answer("Facts", "\n".join(f"Fact {i}" for i in range(11))))),
        ("A fact over 300 characters is rejected", rejected(with_answer("Facts", "y" * 301))),
        ("Not a form response is rejected", rejected({**SAMPLE, "eventType": "PING"})),
    ]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in checks)} of {len(checks)} passed")


if __name__ == "__main__":
    main()
