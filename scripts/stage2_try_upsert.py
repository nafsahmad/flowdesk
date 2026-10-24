"""Stage 2, local test: sample Tally payload -> parse -> score -> upsert -> verify.

Run from the flowdesk folder with:  python -m scripts.stage2_try_upsert
"""

import json

from shared.hubspot import get_contact_by_email, upsert_contact
from shared.scoring import score_contact
from shared.tally import parse_tally


def main():
    with open("sample_data/tally_payload.json", encoding="utf-8") as f:
        payload = json.load(f)

    properties, submission_id = parse_tally(payload)
    properties["fd_score"] = score_contact(properties)

    action, contact_id = upsert_contact(properties)
    print(f"Submission {submission_id}: {action} contact {contact_id}")

    stored = get_contact_by_email(properties["email"], list(properties))["properties"]
    mismatches = [name for name, value in properties.items()
                  if str(stored.get(name)) != str(value)]
    if mismatches:
        raise SystemExit(f"Verification failed for: {', '.join(mismatches)}")
    print(f"Verified all {len(properties)} properties in HubSpot")


if __name__ == "__main__":
    main()