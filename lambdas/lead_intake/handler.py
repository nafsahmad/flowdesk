"""flowdesk-lead-intake: Tally webhook -> check signature -> score -> HubSpot.

Triggered by API Gateway (HTTP API, POST /leads).
"""

import base64
import json
import os

from shared.hubspot import upsert_contact
from shared.scoring import score_contact
from shared.tally import InvalidLead, parse_tally, signature_is_valid


def log(**fields):
    """Write one line of JSON to CloudWatch Logs."""
    print(json.dumps(fields))


def reply(status, message):
    """The response API Gateway sends back to Tally."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message}),
    }


def lambda_handler(event, context):
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(body)
    else:
        raw_body = body.encode("utf-8")

    secret = os.environ.get("TALLY_SIGNING_SECRET")
    if not secret:
        log(step="config", status="error", reason="TALLY_SIGNING_SECRET is not set")
        return reply(500, "Server not configured")

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if not signature_is_valid(raw_body, headers.get("tally-signature"), secret):
        log(step="signature", status="rejected", reason="missing or wrong signature")
        return reply(401, "Invalid signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        log(step="parse", status="rejected", reason="body is not JSON")
        return reply(400, "Body must be JSON")

    log(step="received", submission=payload.get("data", {}).get("submissionId"))

    try:
        properties, submission_id = parse_tally(payload)
    except InvalidLead as e:
        log(step="parse", status="rejected", reason=str(e))
        return reply(200, "Received, but not a valid lead")

    properties["fd_score"] = score_contact(properties)
    action, contact_id = upsert_contact(properties)  # a HubSpot error stops the run on purpose

    log(step="written", status="ok", submission=submission_id,
        action=action, contact_id=contact_id, score=properties["fd_score"],
        variant=properties.get("fd_utm_content") or "none")
    return reply(200, f"Lead {action}")