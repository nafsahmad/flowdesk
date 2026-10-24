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