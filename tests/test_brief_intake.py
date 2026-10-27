"""Runs the brief-intake Lambda against a fake S3, so it needs no AWS access.

Run from the flowdesk folder with:  python -m tests.test_brief_intake
"""

import base64
import contextlib
import copy
import hashlib
import hmac
import importlib.util
import io
import json
import os
import re
from pathlib import Path

from tests.test_briefs import SAMPLE

SECRET = "test-brief-secret"
SAFE_ID = re.compile(r"^[a-z0-9-]{3,60}$")
REQUIRED_KEYS = ["brief_id", "topic", "audience", "offer", "facts"]

HANDLER_FILE = Path(__file__).resolve().parent.parent / "lambdas" / "brief_intake" / "handler.py"
spec = importlib.util.spec_from_file_location("brief_intake_handler", HANDLER_FILE)
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


class FakeS3:
    """Keeps files in a dict and behaves like S3 for IfNoneMatch='*'."""

    def __init__(self, broken=False):
        self.files = {}
        self.broken = broken

    def put_object(self, Bucket, Key, Body, ContentType, IfNoneMatch=None):
        if self.broken:
            raise ConnectionError("S3 is down")
        if IfNoneMatch == "*" and Key in self.files:
            error = Exception("At least one of the pre-conditions you specified did not hold")
            error.response = {"Error": {"Code": "PreconditionFailed"}}
            raise error
        self.files[Key] = json.loads(Body)


def signed_event(payload, secret=SECRET, as_base64=False, raw=None):
    raw = raw if raw is not None else json.dumps(payload).encode("utf-8")
    signature = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    body = base64.b64encode(raw).decode() if as_base64 else raw.decode("utf-8")
    return {"headers": {"Tally-Signature": signature}, "body": body, "isBase64Encoded": as_base64}


def run(event, s3):
    handler._s3 = s3
    with contextlib.redirect_stdout(io.StringIO()):  # keep the Lambda's log lines out of the results
        result = handler.lambda_handler(event, None)
    return result["statusCode"], json.loads(result["body"])


def raises(event, s3):
    try:
        run(event, s3)
    except Exception:
        return True
    return False


def main():
    os.environ["CONTENT_BUCKET"] = "test-bucket"
    os.environ["BRIEF_FORM_SIGNING_SECRET"] = SECRET

    s3 = FakeS3()
    status, body = run(signed_event(SAMPLE), s3)
    saved = next(iter(s3.files.values()), {})
    status2, body2 = run(signed_event(SAMPLE), s3)

    no_facts = copy.deepcopy(SAMPLE)
    for f in no_facts["data"]["fields"]:
        if f["label"] == "Facts":
            f["value"] = ""

    unsigned = signed_event(SAMPLE)
    del unsigned["headers"]["Tally-Signature"]

    empty = FakeS3()
    checks = [
        ("A signed brief is saved to briefs/", status == 200 and list(s3.files) == [f"briefs/{body.get('brief_id')}.json"]),
        ("The saved brief has every key the generator needs",
         all(k in saved for k in REQUIRED_KEYS) and isinstance(saved.get("facts"), list)),
        ("The saved brief_id passes the generator's rule", SAFE_ID.match(saved.get("brief_id", "")) is not None),
        ("The same submission again is not saved twice",
         status2 == 200 and body2["message"] == "Already received" and len(s3.files) == 1),
        ("A base64 body works", run(signed_event(SAMPLE, as_base64=True), FakeS3())[0] == 200),
        ("Wrong secret gets 401 and saves nothing",
         run(signed_event(SAMPLE, secret="wrong"), empty)[0] == 401 and not empty.files),
        ("No signature gets 401 and saves nothing", run(unsigned, empty)[0] == 401 and not empty.files),
        ("A brief with no facts gets 200 and saves nothing",
         run(signed_event(no_facts), empty) == (200, {"message": "Brief not usable", "reason": "Missing: facts"})
         and not empty.files),
        ("A body that isn't JSON gets 400", run(signed_event(None, raw=b"not json"), empty)[0] == 400),
        ("An S3 failure raises, so Tally retries and the alarm fires", raises(signed_event(SAMPLE), FakeS3(broken=True))),
    ]

    del os.environ["BRIEF_FORM_SIGNING_SECRET"]
    checks.append(("A missing secret raises, so the alarm fires", raises(signed_event(SAMPLE), FakeS3())))

    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in checks)} of {len(checks)} passed")


if __name__ == "__main__":
    main()
