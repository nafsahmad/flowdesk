"""Builds tracked links, so every click carries its UTM values into the form."""

from urllib.parse import urlencode


def tracked_link(base_url, source, campaign, content):
    """Add utm_source, utm_campaign and utm_content to a URL."""
    query = urlencode({"utm_source": source, "utm_campaign": campaign,
                       "utm_content": content})
    joiner = "&" if "?" in base_url else "?"
    return f"{base_url}{joiner}{query}"