"""Checks the weekly report maths, SQL and number check, without HubSpot or AWS.

Run from the flowdesk folder with:  python -m tests.test_report
"""

import os

os.environ["FLOWDESK_FAKE_LLM"] = "1"  # never call Bedrock from tests

from shared.report import (build_report, format_email, read_spend_csv,  # noqa: E402
                           unsupported_numbers, write_summary)

SPEND_CSV = """week_start,platform,utm_source,utm_campaign,utm_content,spend_usd,impressions,clicks
2026-10-12,linkedin,linkedin,oct-launch,A,99.00,1000,10
2026-10-19,linkedin,linkedin,oct-launch,A,40.00,12000,180
2026-10-19,linkedin,linkedin,oct-launch,B,40.00,11500,140
"""


def contact(campaign=None, variant=None, stage="lead", revenue=None):
    return {"properties": {"fd_utm_campaign": campaign, "fd_utm_content": variant,
                           "lifecyclestage": stage, "fd_revenue": revenue}}


CONTACTS = [
    contact("oct-launch", "A"),
    contact("oct-launch", "A", "customer", "400"),
    contact("oct-launch", "B", "customer", "600"),
    contact("oct-launch", None),
    contact(None, None),
]


def main():
    spend = read_spend_csv(SPEND_CSV, "2026-10-19")
    report = build_report(CONTACTS, spend, "2026-10-19", "2026-10-26")
    rows = {(r["campaign"], r["variant"]): r for r in report["rows"]}
    a, b = rows[("oct-launch", "A")], rows[("oct-launch", "B")]

    checks = [
        ("Spend from before the period is left out", len(spend) == 2),
        ("Spend counted once, not once per lead (no fan-out)", a["spend"] == 40.0),
        ("Variant A: 2 leads, 1 customer, $400 revenue",
         (a["leads"], a["customers"], a["revenue"]) == (2, 1, 400.0)),
        ("Variant A metrics: CTR 1.5, CPC 0.22, CPM 3.33, CVR 1.11",
         (a["ctr_pct"], a["cpc"], a["cpm"], a["cvr_pct"]) == (1.5, 0.22, 3.33, 1.11)),
        ("Variant A metrics: CPA 20, CAC 40, ROAS 10",
         (a["cpa"], a["cac"], a["roas"]) == (20.0, 40.0, 10.0)),
        ("Variant B metrics: CPA 40, CAC 40, ROAS 15",
         (b["cpa"], b["cac"], b["roas"]) == (40.0, 40.0, 15.0)),
        ("A lead with a campaign but no variant gets its own row, no cost metrics",
         rows[("oct-launch", None)]["leads"] == 1 and rows[("oct-launch", None)]["cpa"] is None),
        ("A lead with no campaign is counted", rows[(None, None)]["leads"] == 1),
        ("Totals cover paid rows only: spend 80, 3 leads",
         (report["totals"]["spend"], report["totals"]["leads"]) == (80.0, 3)),
        ("Data notes flag both attribution problems",
         len(report["notes"]) == 2 and "no campaign" in report["notes"][0]),
        ("Number check passes numbers from the table", unsupported_numbers(
            "CPA was 20.00 for A and 40 for B, with a ROAS of 15.", "cpa 20.0 40.0 roas 15.0") == []),
        ("Number check catches an invented number", unsupported_numbers(
            "ROAS was 12 for A.", "roas 10.0 15.0") == ["12"]),
        ("Rounding is allowed: 1.11 in the table, 1.1 in the text",
         unsupported_numbers("CVR was 1.1%.", "cvr 1.11") == []),
    ]

    summary, bad = write_summary(report)
    report["summary"], report["summary_check"] = summary, "pass"
    email = format_email(report)
    checks += [
        ("Fake summary passes the number check", bad == []),
        ("Email says SAMPLE DATA", "SAMPLE DATA" in email),
        ("Email shows A's CPA and B's ROAS", "CPA $20.00" in email and "ROAS 15.0" in email),
    ]

    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in checks)} of {len(checks)} passed")


if __name__ == "__main__":
    main()