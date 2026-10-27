"""flowdesk-brief-intake: turns the Tally "FlowDesk Content Brief" form into a brief in S3.

Tally webhook -> API Gateway (POST /briefs) -> this Lambda -> s3://<bucket>/briefs/<brief_id>.json
The content generator picks the file up from there, exactly as if someone had uploaded it.

Environment variables:
  CONTENT_BUCKET             the S3 bucket name
  BRIEF_FORM_SIGNING_SECRET  the signing secret from the brief form's Tally webhook
"""

import base64
import json
import os

from shared.briefs import InvalidBrief, build_brief
from shared.tally import signature_is_valid

_s3 = None


def s3():
    """One S3 client, made the first time it's needed. Tests swap in a fake."""
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3")
    return _s3


def log(step, **fields):
    """One JSON line per step, like lead-intake's logs, so Logs Insights can search them."""
    print(json.dumps({"step": step, **fields}))


def reply(status, message, **extra):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message, **extra}),
    }


def error_code(error):
    """The AWS error code, like 'PreconditionFailed', or '' for any other kind of error."""
    return getattr(error, "response", {}).get("Error", {}).get("Code", "")


def lambda_handler(event, context):
    bucket = os.environ.get("CONTENT_BUCKET")
    secret = os.environ.get("BRIEF_FORM_SIGNING_SECRET")
    if not bucket or not secret:
        # Raise, so the Errors alarm emails you. Tally gets a 500 and tries again later.
        log("config", status="error")
        raise RuntimeError("CONTENT_BUCKET or BRIEF_FORM_SIGNING_SECRET is not set")

    body = event.get("body") or ""
    raw_body = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode("utf-8")

    headers = {name.lower(): value for name, value in (event.get("headers") or {}).items()}
    if not signature_is_valid(raw_body, headers.get("tally-signature", ""), secret):
        log("signature", status="rejected")
        return reply(401, "Signature check failed")

    try:
        payload = json.loads(raw_body)
    except ValueError:
        log("parse", status="rejected", reason="body is not JSON")
        return reply(400, "Body is not JSON")

    try:
        brief, submission_id = build_brief(payload)
    except InvalidBrief as e:
        # A retry won't fix a bad submission, so answer 200 and log why.
        log("validate", status="rejected", reason=str(e))
        return reply(200, "Brief not usable", reason=str(e))

    key = f"briefs/{brief['brief_id']}.json"
    log("received", submission_id=submission_id, key=key, facts=len(brief["facts"]))

    try:
        # IfNoneMatch="*" means "only write if this file doesn't exist yet",
        # so a repeat of the same submission can't start a second draft.
        s3().put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(brief, indent=2).encode("utf-8"),
            ContentType="application/json",
            IfNoneMatch="*",
        )
    except Exception as e:
        if error_code(e) == "PreconditionFailed":
            log("saved", status="duplicate", submission_id=submission_id, key=key)
            return reply(200, "Already received", brief_id=brief["brief_id"])
        raise  # Anything else: fail loudly, so the alarm fires and Tally retries.

    log("saved", status="ok", submission_id=submission_id, key=key)
    return reply(200, "Brief saved", brief_id=brief["brief_id"])
