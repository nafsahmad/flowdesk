"""Stage 4, local test: a saved draft record -> WordPress draft -> read it back.

Run from the flowdesk folder with:
    python -m scripts.stage4_try_wordpress build/drafts/onboarding-checklist.json
"""

import json
import os
import sys

from shared.links import tracked_link
from shared.wordpress import body_to_html, create_draft, get_category_id, get_post

CATEGORY_SLUG = "flowdesk"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.stage4_try_wordpress <draft record file>")
    with open(sys.argv[1], encoding="utf-8") as f:
        record = json.load(f)

    if record["status"] != "checked":
        raise SystemExit(f"Status is '{record['status']}'. Only checked drafts go to WordPress.")

    link = tracked_link(os.environ["TALLY_FORM_URL"], "blog", record["brief_id"], "blog")
    content = body_to_html(record["blog"]["body"], link)
    category_id = get_category_id(CATEGORY_SLUG)

    post_id, edit_link = create_draft(record["blog"]["title"], content, category_id)
    print(f"Created draft {post_id}")
    print(f"Edit it here: {edit_link}")

    post = get_post(post_id)
    problems = []
    if post is None:
        problems.append("the post wasn't found when reading it back")
    else:
        if post["status"] != "draft":
            problems.append(f"status is {post['status']}, expected draft")
        if post["title"]["raw"] != record["blog"]["title"]:
            problems.append("the title doesn't match")
        if f"utm_campaign={record['brief_id']}" not in post["content"]["raw"]:
            problems.append("the tracked link is missing")
        if category_id not in post["categories"]:
            problems.append("it isn't in the FlowDesk category")

    if problems:
        raise SystemExit("Verification failed: " + "; ".join(problems))
    print("Verified: it's a draft, with the right title, tracked link and category")


if __name__ == "__main__":
    main()