"""Checks parse_tally on the sample payload and on messy versions of it.

Run from the flowdesk folder with:  python -m tests.test_tally
"""

import copy
import json

from shared.tally import InvalidLead, parse_tally

with open("sample_data/tally_payload.json", encoding="utf-8") as f:
    SAMPLE = json.load(f)


def payload_with(changes=None, remove=()):
    """Copy the sample, change some answers by label, remove some questions."""
    payload = copy.deepcopy(SAMPLE)
    fields = [f for f in payload["data"]["fields"] if f["label"] not in remove]
    for f in fields:
        if changes and f["label"] in changes:
            f["value"] = changes[f["label"]]
    payload["data"]["fields"] = fields
    return payload


def relabelled(old, new):
    """Copy the sample with one question's label renamed."""
    payload = copy.deepcopy(SAMPLE)
    for f in payload["data"]["fields"]:
        if f["label"] == old:
            f["label"] = new
    return payload


def expect_ok(name, payload, check):
    try:
        properties, _ = parse_tally(payload)
    except InvalidLead as e:
        print(f"FAIL  {name}: rejected ({e})")
        return False
    if check(properties):
        print(f"PASS  {name}")
        return True
    print(f"FAIL  {name}: got {properties}")
    return False


def expect_rejected(name, payload):
    try:
        parse_tally(payload)
    except InvalidLead:
        print(f"PASS  {name} (rejected, as it should be)")
        return True
    print(f"FAIL  {name}: accepted, but it should have been rejected")
    return False


def main():
    results = [
        expect_ok("Sample payload", SAMPLE,
                  lambda p: p["email"] == "kemi.test@example.com"
                  and p["fd_utm_content"] == "A"
                  and p["fd_company_size"] == "40"),
        expect_ok("Email in capitals gets lowercased",
                  payload_with({"Work email": "Kemi.Test@Example.COM"}),
                  lambda p: p["email"] == "kemi.test@example.com"),
        expect_ok("No hidden fields still saves the lead",
                  payload_with(remove=("utm_source", "utm_campaign", "utm_content")),
                  lambda p: "fd_utm_content" not in p),
        expect_ok("Blank company is left out",
                  payload_with({"Company": ""}),
                  lambda p: "company" not in p),
        expect_ok("Label in different capitals still matches",
                  relabelled("First Name", "FIRST NAME"),
                  lambda p: p["firstname"] == "Kemi"),
        expect_ok("Renamed question is silently lost",
                  relabelled("Job title", "Your role"),
                  lambda p: "jobtitle" not in p),
        expect_rejected("No email question at all", payload_with(remove=("Work email",))),
        expect_rejected("Blank email", payload_with({"Work email": ""})),
        expect_rejected("Broken email", payload_with({"Work email": "kemi.test@"})),
        expect_rejected("Not a form response", {**SAMPLE, "eventType": "PING"}),
    ]
    print(f"\n{sum(results)} of {len(results)} passed")


if __name__ == "__main__":
    main()