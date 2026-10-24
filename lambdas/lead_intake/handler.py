"""flowdesk-lead-intake: Tally webhook -> score -> HubSpot.

Triggered by API Gateway (HTTP API, POST /leads).
"""

import base64
import json

from shared.hubspot import upsert_contact
from shared.scoring import score_contact
from shared.tally import InvalidLead, parse_tally


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
        body = base64.b64decode(body).decode("utf-8")

    try:
        payload = json.loads(body)
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
        action=action, contact_id=contact_id, score=properties["fd_score"])
    return reply(200, f"Lead {action}")