"""
Send a fake Tally sign-up to your Lambda Function URL, signed the same way Tally signs it.
Handy for testing from VS Code without filling in the form every time.

Run it from the integrations/tally-hubspot folder in VS Code's terminal:

    python send_test_signup.py prospect   # new prospect: #event-signups, lifecycle stage Lead
    python send_test_signup.py customer   # existing customer: #customer-success
    python send_test_signup.py repeat     # same email as prospect, new job title: contact updated
    python send_test_signup.py badsig     # wrong signature: should be rejected (only after step 8)

It reads FUNCTION_URL and TALLY_SIGNING_SECRET from a .env file next to this script.
.env is listed in .gitignore, so your secrets never get committed.
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

# Made-up test people. example.com addresses never receive real email.
PEOPLE = {
    "prospect": {
        "First name": "Ada", "Last name": "Test", "Email": "ada.test@example.com",
        "Company": "Acme Hiring", "Job title": "Head of Talent", "customer": "No",
    },
    "customer": {
        "First name": "Bola", "Last name": "Test", "Email": "bola.test@example.com",
        "Company": "Brightpath Ltd", "Job title": "Talent Partner", "customer": "Yes",
    },
    "repeat": {
        "First name": "Ada", "Last name": "Test", "Email": "ada.test@example.com",
        "Company": "Acme Hiring", "Job title": "VP Talent", "customer": "No",
    },
    "badsig": {
        "First name": "Should", "Last name": "Not Exist", "Email": "should.not.exist@example.com",
        "Company": "Nowhere", "Job title": "Imposter", "customer": "No",
    },
}

CHOICES = [{"id": "opt-yes", "text": "Yes"}, {"id": "opt-no", "text": "No"}]


def load_env(path):
    """Read KEY=value lines from a .env file (no extra library needed)."""
    values = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_payload(person, form_name="10x Recruiting: London"):
    """Build a body shaped like a real Tally FORM_RESPONSE webhook."""
    now = datetime.now(timezone.utc).isoformat()
    fields = [
        {"key": "question_first", "label": "First name", "type": "INPUT_TEXT", "value": person["First name"]},
        {"key": "question_last", "label": "Last name", "type": "INPUT_TEXT", "value": person["Last name"]},
        {"key": "question_email", "label": "Email", "type": "INPUT_EMAIL", "value": person["Email"]},
        {"key": "question_company", "label": "Company", "type": "INPUT_TEXT", "value": person["Company"]},
        {"key": "question_title", "label": "Job title", "type": "INPUT_TEXT", "value": person["Job title"]},
        {
            "key": "question_customer",
            "label": "Are you already a customer?",
            "type": "MULTIPLE_CHOICE",
            "value": ["opt-yes" if person["customer"] == "Yes" else "opt-no"],
            "options": CHOICES,
        },
    ]
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": "FORM_RESPONSE",
        "createdAt": now,
        "data": {
            "responseId": uuid.uuid4().hex[:8],
            "submissionId": uuid.uuid4().hex[:8],
            "formId": "test-form",
            "formName": form_name,
            "createdAt": now,
            "fields": fields,
        },
    }


def sign(raw_bytes, secret):
    digest = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def main():
    case = sys.argv[1] if len(sys.argv) > 1 else ""
    if case not in PEOPLE:
        print("Pick a test: python send_test_signup.py prospect | customer | repeat | badsig")
        sys.exit(1)

    env = load_env(os.path.join(HERE, ".env"))
    url = env.get("FUNCTION_URL") or os.environ.get("FUNCTION_URL", "")
    secret = env.get("TALLY_SIGNING_SECRET") or os.environ.get("TALLY_SIGNING_SECRET", "")
    if not url:
        print("No FUNCTION_URL found. Copy .env.example to .env and paste your Lambda Function URL in.")
        sys.exit(1)

    raw = json.dumps(build_payload(PEOPLE[case])).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if case == "badsig":
        if not secret:
            print("Run badsig only after step 8, once TALLY_SIGNING_SECRET is set in Lambda and in .env.")
            sys.exit(1)
        headers["Tally-Signature"] = "this-is-not-a-real-signature"
    elif secret:
        headers["Tally-Signature"] = sign(raw, secret)

    person = PEOPLE[case]
    print(f"Sending '{case}' test: {person['First name']} {person['Last name']} <{person['Email']}>")
    request = urllib.request.Request(url, data=raw, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            print("Status:", resp.status)
            print("Reply: ", resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        print("Status:", err.code)
        print("Reply: ", err.read().decode("utf-8"))
        if case != "badsig":
            print("Check Lambda > Monitor > View CloudWatch logs for the error.")


if __name__ == "__main__":
    main()
