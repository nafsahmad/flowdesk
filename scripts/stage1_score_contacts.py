"""Stage 1: fetch every contact, score it, write the score back to HubSpot.

Run from the flowdesk folder with:  python -m scripts.stage1_score_contacts
"""

from shared.hubspot import get_all_contacts

PROPERTIES = [
    "firstname", "lastname", "email", "jobtitel", "company",
    "fd_company_size", "fd_utm_campaign", "fd_score",
]

# Small on purpose, so the loop runs more than once. Change to 100 later.
PAGE_SIZE = 3


def main():
    contacts = get_all_contacts(PROPERTIES, page_size=PAGE_SIZE)
    print(f"\nFetched {len(contacts)} contacts in total\n")

    for prop in PROPERTIES:
        if all(not c["properties"].get(prop) for c in contacts):
            print(f"Warning: '{prop}' is empty for every contact. Is the name right?")
            
    for contact in contacts:
        props = contact["properties"]
        name = f"{props.get('firstname') or ''} {props.get('lastname') or ''}".strip()
        name = name or props.get("email")
        title = props.get("jobtitle") or "(no title)"
        company = props.get("company") or "(no company)"
        size = props.get("fd_company_size") or "?"
        print(f"{name:<18} | {title:<22} | {company:<22} | size {size}")


if __name__ == "__main__":
    main()