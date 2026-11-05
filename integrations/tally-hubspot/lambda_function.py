"""
Tally sign-up -> HubSpot contact (tagged with the event) -> Slack alert to the right team.

Prospects start at lifecycle stage Lead and go to the sales channel.
Existing customers go to the customer success channel instead.

Runs on AWS Lambda (Python 3.13) behind a Function URL.
Uses only the Python standard library, so there is nothing to install or zip up.

Environment variables (Lambda > Configuration > Environment variables):
  HUBSPOT_TOKEN         private app access token from HubSpot
  SLACK_WEBHOOK_URL     incoming webhook for the sales channel (#event-signups)
  SLACK_CS_WEBHOOK_URL  incoming webhook for #customer-success (optional, falls back to the one above)
  TALLY_SIGNING_SECRET  signing secret from the Tally webhook (leave empty for the first test)
  EVENT_NAME            the tag to stamp on each contact, e.g. 10x London
"""

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request

HUBSPOT_TOKEN = os.environ.get("HUBSPOT_TOKEN", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_CS_WEBHOOK_URL = os.environ.get("SLACK_CS_WEBHOOK_URL", "")
TALLY_SIGNING_SECRET = os.environ.get("TALLY_SIGNING_SECRET", "")
EVENT_NAME = os.environ.get("EVENT_NAME", "10x London")

HUBSPOT_CONTACTS = "https://api.hubapi.com/crm/v3/objects/contacts"

# Tally question label (exactly as written in your form) -> HubSpot property internal name.
# event_source and existing_customer are custom properties you create in HubSpot first.
FIELD_MAP = {
    "First name": "firstname",
    "Last name": "lastname",
    "Email": "email",
    "Company": "company",
    "Job title": "jobtitle",
    "Are you already a customer?": "existing_customer",
}


def lambda_handler(event, context):
    # 1. Get the raw body exactly as Tally sent it.
    raw = event.get("body") or ""
    raw_bytes = base64.b64decode(raw) if event.get("isBase64Encoded") else raw.encode("utf-8")

    # 2. Check the request really came from Tally (only once a signing secret is set).
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if TALLY_SIGNING_SECRET and not signature_ok(raw_bytes, headers.get("tally-signature", "")):
        print("Rejected: bad or missing Tally-Signature")
        return respond(401, {"ok": False, "error": "bad signature"})

    # 3. Read the answers.
    payload = json.loads(raw_bytes or b"{}")
    if payload.get("eventType") != "FORM_RESPONSE":
        return respond(200, {"ok": True, "ignored": payload.get("eventType")})

    answers = read_answers(payload.get("data", {}).get("fields", []))
    print("Answers received:", json.dumps(answers))

    props = {FIELD_MAP[label]: value for label, value in answers.items() if label in FIELD_MAP and value}
    if not props.get("email"):
        return respond(400, {"ok": False, "error": "no email in the form answers"})
    props["event_source"] = EVENT_NAME
    is_customer = str(props.get("existing_customer", "")).strip().lower().startswith("yes")

    # 4. Create or update the contact in HubSpot.
    #    Brand-new prospects start at lifecycle stage Lead. This is only set when the contact
    #    is created, so an existing contact is never pushed back to an earlier stage.
    #    If HubSpot fails, the function errors, Tally sees a failure and retries later.
    on_create = {} if is_customer else {"lifecyclestage": "lead"}
    action = upsert_contact(props, on_create)
    print(f"HubSpot contact {action}: {props['email']} (customer: {is_customer})")

    # 5. Alert the right team. A Slack hiccup should not lose the lead, so it can't fail the run.
    try:
        notify_slack(props, action, is_customer)
    except Exception as err:  # noqa: BLE001
        print("Slack message failed:", err)

    return respond(200, {"ok": True, "contact": action, "routed_to": "customer success" if is_customer else "sales"})


def signature_ok(raw_bytes, sent_signature):
    """Tally signs the body with HMAC-SHA256 using your secret, then base64-encodes it."""
    digest = hmac.new(TALLY_SIGNING_SECRET.encode("utf-8"), raw_bytes, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, sent_signature or "")


def read_answers(fields):
    """Turn Tally's list of fields into {question label: answer}.

    Choice questions send option IDs, so swap them for the option text."""
    answers = {}
    for field in fields:
        value = field.get("value")
        option_text = {o.get("id"): o.get("text") for o in field.get("options") or []}
        if isinstance(value, list):
            value = ", ".join(str(option_text.get(v, v)) for v in value)
        elif value in option_text:
            value = option_text[value]
        answers[(field.get("label") or "").strip()] = value
    return answers


def upsert_contact(props, on_create=None):
    """Create the contact. If the email already exists (409), update it instead.

    on_create holds properties that should only be set on brand-new contacts."""
    auth = {"Authorization": f"Bearer {HUBSPOT_TOKEN}", "Content-Type": "application/json"}

    status, body = http("POST", HUBSPOT_CONTACTS, {"properties": {**props, **(on_create or {})}}, auth)
    if status == 201:
        return "created"

    if status == 409:
        email = urllib.parse.quote(props["email"], safe="")
        url = f"{HUBSPOT_CONTACTS}/{email}?idProperty=email"
        status, body = http("PATCH", url, {"properties": props}, auth)
        if status == 200:
            return "updated"

    raise RuntimeError(f"HubSpot said {status}: {body}")


def notify_slack(props, action, is_customer):
    name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip() or props["email"]
    details = ", ".join(p for p in (props.get("jobtitle"), props.get("company")) if p)
    who = f"*{name}*" + (f" ({details})" if details else "")

    if is_customer:
        url = SLACK_CS_WEBHOOK_URL or SLACK_WEBHOOK_URL
        text = (f":handshake: {EVENT_NAME} sign-up from an existing customer: {who}\n"
                "Worth a hello from their customer success manager before the event.")
    else:
        url = SLACK_WEBHOOK_URL
        text = (f":tada: {EVENT_NAME} sign-up from a prospect: {who}\n"
                "Not a customer yet, so sales should follow up.")
    text += f"\nHubSpot contact {action}, tagged \"{EVENT_NAME}\"."

    status, body = http("POST", url, {"text": text}, {"Content-Type": "application/json"})
    if status != 200:
        raise RuntimeError(f"Slack said {status}: {body}")


def http(method, url, data, headers):
    """Small helper so we don't need the requests library."""
    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8")


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
