"""flowdesk-content-generator: brief uploaded to S3 -> drafts -> record saved to S3.

Triggered by S3 when a .json file lands in briefs/.
"""

import json
import re
from urllib.parse import unquote_plus

import boto3

from shared.generator import generate

s3 = boto3.client("s3")

REQUIRED_KEYS = ["brief_id", "topic", "audience", "offer", "facts"]
SAFE_ID = re.compile(r"^[a-z0-9-]{3,60}$")


def log(**fields):
    """Write one line of JSON to CloudWatch Logs."""
    print(json.dumps(fields))


def brief_problem(brief):
    """Return what's wrong with a brief, or None if it's usable."""
    if not isinstance(brief, dict):
        return "a brief must be a JSON object"
    missing = [k for k in REQUIRED_KEYS if not brief.get(k)]
    if missing:
        return "missing " + ", ".join(missing)
    if not SAFE_ID.match(brief["brief_id"]):
        return "brief_id must be 3 to 60 lowercase letters, numbers or hyphens"
    if not isinstance(brief["facts"], list):
        return "facts must be a list"
    return None


def lambda_handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        if not key.startswith("briefs/") or not key.endswith(".json"):
            log(step="skip", key=key, reason="not a brief")
            continue

        log(step="received", key=key)
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()

        try:
            brief = json.loads(body)
        except json.JSONDecodeError:
            log(step="validate", status="rejected", key=key, reason="not valid JSON")
            continue
        problem = brief_problem(brief)
        if problem:
            log(step="validate", status="rejected", key=key, reason=problem)
            continue

        draft = generate(brief)  # a model failure raises, so Lambda retries
        draft["source_key"] = key

        out_key = f"content/{draft['brief_id']}/draft.json"
        s3.put_object(Bucket=bucket, Key=out_key,
                      Body=json.dumps(draft, indent=2).encode("utf-8"),
                      ContentType="application/json")
        log(step="saved", key=out_key, status=draft["status"], model=draft["model"],
            repairs=draft["repairs"])