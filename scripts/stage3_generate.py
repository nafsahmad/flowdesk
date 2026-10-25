"""Stage 3, local run: brief file -> generate -> save the record in build/drafts/.

Run from the flowdesk folder with:
    python -m scripts.stage3_generate sample_data/briefs/onboarding-checklist.json
"""

import json
import sys
from pathlib import Path

from shared.generator import generate


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.stage3_generate <brief file>")
    with open(sys.argv[1], encoding="utf-8") as f:
        brief = json.load(f)

    record = generate(brief)

    out_dir = Path("build") / "drafts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{record['brief_id']}.json"
    out_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"Brief:  {record['brief_id']}")
    print(f"Model:  {record['model']}")
    print(f"Status: {record['status']}")
    for piece, results in record["rule_checks"].items():
        problems = {k: v for k, v in results.items() if v != "pass"}
        print(f"  rules {piece:<10} {'all pass' if not problems else problems}")
    for piece, verdict in record["judge"].items():
        print(f"  judge {piece:<10} {verdict}")
    print(f"Saved:  {out_path}")


if __name__ == "__main__":
    main()