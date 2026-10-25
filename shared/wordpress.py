"""Talks to the WordPress REST API, logging in with an application password.

Reads three environment variables: WP_SITE, WP_USER and WP_APP_PASSWORD.
"""

import html
import os

import requests

TIMEOUT_SECONDS = 15


class WordPressError(Exception):
    """WordPress answered, but not with success. Keeps the status code."""

    def __init__(self, status, message):
        super().__init__(f"WordPress returned {status}: {message}")
        self.status = status


def site_url():
    return os.environ["WP_SITE"].rstrip("/")


def _send(method, path, params=None, body=None):
    r = requests.request(method, f"{site_url()}/wp-json/wp/v2{path}",
                         auth=(os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"]),
                         params=params, json=body, timeout=TIMEOUT_SECONDS)
    if not r.ok:
        raise WordPressError(r.status_code, r.text[:300])
    return r.json()


def body_to_html(body, link_url, link_text="Pick a time here"):
    """Turn the model's plain text into WordPress paragraph blocks, with the real link."""
    link_html = f'<a href="{html.escape(link_url)}">{link_text}</a>'
    blocks = []
    for paragraph in body.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        safe = html.escape(paragraph, quote=False).replace("{link}", link_html)
        blocks.append(f"<!-- wp:paragraph -->\n<p>{safe}</p>\n<!-- /wp:paragraph -->")
    return "\n\n".join(blocks)


def get_category_id(slug):
    """Find a category's id from its slug, for example "flowdesk"."""
    found = _send("GET", "/categories", params={"slug": slug})
    if not found:
        raise WordPressError(404, f"No category with the slug '{slug}'")
    return found[0]["id"]


def create_draft(title, html_content, category_id):
    """Create a draft post. Returns (post id, admin edit link)."""
    post = _send("POST", "/posts", body={
        "title": title,
        "content": html_content,
        "status": "draft",
        "categories": [category_id],
    })
    edit_link = f"{site_url()}/wp-admin/post.php?post={post['id']}&action=edit"
    return post["id"], edit_link


def get_post(post_id):
    """Return the post, or None if it has been deleted for good."""
    try:
        return _send("GET", f"/posts/{post_id}", params={"context": "edit"})
    except WordPressError as e:
        if e.status == 404:
            return None
        raise