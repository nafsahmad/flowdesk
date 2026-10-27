def get_all_contacts(properties, page_size=100):
    """Fetch every contact, one page at a time. Return them all in one list."""
    contacts = []
    params = {"limit": page_size, "properties": ",".join(properties)}
    page = 1
    while True:
        data = call_api("GET", "/crm/v3/objects/contacts", params=params)
        if data is None:
            raise RuntimeError(f"Stopped on page {page}. See the error above.")
        contacts.extend(data["results"])
        print(f"Page {page}: got {len(data['results'])} contacts")
        next_page = data.get("paging", {}).get("next")
        if not next_page:
            break
        params["after"] = next_page["after"]
        page += 1
    return contacts


"""Small helper for talking to the HubSpot API.

Every FlowDesk script and Lambda imports call_api from here,
so the key, headers, timeout and error handling live in one place.
"""

import os

from urllib.parse import quote

import requests

BASE_URL = "https://api.hubapi.com"
TIMEOUT_SECONDS = 10


def _headers():
    """Build the request headers, reading the key at the moment of the call."""
    key = os.environ.get("HUBSPOT_KEY")
    if not key:
        raise RuntimeError("HUBSPOT_KEY isn't set. Run setx, then restart VS Code.")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def call_api(method, path, params=None, body=None):
    """Send one request to HubSpot. Return the JSON, or None if it failed."""
    url = BASE_URL + path
    try:
        r = requests.request(method, url, headers=_headers(),
                             params=params, json=body, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        print(f"{method} {path} failed with {r.status_code}: {r.text[:300]}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"{method} {path} never reached HubSpot: {e}")
        return None
    if r.status_code == 204:
        return {}
    return r.json()

def update_contact(contact_id, properties):
    """Change some properties on one contact. Return the updated contact, or None."""
    return call_api("PATCH", f"/crm/v3/objects/contacts/{contact_id}",
                    body={"properties": properties})


class HubSpotError(Exception):
    """HubSpot answered, but not with success. Keeps the status code."""

    def __init__(self, status, message):
        super().__init__(f"HubSpot returned {status}: {message}")
        self.status = status


def _send_or_raise(method, path, params=None, body=None):
    """Like call_api, but raises instead of returning None.

    Used for webhooks, where a failure must stop the run so the sender retries.
    """
    r = requests.request(method, BASE_URL + path, headers=_headers(),
                         params=params, json=body, timeout=TIMEOUT_SECONDS)
    if not r.ok:
        raise HubSpotError(r.status_code, r.text[:300])
    return r.json() if r.content else {}


def get_contact_by_email(email, properties=()):
    """Return the contact with this email, or None if there isn't one."""
    params = {"idProperty": "email"}
    if properties:
        params["properties"] = ",".join(properties)
    try:
        return _send_or_raise("GET", f"/crm/v3/objects/contacts/{quote(email)}",
                              params=params)
    except HubSpotError as e:
        if e.status == 404:
            return None
        raise


def upsert_contact(properties):
    """Update the contact if the email exists, create it if not.

    Returns ("created" or "updated", contact_id).
    """
    existing = get_contact_by_email(properties["email"])
    if existing:
        _send_or_raise("PATCH", f"/crm/v3/objects/contacts/{existing['id']}",
                       body={"properties": properties})
        return "updated", existing["id"]

    created = _send_or_raise("POST", "/crm/v3/objects/contacts",
                             body={"properties": properties})
    return "created", created["id"]

def search_contacts_created_since(since, properties):
    """Every contact created at or after `since` (a datetime), page by page."""
    body = {
        "filterGroups": [{"filters": [{
            "propertyName": "createdate",
            "operator": "GTE",
            "value": str(int(since.timestamp() * 1000)),
        }]}],
        "properties": list(properties),
        "limit": 100,
    }
    contacts = []
    while True:
        data = _send_or_raise("POST", "/crm/v3/objects/contacts/search", body=body)
        contacts.extend(data["results"])
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            return contacts
        body["after"] = after

if __name__ == "__main__":
    # Quick self-test: fetch one contact and show its email.
    data = call_api("GET", "/crm/v3/objects/contacts", params={"limit": 1})
    if data is None:
        print("The call failed. Read the message above.")
    elif not data["results"]:
        print("Connected, but there are no contacts yet.")
    else:
        first = data["results"][0]
        print("It works. First contact:", first["properties"].get("email"))