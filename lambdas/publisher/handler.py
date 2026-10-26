"""flowdesk-publisher: moves each draft record along its statuses.

Runs every hour. For each record in content/:
  checked or needs_review -> create a WordPress draft  -> in_wordpress
                             (needs_review drafts start with a red box of review notes)
  in_wordpress  -> you published it and it's live        -> published
                   it was deleted or trashed in WordPress -> removed_in_wordpress
Everything else is left alone.
"""

import json
import os
from datetime import datetime, timezone

import boto3
import requests

from shared.links import tracked_link
from shared.wordpress import (REVIEW_MARKER, body_to_html, create_draft, get_category_id,
                              get_post, review_notes_html)

s3 = boto3.client("s3")
BUCKET = os.environ["CONTENT_BUCKET"]
CATEGORY_SLUG = "flowdesk"


def log(**fields):
    """Write one line of JSON to CloudWatch Logs."""
    print(json.dumps(fields))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def set_status(record, status):
    """Change the status and add it to the record's history."""
    record["status"] = status
    record.setdefault("history", []).append({"status": status, "at": now()})


def load(key):
    return json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())


def save(key, record):
    s3.put_object(Bucket=BUCKET, Key=key,
                  Body=json.dumps(record, indent=2).encode("utf-8"),
                  ContentType="application/json")


def record_keys():
    """Every draft.json under content/, page by page."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix="content/"):
        for item in page.get("Contents", []):
            if item["Key"].endswith("/draft.json"):
                yield item["Key"]


def send_to_wordpress(record):
    """checked -> in_wordpress"""
    link = tracked_link(os.environ["TALLY_FORM_URL"], "blog", record["brief_id"], "blog")
    content = body_to_html(record["blog"]["body"], link)
    if record.get("review_notes"):
        content = review_notes_html(record["review_notes"]) + content
    post_id, edit_link = create_draft(record["blog"]["title"], content,
                                      get_category_id(CATEGORY_SLUG))
    record["wordpress"] = {"post_id": post_id, "edit_link": edit_link}
    set_status(record, "in_wordpress")


def live_page(url, post_id):
    """The public page's HTML, if it loads and really is this post. Otherwise None."""
    r = requests.get(url, timeout=15)
    if r.status_code == 200 and f"postid-{post_id}" in r.text:
        return r.text
    return None


def captions_with_links(record):
    """Captions A and B with {link} swapped for a tracked link to the demo form."""
    form = os.environ["TALLY_FORM_URL"]
    return {variant: text.replace("{link}",
                                  tracked_link(form, "linkedin", record["brief_id"], variant))
            for variant, text in record["captions"].items()}


def check_wordpress(record):
    """in_wordpress -> published or removed_in_wordpress. Returns True if it changed."""
    post_id = record["wordpress"]["post_id"]
    post = get_post(post_id)
    if post is None or post["status"] == "trash":
        set_status(record, "removed_in_wordpress")
        return True
    if post["status"] != "publish":
        return False  # still waiting for your approval
    page = live_page(post["link"], post_id)
    if page is None:
        raise RuntimeError(f"published, but {post['link']} isn't loading as this post")
    if REVIEW_MARKER in page:
        raise RuntimeError("published with the review notes box still in it. "
                           "Edit the post and delete the box")
    record["wordpress"]["url"] = post["link"]
    record["captions_ready"] = captions_with_links(record)
    set_status(record, "published")
    return True


def lambda_handler(event, context):
    counts = {"moved": 0, "waiting": 0, "skipped": 0, "errors": 0}
    for key in record_keys():
        record = load(key)
        try:
            if record["status"] in ("checked", "needs_review"):
                send_to_wordpress(record)
                changed = True
            elif record["status"] == "in_wordpress":
                changed = check_wordpress(record)
            else:
                counts["skipped"] += 1
                continue
        except Exception as e:  # one bad record mustn't stop the others
            counts["errors"] += 1
            log(step="publish", status="error", key=key, reason=str(e)[:300])
            continue

        if changed:
            save(key, record)
            counts["moved"] += 1
            log(step="moved", key=key, status=record["status"])
        else:
            counts["waiting"] += 1

    log(step="summary", **counts)
    if counts["errors"]:
        raise RuntimeError(f"{counts['errors']} record(s) failed. See the error lines above.")