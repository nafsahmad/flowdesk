"""Stage 1: fetch every contact, score it, write the score back to HubSpot,
then read every score back to prove it landed.

Run from the flowdesk folder with:  python -m scripts.stage1_score_contacts
"""

import time

from shared.hubspot import get_all_contacts, update_contact
from shared.scoring import score_contact

PROPERTIES = [
    "firstname", "lastname", "email", "jobtitle", "company",
    "fd_company_size", "fd_utm_campaign", "fd_score",
]

# Small on purpose, so the loop runs more than once. Change to 100 later.
PAGE_SIZE = 100

# True = only show what would change. False = actually write to HubSpot.
DRY_RUN = False


def display_name(props):
    """First and last name, or the email if there's no name."""
    name = f"{props.get('firstname') or ''} {props.get('lastname') or ''}".strip()
    return name or props.get("email")


def needs_update(current, new_score):
    """True if HubSpot's stored score is missing or different from the new one."""
    if current in (None, ""):
        return True
    try:
        return float(current) != new_score
    except ValueError:
        return True


def verify(expected):
    """Read every contact back from HubSpot and check its score matches."""
    print("\nReading scores back from HubSpot to verify...")
    time.sleep(2)  # give HubSpot a moment to finish saving
    fresh = get_all_contacts(["firstname", "lastname", "email", "fd_score"],
                             page_size=PAGE_SIZE)
    fresh_by_id = {c["id"]: c for c in fresh}

    verified = 0
    problems = []
    for contact_id, score in expected.items():
        contact = fresh_by_id.get(contact_id)
        if contact is None:
            problems.append(f"Contact {contact_id} has disappeared from HubSpot")
            continue
        stored = contact["properties"].get("fd_score")
        if needs_update(stored, score):
            name = display_name(contact["properties"])
            problems.append(f"{name}: expected {score}, HubSpot has {stored}")
        else:
            verified += 1

    print(f"\nVerified {verified} of {len(expected)}")
    for problem in problems:
        print("  PROBLEM:", problem)
    return not problems


def main():
    contacts = get_all_contacts(PROPERTIES, page_size=PAGE_SIZE)
    print(f"\nFetched {len(contacts)} contacts in total\n")

    for prop in PROPERTIES:
        if all(not c["properties"].get(prop) for c in contacts):
            print(f"Warning: '{prop}' is empty for every contact. Is the name right?")

    expected = {}
    to_update, updated, unchanged, failed = 0, 0, 0, 0

    for contact in contacts:
        props = contact["properties"]
        name = display_name(props)
        current = props.get("fd_score")
        new_score = score_contact(props)
        expected[contact["id"]] = new_score

        if not needs_update(current, new_score):
            unchanged += 1
            print(f"SAME       {name:<18} score {new_score}")
            continue

        to_update += 1
        if DRY_RUN:
            print(f"WOULD SET  {name:<18} {current} -> {new_score}")
            continue

        result = update_contact(contact["id"], {"fd_score": new_score})
        if result is None:
            failed += 1
            print(f"FAILED     {name:<18} (see the error above)")
        else:
            updated += 1
            print(f"UPDATED    {name:<18} {current} -> {new_score}")

    print(f"\nNeeded changes: {to_update}. Updated: {updated}. "
          f"Unchanged: {unchanged}. Failed: {failed}.")

    if DRY_RUN:
        print("Dry run, so nothing was written or verified. Set DRY_RUN = False to write.")
        return

    if not verify(expected):
        raise SystemExit("Verification failed. See the problems above.")


if __name__ == "__main__":
    main()